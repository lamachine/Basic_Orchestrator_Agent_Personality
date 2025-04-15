import json
from dotenv import load_dotenv
import requests
import os
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import re

# Local imports
from src.services.db_services.db_manager import (
    DatabaseManager, 
    ConversationState, 
    ConversationSummary,
    TaskStatus, 
    MessageRole, 
    StateError,
    StateTransitionError,
    Message
)
from src.config import Configuration
from src.config.logging_config import setup_logging
# Import tool integration
from src.agents.orchestrator_tools import (
    add_tools_to_prompt, 
    handle_tool_calls, 
    format_tool_results, 
    format_completed_tools_prompt,
    PENDING_TOOL_REQUESTS
)
from src.graphs.orchestrator_graph import create_initial_state, StateManager

# Import tool initialization
from src.tools.initialize_tools import initialize_tool_dependencies

# Load environment variables
load_dotenv(override=True)

# Setup basic logging
logger = logging.getLogger(__name__)

# Load common configuration
config = Configuration()

# Setup logging
try:
    # Initialize logging
    file_handler, console_handler = setup_logging(config)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.debug("Logging initialized successfully")
except Exception as e:
    print(f"Error setting up logging: {e}")
    # Setup basic logging as fallback
    logging.basicConfig(level=logging.INFO)

class LLMQueryAgent:
    def __init__(self, config: Configuration = config):
        """Initialize the LLM Query Agent with configuration."""
        # Configuration
        self.config = config
        self.api_url = config.ollama_api_url + '/api/generate'
        self.model = config.ollama_model
        
        # Initialize database
        try:
            self.db = DatabaseManager()
            self.has_db = True
            logger.debug(f"Database initialized successfully")
        except Exception as e:
            error_msg = f"Database initialization failed: {e}"
            logger.critical(error_msg)
            print(error_msg)
            self.has_db = False
        
        # Session tracking
        self.conversation_state = None
        self.user_id = "developer"  # Default user ID
        
        # Tool tracking
        self.last_tool_results = ""
        
        # Initialize graph state and state manager
        self.graph_state = create_initial_state()
        self.state_manager = StateManager(self.graph_state)
        
        # Track requests and user inputs
        self.pending_requests = {}
        
        # Initialize tool dependencies
        self.tool_initialization = initialize_tool_dependencies(self)
        
        # Print configuration for debugging
        logger.debug(f"Initializing LLM Agent with model: {self.model}")
        logger.debug(f"API URL: {self.api_url}")
        # print(f"Database available: {self.has_db}")
        
    @property
    def session_id(self) -> Optional[int]:
        """Get the current session ID if available."""
        if self.conversation_state:
            return self.conversation_state.session_id
        return None

    def start_conversation(self, title: Optional[str] = None):
        """Start a new conversation if database is available."""
        try:
            self.conversation_state = self.db.create_conversation(
                self.user_id,
                title=title
            )
            logger.debug(f"Started conversation with session ID: {self.session_id}")
            
            # Initialize graph state for the new conversation
            self.graph_state = create_initial_state()
            self.state_manager = StateManager(self.graph_state)
            
            return True
        except Exception as e:
            error_msg = f"Failed to start conversation: {e}"
            logger.error(error_msg)
            return False

    def continue_conversation(self, session_id):
        """Continue an existing conversation if database is available.
        
        Args:
            session_id: The session ID to continue (can be int or string)
            
        Returns:
            bool: True if conversation was successfully continued, False otherwise
        """
        try:
            # Log the session ID and type for debugging
            logger.debug(f"Agent attempting to continue conversation with session ID: {session_id} (type: {type(session_id).__name__})")
            
            # Try to continue the conversation
            self.conversation_state = self.db.continue_conversation(session_id)
            
            if self.conversation_state:
                logger.debug(f"Successfully continued conversation with session ID: {session_id}")
                
                # Initialize graph state for the continued conversation
                self.graph_state = create_initial_state()
                self.state_manager = StateManager(self.graph_state)
                
                return True
            else:
                error_msg = f"Failed to continue conversation: session {session_id} not found"
                logger.error(error_msg)
                return False
        except Exception as e:
            error_msg = f"Failed to continue conversation: {e}"
            logger.error(error_msg)
            logger.error(f"Exception type: {type(e).__name__}, details: {str(e)}")
            return False

    def list_conversations(self, limit: int = 10):
        """List available conversations for the current user.
        
        Args:
            limit: Maximum number of conversations to return
            
        Returns:
            List of ConversationSummary objects or dictionary of conversation data
        """
        try:
            # Get conversations for the current user from the DB manager
            all_conversations = self.db.list_conversations(user_id=self.user_id)
            
            if not all_conversations:
                return []
            
            # Create a list of conversation summaries for compatibility
            conversation_summaries = []
            
            # Sort conversations by updated_at in descending order
            sorted_sessions = sorted(
                all_conversations.items(),
                key=lambda x: x[1]['updated_at'] if x[1]['updated_at'] else datetime.min,
                reverse=True
            )
            
            # Apply limit
            for session_id, conv_data in sorted_sessions[:limit]:
                # Keep session_id as is - don't try to convert to int
                # The ConversationSummary model now accepts Union[int, str]
                
                # Ensure datetimes are properly handled
                created_at = self.db._ensure_naive_datetime(conv_data['created_at'])
                updated_at = self.db._ensure_naive_datetime(conv_data['updated_at'])
                
                # Create a ConversationSummary for backward compatibility
                summary = ConversationSummary(
                    session_id=session_id,  # Use as is, no conversion
                    title=conv_data['name'],
                    created_at=created_at,
                    updated_at=updated_at,
                    message_count=0,  # Not available in new format
                    user_id=self.user_id,
                    current_task_status=TaskStatus.PENDING  # Default
                )
                
                # Add an extra attribute for display formatting
                summary.display_name = conv_data.get('display_name', conv_data['name'])
                
                conversation_summaries.append(summary)
            
            return conversation_summaries
        except Exception as e:
            error_msg = f"Failed to list conversations: {e}"
            logger.error(error_msg)
        return []

    def update_task_status(self, new_status: TaskStatus) -> bool:
        """Update the task status of the current conversation."""
        try:
            result = self.db.update_task_status(self.conversation_state, new_status)
            if result:
                logger.debug(f"Updated task status to {new_status}")
                return True
            else:
                logger.error(f"Failed to update task status to {new_status}")
                return False
        except StateTransitionError as e:
            error_msg = f"Invalid task status transition: {e}"
            logger.error(error_msg)
            return False
        except Exception as e:
            error_msg = f"Error updating task status: {e}"
            logger.error(error_msg)
            return False

    # Add a method to rename the current conversation
    def rename_conversation(self, new_title: str) -> bool:
        """Rename the current conversation.
        
        Args:
            new_title: The new title for the conversation
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.session_id:
            logger.error("Cannot rename: No active conversation")
            return False
        
        try:
            result = self.db.rename_conversation(self.session_id, new_title)
            if result:
                # Update the local state as well
                if self.conversation_state:
                    self.conversation_state.metadata.title = new_title
                    self.conversation_state.metadata.updated_at = datetime.now()
                logger.debug(f"Renamed conversation to '{new_title}'")
                return True
            else:
                logger.error(f"Failed to rename conversation to '{new_title}'")
                return False
        except Exception as e:
            error_msg = f"Error renaming conversation: {e}"
            logger.error(error_msg)
            return False

    def generate_prompt(self, user_input: str) -> str:
        """Generate a prompt for the LLM with tool descriptions and conversation context."""
        logger.debug(f"Generating prompt for input: {user_input[:50]}...")
        
        # Get recent conversation context
        context = self.get_conversation_context()
        
        # Enhanced base prompt with more explicit instructions about tool usage
        base_prompt = f"""You are a helpful AI assistant with access to specialized tools.

IMPORTANT INSTRUCTIONS FOR TOOL USAGE:
1. Answer questions directly when you can.
2. Use tools ONLY when necessary for specific tasks that require them.
3. When using a tool, use EXACTLY this format: `tool_name(task="your request")` 
   For example: `scrape_repo(task="https://github.com/username/repo")`
4. NEVER make up or hallucinate tool results. Wait for actual results.
5. If you mention a tool, you MUST call it properly with the syntax above.
6. For GitHub repositories, you MUST use the scrape_repo tool with the full URL.

Conversation Context:
{context}

User: {user_input}
Assistant:"""

        # Add tool descriptions to the prompt
        enhanced_prompt = add_tools_to_prompt(base_prompt)
        
        # Add previous tool results if available
        if self.last_tool_results:
            enhanced_prompt = f"{enhanced_prompt}\n\n{self.last_tool_results}"
            
        # Log the full prompt at debug level
        logger.debug(f"FULL PROMPT:\n{enhanced_prompt}")
            
        return enhanced_prompt

    def get_conversation_context(self) -> str:
        """Get conversation context if database is available."""
        try:
            recent_messages = self.db.get_recent_messages(self.session_id)
            logger.debug(f"Retrieved {len(recent_messages)} messages for context")
            
            # Filter out system messages and format the conversation more cleanly
            formatted_messages = []
            for msg in recent_messages:
                # Skip system messages and tool submissions
                if msg['role'] in ['system'] or 'tool request submitted' in msg['message']:
                    continue
                # Clean up the role name
                role = msg['role'].replace('orchestrator_graph.', '')
                formatted_messages.append(f"{role}: {msg['message']}")
            
            return "\n".join(formatted_messages)
        except Exception as e:
            error_msg = f"Failed to get conversation context: {e}"
            logger.error(error_msg)
            return ""

    # Original LLM query method
    def query_llm(self, prompt: str) -> str:
        """Send a query to the LLM via Ollama API and return the response."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            # Send the request to the LLM
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            response_json = response.json()
            
            # Extract the response text and metadata
            response_text = response_json.get('response', 'No response from LLM')
            created_at = response_json.get('created_at', '')
            context = response_json.get('context', [])
            total_duration = response_json.get('total_duration', 0)
            load_duration = response_json.get('load_duration', 0)
            prompt_eval_count = response_json.get('prompt_eval_count', 0)
            eval_count = response_json.get('eval_count', 0)
            
            # Log response details at debug level only
            logger.debug(f"Response details:")
            logger.debug(f"- Created at: {created_at}")
            logger.debug(f"- Total duration: {total_duration}ns")
            logger.debug(f"- Load duration: {load_duration}ns")
            logger.debug(f"- Prompt eval tokens: {prompt_eval_count}")
            logger.debug(f"- Response eval tokens: {eval_count}")
            logger.debug(f"- Response length: {len(response_text)} characters")
            
            return response_text
        except Exception as e:
            error_msg = f"Error querying LLM: {str(e)}"
            logger.critical(error_msg)
            return error_msg
    
    def process_response_with_tools(self, response_text: str) -> Dict[str, Any]:
        """Process LLM response to handle any tool calls."""
        logger.debug("Processing LLM response for tool calls")
        logger.debug(f"Response text (first 300 chars): {response_text[:300]}...")  # Log first 300 characters at DEBUG level
        
        # Check for hallucinated tool responses - patterns like "tool_name: result" or "tool(...): result"
        # Only consider it a hallucination if it's not a proper tool call syntax
        hallucination_patterns = [
            r'`([a-zA-Z_\.]+)_tool:\s+(.*?)`',  # `tool_name_tool: result`
            r'([a-zA-Z_]+)\s*\([^)]*\):\s+(.*)',  # tool(...): result 
            r'([a-zA-Z_]+)\s+tool\s+response:\s+(.*)',  # tool name tool response: result
            r'orchestrator_graph\.([a-zA-Z_]+)_tool:\s+(.*)'  # orchestrator_graph.tool_name_tool: result
        ]
        
        # First, check if there's a valid tool call pattern
        valid_tool_pattern = r'`([a-zA-Z_]+)\s*\(\s*task\s*=\s*(?:"|\')(.*?)(?:"|\')\s*\)`'
        has_valid_tool_call = bool(re.search(valid_tool_pattern, response_text))
        
        logger.debug(f"Has valid tool call pattern: {has_valid_tool_call}")
        
        # Only check for hallucinations if we don't have a valid tool call
        hallucinated = False
        if not has_valid_tool_call:
            for pattern in hallucination_patterns:
                if re.search(pattern, response_text, re.IGNORECASE):
                    hallucinated = True
                    logger.warning(f"Detected hallucinated tool output in response: {response_text[:100]}...")
                    break
        
        if hallucinated:
            # We need to re-prompt with stronger instructions against hallucination
            # Return an empty result that will trigger the appropriate handling
            logger.warning("Detected hallucination, will attempt re-prompting")
            return {
                "tool_calls": [],
                "execution_results": [],
                "hallucinated": True,
                "original_response": response_text
            }
            
        # Handle any tool calls in the response
        logger.debug("Calling handle_tool_calls to extract tool calls from response")
        processing_result = handle_tool_calls(response_text)
        
        # Log the processing result
        logger.debug(f"Processing result tool_calls: {processing_result['tool_calls']}")
        
        # Format tool results for the next prompt if there were any tool calls
        if processing_result["tool_calls"]:
            logger.debug(f"Found {len(processing_result['tool_calls'])} tool calls in response")
            self.last_tool_results = format_tool_results(processing_result)
            
            # Log tool execution
            for result in processing_result["execution_results"]:
                tool_name = result["name"]
                status = result["result"]["status"]
                request_id = result["result"].get("request_id", "unknown")
                logger.info(f"Tool {tool_name} request {request_id} executed with status: {status}")
        else:
            logger.debug("No tool calls found in response")
            self.last_tool_results = ""
            
        return processing_result
            
    def chat(self, user_input: str, request_id: Optional[str] = None) -> Dict[str, str]:
        """
        Full chat flow with tool integration and database integration if available.
        
        Args:
            user_input: The user's input text
            request_id: Optional request ID for continuing a tool conversation
            
        Returns:
            Dictionary containing the LLM response and any tool results
        """
        logger.debug(f"Processing chat input (length: {len(user_input)})")
        
        # If a request ID is provided, we're handling a tool completion
        if request_id:
            return self.handle_tool_completion(request_id, user_input)
        
        # Start conversation if needed
        if not self.conversation_state:
            logger.info("No active conversation. Starting a new one.")
            self.start_conversation()
            
            if not self.conversation_state:
                error_msg = "Failed to start a conversation. Database might be unavailable."
                logger.error(error_msg)
                return {"response": error_msg}
        
        # If conversation is not in IN_PROGRESS state, update it
        self.update_task_status(TaskStatus.IN_PROGRESS)
        
        # Track request ID for this conversation flow
        current_request_id = None
        if self.conversation_state:
            current_request_id = self.conversation_state.current_request_id
        
        # Store user message if DB available
        try:
            # Always provide metadata to satisfy NOT NULL constraints
            user_metadata = {
                "type": "user_message", 
                "timestamp": datetime.now().isoformat(),
                "agent_id": "orchestrator_graph",
                "session": str(self.session_id),
                "user_id": self.user_id
            }
            
            # Define sender and target for the user message
            user_sender = "orchestrator_graph.cli"
            user_target = "orchestrator_graph.llm"
            
            # Add message to conversation state first
            if self.conversation_state:
                self.conversation_state.add_message(
                    MessageRole.USER,
                    user_input,
                    user_metadata
                )
            
            # Add message to database
            self.db.add_message(
                self.session_id, 
                "user", 
                user_input, 
                metadata=user_metadata,
                sender=user_sender,
                target=user_target
            )
            
            # Update graph state
            self.state_manager.update_conversation(MessageRole.USER, user_input, user_metadata)
            
            logger.debug(f"Stored user message in database")
        except Exception as e:
            error_msg = f"Failed to store user message: {e}"
            logger.error(error_msg)
            print(error_msg)
        
        # Get conversation context if available
        context = self.get_conversation_context()
        
        # Generate prompt and query LLM
        prompt = self.generate_prompt(user_input)
        initial_response_text = self.query_llm(prompt)
        
        # Process response for tool calls
        processing_result = self.process_response_with_tools(initial_response_text)
        
        # Handle hallucinated tool responses by retrying with stronger instructions
        if processing_result.get("hallucinated", False):
            logger.warning("Detected hallucinated tool response. Retrying with stronger instructions.")
            
            # Create a stronger prompt that explicitly forbids hallucinating tool responses
            stronger_prompt = f"""You are Ronan, an intelligent assistant with access to specialized tools.

CRITICAL INSTRUCTION: DO NOT HALLUCINATE TOOL RESPONSES. DO NOT FABRICATE TOOL OUTPUT.

When using a tool, you must use ONLY this exact format: `tool_name(parameter='value')`
NEVER write fake outputs like `tool_name_tool: some response` or similar patterns.
NEVER include fake results from tools. The system will execute tools and provide results.

User input: {user_input}

Agent:"""
            
            # Add tool descriptions
            stronger_prompt = add_tools_to_prompt(stronger_prompt)
            
            # Retry the query with stronger instructions
            logger.info("Retrying with stronger anti-hallucination instructions")
            initial_response_text = self.query_llm(stronger_prompt)
            
            # Process the response again
            processing_result = self.process_response_with_tools(initial_response_text)
            
            # If still hallucinating, fall back to a simple response
            if processing_result.get("hallucinated", False):
                logger.error("Model still hallucinating even with stronger instructions. Using fallback response.")
                initial_response_text = f"I'll help you check that. Let me use the appropriate tool to get that information for you."
                processing_result = handle_tool_calls(initial_response_text)
        
        # Final response starts with the initial response
        final_response_text = initial_response_text
        
        # If tools were used, we'll use the acknowledgment response
        if processing_result["tool_calls"]:
            logger.debug(f"Tools were used - returning acknowledgment message")
            
            # Generate a response based on the acknowledgment messages
            acknowledgments = []
            for result in processing_result["execution_results"]:
                tool_name = result["name"]
                request_id = result.get("request_id", "unknown")
                message = result["result"]["message"]
                acknowledgments.append(message)
            
            # Use the acknowledgment message as the final response
            final_response_text = " ".join(acknowledgments)
        
        # Store assistant message if DB available
        try:
            # Add tool usage info to metadata
            tool_info = {}
            if processing_result["tool_calls"]:
                tool_info = {
                    "tools_used": [call["name"] for call in processing_result["tool_calls"]],
                    "tool_count": len(processing_result["tool_calls"]),
                    "request_ids": [result.get("request_id", "unknown") for result in processing_result["execution_results"]]
                }
            
            # Always provide metadata to satisfy NOT NULL constraints
            assistant_metadata = {
                "type": "assistant_response", 
                "timestamp": datetime.now().isoformat(),
                "agent_id": "orchestrator_graph",
                "model": self.model,
                "session": str(self.session_id),
                "user_id": self.user_id,
                **tool_info
            }
            
            # Define sender and target for the assistant message
            assistant_sender = "orchestrator_graph.llm"
            assistant_target = "orchestrator_graph.cli"
            
            # Add message to conversation state first
            if self.conversation_state:
                self.conversation_state.add_message(
                    MessageRole.ASSISTANT,
                    final_response_text,
                    assistant_metadata
                )
            
            # Add message to database
            self.db.add_message(
                self.session_id, 
                "assistant", 
                final_response_text, 
                metadata=assistant_metadata,
                sender=assistant_sender,
                target=assistant_target
            )
            
            # Update graph state
            self.state_manager.update_conversation(MessageRole.ASSISTANT, final_response_text, assistant_metadata)
            
            logger.debug(f"Stored assistant response in database")
            
            # Store tool requests if any
            if processing_result["execution_results"]:
                for result in processing_result["execution_results"]:
                    tool_name = result["name"]
                    request_id = result.get("request_id", "unknown")
                    status = result["result"]["status"]
                    
                    tool_metadata = {
                        "type": "tool_request", 
                        "tool": tool_name,
                        "request_id": request_id,
                        "status": status,
                        "timestamp": datetime.now().isoformat(),
                        "session": str(self.session_id),
                        "user_id": self.user_id
                    }
                    
                    # Add message to conversation state first
                    if self.conversation_state:
                        self.conversation_state.add_message(
                            MessageRole.TOOL,
                            "Tool request submitted",
                            tool_metadata
                        )
                    
                    # Define sender and target for the tool message
                    tool_sender = f"orchestrator_graph.{tool_name}_tool"
                    tool_target = "orchestrator_graph.llm"
                    
                    # Pass the current_request_id to maintain continuity and get back any new one
                    current_request_id = self.db.add_message(
                        self.session_id, 
                        "tool", 
                        "Tool request submitted", 
                        metadata=tool_metadata,
                        request_id=current_request_id,
                        sender=tool_sender,
                        target=tool_target
                    )
                        
                logger.debug(f"Stored {len(processing_result['execution_results'])} tool requests in database")
                
                # Update conversation state with current request ID
                if self.conversation_state:
                    self.conversation_state.current_request_id = current_request_id
            
            # If this appears to be a "goodbye" or end of conversation, mark the task as completed
            if self._is_conversation_end(final_response_text) and self.conversation_state:
                self.update_task_status(TaskStatus.COMPLETED)
        except Exception as e:
            error_msg = f"Failed to store messages: {e}"
            logger.error(error_msg)
            print(error_msg)
        
        # Return both the LLM response and any tool results
        result = {
            "response": final_response_text,
            "has_tool_results": bool(processing_result["tool_calls"]),
        }
        
        if processing_result["execution_results"]:
            tool_requests = []
            for r in processing_result["execution_results"]:
                request_id = r.get("request_id", "unknown")
                # Store the user input for each request for later automatic completion
                self.pending_requests[request_id] = user_input
                
                tool_requests.append({
                    "tool": r["name"],
                    "request_id": request_id,
                    "message": r["result"]["message"]
                })
            
            result["tool_requests"] = tool_requests
                
        return result

    def handle_tool_completion(self, request_id: str, original_query: str) -> Dict[str, str]:
        """
        Handle tool request completion and generate a response with the results.
        
        Args:
            request_id: The ID of the completed request
            original_query: The original user query that triggered the tool
            
        Returns:
            Dictionary containing the LLM response
        """
        logger.info(f"HANDLING TOOL COMPLETION: Request ID {request_id}")
        
        # Generate a prompt with the completed tool results
        prompt = format_completed_tools_prompt(request_id, original_query)
        
        # Query the LLM with the tool results
        response_text = self.query_llm(prompt)
        
        # Store the tool completion message if DB available
        try:
            # Get the tool and response details
            tool_details = PENDING_TOOL_REQUESTS.get(request_id, {})
            tool_name = tool_details.get("name", "unknown")
            tool_response = tool_details.get("response", "No response available")
            
            # Add metadata for the tool completion
            tool_metadata = {
                "type": "tool_response", 
                "tool": tool_name,
                "request_id": request_id,
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "session": str(self.session_id),
                "user_id": self.user_id
            }
            
            # Add message to conversation state first
            if self.conversation_state:
                self.conversation_state.add_message(
                    MessageRole.TOOL,
                    tool_response,
                    tool_metadata
                )
            
            # Define sender and target
            tool_sender = f"orchestrator_graph.{tool_name}_tool"
            tool_target = "orchestrator_graph.llm"
            
            # Add message to database
            self.db.add_message(
                self.session_id, 
                "tool", 
                tool_response, 
                metadata=tool_metadata,
                sender=tool_sender,
                target=tool_target
            )
            
            # Add the LLM's response with the tool results
            assistant_metadata = {
                "type": "assistant_response", 
                "timestamp": datetime.now().isoformat(),
                "agent_id": "orchestrator_graph",
                "model": self.model,
                "session": str(self.session_id),
                "user_id": self.user_id,
                "request_id": request_id
            }
            
            # Define sender and target
            assistant_sender = "orchestrator_graph.llm"
            assistant_target = "orchestrator_graph.cli"
            
            # Add message to conversation state first
            if self.conversation_state:
                self.conversation_state.add_message(
                    MessageRole.ASSISTANT,
                    response_text,
                    assistant_metadata
                )
            
            # Add message to database
            self.db.add_message(
                self.session_id, 
                "assistant", 
                response_text, 
                metadata=assistant_metadata,
                sender=assistant_sender,
                target=assistant_target
            )
            
            logger.debug(f"Stored tool completion and response in database")
        except Exception as e:
            error_msg = f"Failed to store tool completion: {e}"
            logger.error(error_msg)
            print(error_msg)
        
        return {
            "response": response_text,
            "has_tool_results": True,
            "tool_completed": tool_name,
            "request_id": request_id
        }

    def _is_conversation_end(self, text: str) -> bool:
        """Check if a response text indicates the end of a conversation."""
        goodbye_phrases = [
            "goodbye", "bye", "farewell", "take care", "until next time",
            "have a good day", "have a great day", "see you later"
        ]
        lowercase_text = text.lower()
        return any(phrase in lowercase_text for phrase in goodbye_phrases)

    def check_pending_tools(self) -> Optional[Dict[str, Any]]:
        """Check if any pending tool requests have completed and process them."""
        # Import the tool utilities
        from src.agents.orchestrator_tools import PENDING_TOOL_REQUESTS
        
        # Run the check for completed tool requests
        from src.agents.orchestrator_tools import check_completed_tool_requests
        check_completed_tool_requests()
        
        # Check if any pending requests exist in our instance
        for request_id, user_input in list(self.pending_requests.items()):
            # Check if the request has been completed
            request_info = PENDING_TOOL_REQUESTS.get(request_id, {})
            if request_info.get('status') == 'completed':
                # Process the completed request
                logger.info(f"Found completed tool request: {request_id}")
                # Remove from our pending requests
                del self.pending_requests[request_id]
                
                # Return the completed request information
                return {
                    'request_id': request_id,
                    'user_input': user_input,
                    'response': request_info.get('response', {})
                }
        
        # No completed requests found
        return None

def main():
    """Main function to run the LLM agent in a chat loop."""
    agent = LLMQueryAgent()
    logger.debug("Starting LLM Agent CLI")
    print("Initializing LLM Agent...")
    
    # Handle conversation selection
    print("\nConversation options:")
    print("1. Start a new conversation")
    print("2. Continue an existing conversation")
    
    choice = input("Enter your choice (1/2): ").strip()
    
    if choice == "2":
        # List available conversations
        conversations = agent.list_conversations(limit=10)
        
        if not conversations:
            print("No existing conversations found. Starting a new one.")
            title = input("\nGive your conversation a meaningful title (optional): ").strip()
            agent.start_conversation(title=title if title else None)
        else:
            # Display conversations in an enhanced format
            print("\n=== Available Conversations ===")
            for i, conv in enumerate(conversations, 1):
                # Get the name (or "null" if not present)
                name = "null" if conv.title is None else conv.title
                
                # Format the timestamp using ISO format
                try:
                    if hasattr(conv, 'updated_at') and conv.updated_at:
                        # Use ISO format without microseconds for readability
                        dt = conv.updated_at
                        if isinstance(dt, datetime):
                            updated = dt.isoformat().split('.')[0]  # Remove microseconds
                        else:
                            updated = str(dt)[:19]  # Get just the date and time part
                    else:
                        updated = "unknown"
                except (AttributeError, TypeError):
                    updated = str(conv.updated_at)[:19] if conv.updated_at else "unknown"
                
                # Print in exactly the format specified
                print(f"{i}. Conversation Name: {name} Last Updated: {updated}")
                
                # Add separator between conversations
                print("   " + "-" * 50)
            
            conv_choice = input("\nEnter conversation number to continue (or 'n' for new): ").strip()
            
            if conv_choice.lower() == 'n':
                title = input("\nGive your conversation a meaningful title (optional): ").strip()
                agent.start_conversation(title=title if title else None)
            else:
                try:
                    idx = int(conv_choice) - 1
                    if 0 <= idx < len(conversations):
                        agent.continue_conversation(conversations[idx].session_id)
                    else:
                        print("Invalid selection. Starting a new conversation.")
                        title = input("\nGive your conversation a meaningful title (optional): ").strip()
                        agent.start_conversation(title=title if title else None)
                except ValueError:
                    print("Invalid input. Starting a new conversation.")
                    title = input("\nGive your conversation a meaningful title (optional): ").strip()
                    agent.start_conversation(title=title if title else None)
    else:
        # Start a new conversation with improved title prompt
        title = input("\nGive your conversation a meaningful title (optional): ").strip()
        agent.start_conversation(title=title if title else None)
        
    # Display capabilities and commands
    print("\nYou can start chatting with the agent. Type 'exit' to quit.")
    print("\nRonan can:")
    print("- Answer general questions and chat directly")
    print("- Tell jokes and stories")
    print("- Use specialized tools when needed:")
    print("  * valet: Check schedule, staff tasks, and personal messages")
    print("  * personal_assistant: Handle emails and manage to-do lists")
    print("  * librarian: Perform research and documentation tasks")
    print("\nCommands:")
    print("- Type 'rename' to change the title of the current conversation")
    print("- Type 'exit' to quit the conversation")
    print("\nTools will process asynchronously so you can continue chatting while they work.")
    print("When a tool completes, you'll see its response automatically.")
    
    # Main chat loop
    while True:
        user_input = input("\nYou: ").strip()
        
        # Check for special commands
        if user_input.lower() in ['exit', 'quit', 'bye']:
            logger.debug("User requested exit. Shutting down.")
            print("Goodbye!")
            break
        
        elif user_input.lower() == 'rename':
            # Rename the current conversation
            if agent.session_id:
                current_title = "Untitled"
                if agent.conversation_state and agent.conversation_state.metadata.title:
                    current_title = agent.conversation_state.metadata.title
                print(f"\nCurrent title: {current_title}")
                new_title = input("Enter new title: ").strip()
                if new_title:
                    if agent.rename_conversation(new_title):
                        print(f"Conversation renamed to '{new_title}'")
                    else:
                        print("Failed to rename conversation. Please try again.")
                else:
                    print("Title unchanged (empty title provided)")
            else:
                print("No active conversation to rename.")
            continue  # Skip processing as a regular message
        
        # Use the full chat flow
        logger.debug("Processing user input")
        result = agent.chat(user_input)
        logger.debug("Received response from agent")
        
        # Print the main response without duplicate logging
        if result.get("has_tool_results"):
            print(f"\nAgent: {result['response']}")
            # Print tool request information
            if result.get("tool_requests"):
                for req in result["tool_requests"]:
                    request_id = req["request_id"]
                    agent.pending_requests[request_id] = user_input
                    print(f"- Tool request sent: {req['tool']} (request {request_id})")
        else:
            print(f"\nAgent: {result['response']}")

if __name__ == "__main__":
    main() 
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
    PENDING_TOOL_REQUESTS,
    check_pending_tool_requests
)
from src.graphs.orchestrator_graph import create_initial_state, StateManager

# Load environment variables
load_dotenv(override=True)

# Setup basic logging
logger = logging.getLogger(__name__)

# Load common configuration
config = Configuration()

# Setup logging
# try:
#     # Initialize logging
#     file_handler, console_handler = setup_logging(config)
#     
#     # Add handlers to logger
#     logger.addHandler(file_handler)
#     logger.addHandler(console_handler)
#     
#     logger.debug("Logging initialized successfully")
# except Exception as e:
#     print(f"Error setting up logging: {e}")
#     # Setup basic logging as fallback
#     logging.basicConfig(level=logging.INFO)

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
            logger.error(error_msg)
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
            logger.info(f"Agent attempting to continue conversation with session ID: {session_id} (type: {type(session_id).__name__})")
            print(f"DEBUG: Attempting to continue conversation with session ID: {session_id} (type: {type(session_id).__name__})")
            
            # Try to continue the conversation
            self.conversation_state = self.db.continue_conversation(session_id)
            
            if self.conversation_state:
                logger.info(f"Successfully continued conversation with session ID: {session_id}")
                
                # Initialize graph state for the continued conversation
                self.graph_state = create_initial_state()
                self.state_manager = StateManager(self.graph_state)
                
                return True
            else:
                error_msg = f"Failed to continue conversation: session {session_id} not found"
                logger.error(error_msg)
                print(error_msg)  # Print to console for visibility
        except Exception as e:
            error_msg = f"Failed to continue conversation: {e}"
            logger.error(error_msg)
            print(f"DEBUG ERROR: {type(e).__name__}: {str(e)}")  # Print detailed error for debugging
        
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
        
        base_prompt = f"""You are Ronan, an intelligent assistant with access to specialized tools.
                    You can respond directly to most questions and requests, including general knowledge questions, 
                    jokes, casual conversation, and basic assistance.

                    ONLY use tools when you need specific information that you don't have or when the user explicitly
                    requests something that requires one of your specialized tools. 

                    Tool usage guidelines:
                    - personal_assistant: Use for emails, to-do lists, calendar events, scheduling, and any personal organization
                    - valet: Use for staff management, home logistics, and internal messaging
                    - librarian: Use for research and documentation tasks
                    
                    For example:
                    - If asked for a joke, tell a joke directly
                    - If asked for general information, answer directly
                    - If asked about the weather, admit you don't have current weather data
                    - If asked to send an email or check your schedule, use personal_assistant
                    - If asked about staff or home management, use valet
                    - If asked to research a topic, use librarian

                    IMPORTANT: When using a tool, DO NOT fabricate a response from the tool.
                    ONLY use the exact format shown in the examples below and wait for the system to execute the tool.
                    DO NOT write responses as if coming from the tool - the system will provide those.

                    Conversation Context:
                    {context}

                    User: {user_input}
                    Agent:"""

        # Add tool descriptions to the prompt
        enhanced_prompt = add_tools_to_prompt(base_prompt)
        
        # Add previous tool results if available
        if self.last_tool_results:
            enhanced_prompt = f"{enhanced_prompt}\n\n{self.last_tool_results}"
            
        return enhanced_prompt

    def get_conversation_context(self) -> str:
        """Get conversation context if database is available."""
        try:
            recent_messages = self.db.get_recent_messages(self.session_id)
            logger.debug(f"Retrieved {len(recent_messages)} messages for context")
            
            # The db_manager.get_recent_messages already converts the column names to role/message
            return "\n".join([f"{msg['role']}: {msg['message']}" for msg in recent_messages])
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
            # LLM call via Ollama API
            logger.info(f"Payload sent to LLM (first 100 chars): {json.dumps(payload)[:100]}...")  # Log just first 100 chars
            logger.debug(f"Querying LLM model: {self.model}")
            
            # Print payload for debugging - first 100 chars only
            print(f"Payload (first 100 chars): {json.dumps(payload)[:100]}...")
            
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            response_json = response.json()
            response_text = response_json.get('response', 'No response from LLM')
            
            # Print response for debugging - first 100 chars only
            print(f"Response (first 100 chars): {json.dumps(response_json)[:100]}...")
            
            logger.info(f"Response received from LLM (first 100 chars): {json.dumps(response_json)[:100]}...")  # Log just first 100 chars
            logger.debug(f"Received response from LLM (length: {len(response_text)})")
            
            return response_text
        except Exception as e:
            error_msg = f"Error querying LLM: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def process_response_with_tools(self, response_text: str) -> Dict[str, Any]:
        """Process LLM response to handle any tool calls."""
        logger.debug("Processing LLM response for tool calls")
        logger.debug(f"Response text: {response_text[:100]}...")  # Log the first 100 characters of the response
        
        # Check for hallucinated tool responses - patterns like "tool_name: result" or "tool(...): result"
        hallucination_patterns = [
            r'`([a-zA-Z_\.]+)_tool:\s+(.*?)`',  # `tool_name_tool: result`
            r'([a-zA-Z_]+)\s*\([^)]*\)\s*:\s+(.*)',  # tool(...): result
            r'([a-zA-Z_]+)\s+tool\s+response:\s+(.*)',  # tool name tool response: result
            r'orchestrator_graph\.([a-zA-Z_]+)_tool:\s+(.*)'  # orchestrator_graph.tool_name_tool: result
        ]
        
        # Check if the response contains hallucinated tool outputs
        hallucinated = False
        for pattern in hallucination_patterns:
            if re.search(pattern, response_text, re.IGNORECASE):
                hallucinated = True
                logger.warning(f"Detected hallucinated tool output in response: {response_text[:100]}...")
                break
        
        if hallucinated:
            # We need to re-prompt with stronger instructions against hallucination
            # Return an empty result that will trigger the appropriate handling
            return {
                "tool_calls": [],
                "execution_results": [],
                "hallucinated": True,
                "original_response": response_text
            }
            
        # Handle any tool calls in the response
        processing_result = handle_tool_calls(response_text)
        
        # Log the processing result
        logger.debug(f"Processing result: {processing_result}")
        
        # Format tool results for the next prompt if there were any tool calls
        if processing_result["tool_calls"]:
            logger.debug(f"Found {len(processing_result['tool_calls'])} tool calls in response")
            self.last_tool_results = format_tool_results(processing_result)
            
            # Log tool execution
            for result in processing_result["execution_results"]:
                tool_name = result["name"]
                result_msg = result["result"]["message"]
                logger.debug(f"Executed {tool_name}: {result_msg[:50]}...")
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
            result["tool_requests"] = [
                {
                    "tool": r["name"],
                    "request_id": r.get("request_id", "unknown"),
                    "message": r["result"]["message"]
                }
                for r in processing_result["execution_results"]
            ]
                
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
        logger.debug(f"Handling tool completion for request ID: {request_id}")
        
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
    print("- Type 'check tools' to check if any tool requests have been completed")
    print("- Type 'rename' to change the title of the current conversation")
    print("- Type 'exit' to quit the conversation")
    print("\nTry asking for a joke or general question first, then try asking about your schedule or email.\n")
    
    # Keep track of pending requests
    pending_requests = {}
    
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
        
        elif user_input.lower() == 'check tools':
            # Check for completed tool requests
            completed_requests = check_pending_tool_requests()
            
            if not completed_requests:
                # Show pending requests with their elapsed time
                pending_count = len([r for r in PENDING_TOOL_REQUESTS.values() if r["status"] == "pending"])
                
                if pending_count > 0:
                    print(f"You have {pending_count} pending tool requests that are still processing.")
                    print("Pending requests:")
                    
                    current_time = datetime.now()
                    for req_id, req in PENDING_TOOL_REQUESTS.items():
                        if req["status"] == "pending":
                            created_time = datetime.fromisoformat(req["created_at"])
                            elapsed_seconds = (current_time - created_time).total_seconds()
                            tool_name = req["name"]
                            
                            # Calculate remaining time (assuming 10 second delay)
                            remaining = max(0, 10 - elapsed_seconds)
                            print(f"- {tool_name} (Request ID: {req_id}): {elapsed_seconds:.1f}s elapsed, ~{remaining:.1f}s remaining")
                    
                    print("\nThe requests will complete in approximately 10 seconds. Please check again soon.")
                else:
                    print("No pending tool requests found.")
            else:
                print(f"Found {len(completed_requests)} completed tool requests:")
                
                for i, request in enumerate(completed_requests, 1):
                    request_id = request["request_id"]
                    tool_name = request["name"]
                    
                    print(f"{i}. {tool_name} (Request ID: {request_id})")
                
                # Ask which request to process
                if completed_requests:
                    req_choice = input("Enter request number to process (or press Enter to skip): ").strip()
                    
                    if req_choice and req_choice.isdigit():
                        try:
                            idx = int(req_choice) - 1
                            if 0 <= idx < len(completed_requests):
                                # Process the completed request
                                req = completed_requests[idx]
                                request_id = req["request_id"]
                                
                                # Get the original query from pending_requests or use a default
                                original_query = pending_requests.get(request_id, "your previous request")
                                
                                # Process the tool completion
                                result = agent.handle_tool_completion(request_id, original_query)
                                
                                # Print the response
                                print(f"\nAgent: {result['response']}")
                                
                                # Remove from pending requests
                                if request_id in pending_requests:
                                    del pending_requests[request_id]
                        except (ValueError, IndexError):
                            print("Invalid selection.")
            
            # Continue to next iteration
            continue
            
        # Use the full chat flow
        logger.debug("Processing user input")
        result = agent.chat(user_input)
        logger.debug("Received response from agent")
        
        # Print the main response
        print(f"\nAgent: {result['response']}")
        
        # Store any new pending requests
        if result.get("tool_requests"):
            for req in result["tool_requests"]:
                request_id = req["request_id"]
                pending_requests[request_id] = user_input
                
            print("\nPending Tool Requests:")
            for req in result["tool_requests"]:
                print(f"- {req['tool']} (Request ID: {req['request_id']})")
            print("\nType 'check tools' to check if these requests have completed.")

if __name__ == "__main__":
    main() 
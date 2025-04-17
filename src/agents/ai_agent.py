import json
from dotenv import load_dotenv
import requests
import os
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import re
import time
import sys
import threading

# Add platform-specific imports for non-blocking input
if os.name == 'nt':  # Windows
    import msvcrt
else:  # Unix/Linux/MacOS
    import select
    import termios
    import tty

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
    check_completed_tool_requests,
    start_tool_checker
)
from src.graphs.orchestrator_graph import create_initial_state, StateManager

# Import tool initialization
from src.tools.initialize_tools import initialize_tool_dependencies
from src.agents.base_agent import BaseAgent

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
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.debug("Logging initialized successfully")
except Exception as e:
    print(f"Error setting up logging: {e}")
    logging.basicConfig(level=logging.INFO)

class LLMQueryAgent(BaseAgent):
    def __init__(self, config: Configuration = config):
        """Initialize the LLM Query Agent with configuration."""
        super().__init__(
            name="orchestrator",
            prompt_section="",
            api_url=config.ollama_api_url + '/api/generate',
            model=config.ollama_model
        )
        self.config = config
        self.api_url = config.ollama_api_url + '/api/generate'
        self.model = config.ollama_model
        # Initialize database (already in BaseAgent, but keep for compatibility)
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
        logger.debug(f"Initializing LLM Agent with model: {self.model}")
        logger.debug(f"API URL: {self.api_url}")
        
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
            logger.debug(f"Agent attempting to continue conversation with session ID: {session_id} (type: {type(session_id).__name__})")
            self.conversation_state = self.db.continue_conversation(session_id)
            if self.conversation_state:
                logger.debug(f"Successfully continued conversation with session ID: {session_id}")
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
        # but also emphasizing conversational abilities
        base_prompt = f"""You are a helpful AI assistant named Ronan with a friendly, conversational tone. You can directly answer questions AND you have access to specialized tools when needed.

CONVERSATION INSTRUCTIONS:
1. Answer questions directly and conversationally for general knowledge, jokes, explanations, etc.
2. Be engaging, informative, and concise in your responses.
3. Only use tools when the user's request specifically requires specialized functionality.

TOOL USAGE INSTRUCTIONS:
1. Use tools ONLY when necessary for specific tasks that require them.
2. KEYWORD TRIGGER FORMAT: When the user's message starts with "tool, [tool_name], [task]", you MUST:
   - Extract the tool name and task
   - Call the specified tool using the format: `tool_name(task="task")`
3. When using a tool, use EXACTLY this format: `tool_name(task="your request")`
4. NEVER make up or hallucinate tool results. Wait for actual results.

# AVAILABLE TOOLS

## librarian
Performs research, documentation crawling, and knowledge management.
Example: `librarian(task="Ask for an update")`

When you need to use a tool, say "I'll use the [tool name] tool to [brief description of task]" 
followed by the tool call using the proper syntax.

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
    
    def get_llm_response(self, user_input: str) -> str:
        """
        Generate a prompt from user input and query the LLM.
        
        Args:
            user_input: The user's message
            
        Returns:
            The LLM's response text
        """
        # Generate prompt with tools and context
        prompt = self.generate_prompt(user_input)
        
        # Query LLM with the prompt
        return self.query_llm(prompt)

    def log_message(self, message: str, level: str = "info") -> None:
        """
        Log a message at the specified level.
        
        Args:
            message: The message to log
            level: The logging level (debug, info, warning, error, critical)
        """
        if level == "debug":
            logger.debug(message)
        elif level == "info":
            logger.info(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
        elif level == "critical":
            logger.critical(message)
        else:
            logger.info(message)
            
    def store_tool_requests(self, execution_results: List[Dict[str, Any]]) -> None:
        """
        Store tool requests in the conversation history.
        
        Args:
            execution_results: List of tool execution results
        """
        if not self.has_db or not self.conversation_state:
            logger.warning("Cannot store tool requests: database or conversation state not available")
            return
            
        for result in execution_results:
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
            
            # Add message to conversation state
            if self.conversation_state:
                self.conversation_state.add_message(
                    MessageRole.TOOL,
                    "Tool request submitted",
                    tool_metadata
                )
            
            # Define sender and target for the tool message
            tool_sender = f"orchestrator_graph.{tool_name}_tool"
            tool_target = "orchestrator_graph.llm"
            
            # Add message to database
            self.db.add_message(
                self.session_id, 
                "tool", 
                "Tool request submitted", 
                metadata=tool_metadata,
                sender=tool_sender,
                target=tool_target
            )
        
        logger.debug(f"Stored {len(execution_results)} tool requests in database")

    def process_llm_response(self, response_text: str, user_input: str) -> str:
        """Process the LLM response for tool calls and handle results."""
        self.log_message(f"Processing LLM response for tool calls", level="debug")
        self.log_message(f"Response text (first 300 chars): {response_text[:300]}", level="debug")
        
        # Check if this is a direct request for tool usage
        is_direct_tool_request = user_input.strip().lower().startswith("tool,")
        
        # For direct tool requests or if response contains valid tool call pattern
        # Look for both the explicit backtick format and the descriptive format
        has_tool_pattern = bool(re.search(r"(^|\n)`\w+\(task=\"[^\"]+\"\)`", response_text) or 
                               re.search(r"I'll use the (\w+) tool to", response_text))
        self.log_message(f"Has valid tool call pattern: {has_tool_pattern}", level="debug")
        
        # Only extract and execute tool calls if it's a direct tool request or the response
        # has a valid tool call pattern
        if is_direct_tool_request or has_tool_pattern:
            # Extract and execute tool calls
            self.log_message("Calling handle_tool_calls to extract tool calls from response", level="debug")
            processing_result = handle_tool_calls(response_text, user_input)
            
            if processing_result["tool_calls"]:
                self.log_message(f"Processing result tool_calls: {processing_result['tool_calls']}", level="debug")
                self.log_message(f"Found {len(processing_result['tool_calls'])} tool calls in response", level="debug")
                
                # Log tool execution results
                for result in processing_result["execution_results"]:
                    status = result["result"].get("status", "unknown")
                    self.log_message(
                        f"Tool {result['name']} request {result['request_id']} executed with status: {status}",
                        level="info"
                    )
                
                # Store tool requests in database
                try:
                    self.store_tool_requests(processing_result["execution_results"])
                    self.log_message(f"Stored {len(processing_result['execution_results'])} tool requests in database", level="debug")
                except Exception as e:
                    self.log_message(f"Failed to store tool requests: {e}", level="error")
                
                # Return acknowledgment message
                self.log_message("Tools were used - returning acknowledgment message", level="debug")
                return "I've processed your request and started the tool. Please wait for results to appear automatically..."
        
        # For regular conversational responses with no tool calls
        if not is_direct_tool_request and not has_tool_pattern:
            self.log_message("No tool calls found - returning original response", level="debug")
        else:
            self.log_message("No tool calls found in response", level="debug")
            
        return response_text

    def chat(self, user_input: str, request_id: Optional[str] = None) -> Dict[str, str]:
        """
        Process a chat message from the user and return a response.
        
        Args:
            user_input: The user's message
            request_id: Optional request ID for tracking
            
        Returns:
            Dict containing the response text and status
        """
        try:
            # Check if this is a direct tool request
            is_direct_tool_request = user_input.strip().lower().startswith("tool,")
            
            # Get initial response from LLM
            initial_response_text = self.get_llm_response(user_input)
            
            # For direct tool requests, force tool processing
            if is_direct_tool_request:
                self.log_message(f"Direct tool request detected: {user_input[:50]}...", level="debug")
                response_text = self.process_llm_response(initial_response_text, user_input)
                
                # Add tool tracking for direct tool requests
                if user_input.strip().lower().startswith("tool,"):
                    # Extract tool name from input
                    parts = user_input.split(",", 2)
                    if len(parts) >= 3:
                        tool_name = parts[1].strip()
                        # Log that we're tracking this tool request
                        self.log_message(f"Tracking tool request for {tool_name}", level="debug")
                        
                        # Check for any new tool requests in the PENDING_TOOL_REQUESTS dictionary
                        for req_id, req_info in PENDING_TOOL_REQUESTS.items():
                            # Find the most recent request ID that matches our tool
                            if req_info.get("status") == "pending" and not req_id in self.pending_requests:
                                self.log_message(f"Adding pending request {req_id} to tracking", level="debug")
                                # Store the original user input with the request ID
                                self.pending_requests[req_id] = user_input
                                break
            else:
                # For conversational messages, check if the response tries to use a tool
                has_tool_pattern = bool(re.search(r"(^|\n)`\w+\(task=\"[^\"]+\"\)`", initial_response_text) or 
                                      re.search(r"I'll use the (\w+) tool to", initial_response_text))
                
                if has_tool_pattern:
                    # Process the response for tool calls
                    self.log_message(f"Tool pattern detected in response, processing", level="debug")
                    response_text = self.process_llm_response(initial_response_text, user_input)
                else:
                    # For purely conversational responses, just return the LLM's response directly
                    self.log_message(f"Conversational response with no tool pattern", level="debug")
                    response_text = initial_response_text
            
            # Return successful response
            return {
                "status": "success",
                "response": response_text
            }
            
        except Exception as e:
            error_msg = f"Error processing chat message: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error", 
                "response": error_msg
            }

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
        logger.debug(f"Generated tool completion prompt: {prompt[:100]}...")
        
        # Query the LLM with the tool results
        response_text = self.query_llm(prompt)
        logger.debug(f"Generated LLM response: {response_text[:100]}...")
        
        # Store the tool completion message if DB available
        try:
            # Get the tool and response details
            tool_details = PENDING_TOOL_REQUESTS.get(request_id, {})
            tool_name = tool_details.get("name", "unknown")
            
            # Get the tool response message
            if isinstance(tool_details, dict):
                tool_response = tool_details.get("message", str(tool_details))
            else:
                tool_response = str(tool_details)
            
            logger.debug(f"Tool response: {tool_response[:100]}...")
            
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
        # Log check time for timeline tracking
        check_time = datetime.now()
        logger.debug(f"[{check_time.isoformat()}] Checking for completed tool requests...")
        
        # Run the check for completed tool requests
        completed = check_completed_tool_requests()
        if completed:
            logger.info(f"[{check_time.isoformat()}] Found {len(completed)} completed requests from check_completed_tool_requests")
        
        # Log all pending requests for debugging
        logger.debug(f"[{check_time.isoformat()}] Current pending requests in agent: {list(self.pending_requests.keys())}")
        logger.debug(f"[{check_time.isoformat()}] All pending tool requests: {list(PENDING_TOOL_REQUESTS.keys())}")
        
        # Check if any pending requests exist in our instance
        for request_id, user_input in list(self.pending_requests.items()):
            logger.debug(f"[{check_time.isoformat()}] Checking pending request: {request_id}")
            
            # Check if the request has been completed
            request_info = PENDING_TOOL_REQUESTS.get(request_id, {})
            logger.debug(f"[{check_time.isoformat()}] Request info for {request_id}: status={request_info.get('status', 'unknown')}")
            
            # Check for both 'completed' and 'success' status
            if request_info.get('status') in ['completed', 'success', 'error']:
                # Process the completed request
                logger.info(f"[{check_time.isoformat()}] Found completed tool request: {request_id} with status: {request_info.get('status')}")
                # Remove from our pending requests
                del self.pending_requests[request_id]
                
                # Return the completed request information
                return {
                    'request_id': request_id,
                    'user_input': user_input,
                    'response': request_info
                }
            else:
                logger.debug(f"[{check_time.isoformat()}] Request {request_id} not completed yet, status: {request_info.get('status', 'unknown')}")
        
        # No completed requests found
        logger.debug(f"[{check_time.isoformat()}] No completed tool requests found")
        return None

def process_completed_tool_request(request):
    """
    Process a completed tool request and format the result for display.
    
    Args:
        request: Dictionary containing the tool request data
        
    Returns:
        Formatted string result for display
    """
    logger.debug(f"Processing completed tool request: {request}")
    
    # Extract request details
    request_id = request.get('request_id', 'unknown')
    tool_details = request.get('response', {})
    
    # Extract tool name and result message
    tool_name = tool_details.get('name', 'unknown')
    
    # Try to get the message from various possible locations
    message = None
    if 'message' in tool_details:
        message = tool_details['message']
    elif 'response' in tool_details and isinstance(tool_details['response'], dict):
        message = tool_details['response'].get('message')
    elif isinstance(tool_details, dict) and 'result' in tool_details:
        result = tool_details['result']
        if isinstance(result, dict) and 'message' in result:
            message = result['message']
    
    # Fallback to a generic message if we couldn't find one
    if not message:
        message = f"Request {request_id} completed with status: {tool_details.get('status', 'unknown')}"
    
    # Add the tool name to the request for reference in the caller
    request['tool_name'] = tool_name
    
    return message

def main():
    """
    Main function to start the interactive session with the AI assistant.
    Implements a non-blocking input method to check for tool responses while waiting for user input.
    """
    logger = logging.getLogger(__name__)
    
    # Start the tool checker thread
    start_tool_checker()
    
    # Initialize AI agent with conversation history from DB
    ai_agent = LLMQueryAgent()
    
    # Check for and process any tool results that completed while the agent was offline
    completed_requests = check_completed_tool_requests()
    if completed_requests:
        logger.info(f"Found {len(completed_requests)} completed tool requests that occurred while offline")
        # Convert dictionary to list for processing
        completed_list = []
        for req_id, req_data in completed_requests.items():
            completed_list.append({
                'request_id': req_id,
                'response': req_data
            })
        
        for request in completed_list:
            result = process_completed_tool_request(request)
            print(f"\nTool '{request['tool_name']}' completed: {result}")
    
    print(f"Starting chat with AI assistant. Type 'exit' to quit or 'rename' to change the session name.")
    print(f"To use a tool directly, type: tool,tool_name,your request")
    session_name = f"CLI-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    print(f"Current session name: {session_name}")
    
    # Start a new conversation with the session name
    ai_agent.start_conversation(session_name)
    
    buffer = ""
    input_prompt = "> "
    poll_interval = 0.1  # seconds between checks for tool completions
    last_tool_check = time.time()
    
    # Function to clear the current line and restore the prompt with buffer
    def refresh_input_line():
        if os.name == 'nt':  # Windows
            # Use carriage return to go to start of line
            sys.stdout.write('\r' + ' ' * (len(input_prompt) + len(buffer)) + '\r')
        else:  # Unix/Linux/MacOS
            # ANSI escape sequence to clear line
            sys.stdout.write('\033[2K\r')
        sys.stdout.write(input_prompt + buffer)
        sys.stdout.flush()
    
    while True:
        # Check for completed tool requests periodically
        current_time = time.time()
        if current_time - last_tool_check > poll_interval:
            completed_requests = check_completed_tool_requests()
            if completed_requests:
                logger.info(f"Found {len(completed_requests)} new completed tool requests")
                
                # Clear the current input line
                refresh_input_line()
                
                # Process and display the completed tool results
                # Convert dictionary to list for processing
                completed_list = []
                for req_id, req_data in completed_requests.items():
                    completed_list.append({
                        'request_id': req_id,
                        'response': req_data
                    })
                
                print("\n===== TOOL RESULTS AVAILABLE =====")
                for request in completed_list:
                    result = process_completed_tool_request(request)
                    print(f"Tool '{request['tool_name']}' completed with result:")
                    print(f"{result}")
                print("=================================\n")
                
                # Redisplay the input prompt with the current buffer
                refresh_input_line()
            
            last_tool_check = current_time
        
        # Non-blocking input check
        if os.name == 'nt':  # Windows
            if msvcrt.kbhit():
                char = msvcrt.getwch()
                if char == '\r':  # Enter key
                    print()  # Move to next line
                    user_input = buffer
                    buffer = ""
                    
                    # Process the input
                    if user_input.lower() == 'exit':
                        print("Exiting.")
                        break
                    elif user_input.lower() == 'rename':
                        print("Enter new session name:")
                        session_name = input()
                        ai_agent.rename_conversation(session_name)
                        print(f"Session renamed to: {session_name}")
                        continue
                    
                    # Process normal input
                    if user_input.strip():
                        try:
                            # Use the chat method which handles both conversation and tool processing
                            result = ai_agent.chat(user_input)
                            print(result["response"])
                        except Exception as e:
                            logger.error(f"Error processing request: {e}")
                            print(f"Error processing request: {e}")
                elif char == '\b':  # Backspace
                    if buffer:
                        buffer = buffer[:-1]
                        # Redraw the line with updated buffer
                        refresh_input_line()
                else:  # Regular character
                    buffer += char
                    sys.stdout.write(char)
                    sys.stdout.flush()
        else:  # Unix/Linux/MacOS
            rlist, _, _ = select.select([sys.stdin], [], [], poll_interval)
            if rlist:
                # Set terminal to raw mode
                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    tty.setraw(sys.stdin.fileno())
                    char = sys.stdin.read(1)
                finally:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                
                if char == '\r' or char == '\n':  # Enter key
                    print()  # Move to next line
                    user_input = buffer
                    buffer = ""
                    
                    # Process the input
                    if user_input.lower() == 'exit':
                        print("Exiting.")
                        break
                    elif user_input.lower() == 'rename':
                        print("Enter new session name:")
                        new_name = input()
                        ai_agent.rename_conversation(new_name)
                        print(f"Session renamed to: {new_name}")
                        continue
                    
                    # Process normal input
                    if user_input.strip():
                        try:
                            # Use the chat method which handles both conversation and tool processing
                            result = ai_agent.chat(user_input)
                            print(result["response"])
                        except Exception as e:
                            logger.error(f"Error processing request: {e}")
                            print(f"Error processing request: {e}")
                elif char == '\x7f' or char == '\b':  # Backspace
                    if buffer:
                        buffer = buffer[:-1]
                        # Redraw the line with updated buffer
                        refresh_input_line()
                else:  # Regular character
                    buffer += char
                    sys.stdout.write(char)
                    sys.stdout.flush()
        
        # Small sleep to prevent CPU spinning
        time.sleep(0.01)

if __name__ == "__main__":
    setup_logging()
    main() 
from src.agents.ai_agent import LLMQueryAgent
from src.graphs.orchestrator_graph import create_initial_state, StateManager
from src.graphs.orchestrator_graph import TaskStatus, MessageRole
from src.agents.orchestrator_tools import TOOL_DEFINITIONS, PENDING_TOOL_REQUESTS
from datetime import datetime
import logging
import time
import sys
import os
import threading
import traceback

# Setup logger
logger = logging.getLogger(__name__)

"""
CLI Tool Request Polling Architecture
------------------------------------

In a command-line interface application, we face a fundamental challenge with asynchronous 
operations due to the inherently synchronous nature of terminal I/O:

1. User input through the terminal's `input()` function is blocking and event-driven. 
   When a user types and presses Enter, the program receives this input as a discrete event.

2. However, background processes (like our tools executing asynchronously) have no native way 
   to interrupt and insert their response into this I/O flow. Unlike GUI applications with 
   event loops or web servers with websockets, a CLI application has no built-in mechanism 
   for background events to notify the foreground process.

3. Therefore, we implement polling as a simple solution - regularly checking if any background 
   tool operations have completed while maintaining a responsive CLI experience.

In more sophisticated applications, this limitation might be addressed with:
- Event queues with proper event loops
- Signal handlers
- Dedicated worker processes with IPC
- WebSocket-based communication for real-time events

For our CLI application, polling provides a straightforward way to simulate asynchronous 
events without requiring complex threading or event handling architectures.
"""

def check_completed_tools(agent, user_input=""):
    """
    Check for completed tool operations.
    
    Args:
        agent: The AI agent which might have pending tool operations
        user_input: The current user input (for contextual responses)
        
    Returns:
        Bool: True if any completions were found, False otherwise
    """
    completed_found = False
    try:
        # This function is called repeatedly as a polling mechanism
        completed_requests = agent.check_pending_tools()
        if completed_requests:
            logger.debug(f"TRACKING: Tool completions found: {len(completed_requests)}")
            logger.debug(f"TRACKING: Tool completions type: {type(completed_requests).__name__}")
            logger.debug(f"TRACKING: Tool completions data: {completed_requests}")
            logger.debug(f"TRACKING: Agent pending_requests keys: {list(agent.pending_requests.keys())}")
            
            # Clear the line before showing any tool completions
            sys.stdout.write("\r\033[K")  # Clear the current line
            sys.stdout.flush()
            print("")  # Add a blank line for visual separation
            
            for completion in completed_requests:
                try:
                    # Log the completion data for debugging
                    logger.debug(f"TRACKING: Processing completion: {completion}")
                    
                    request_id = completion.get("request_id")
                    logger.debug(f"TRACKING: Extracted request_id: {request_id}")
                    
                    if not request_id:
                        print("\n") # Add newline before warning
                        logger.error(f"No request_id in completion: {completion}")
                        continue
                    
                    if request_id not in agent.pending_requests:
                        print("\n") # Add newline before warning
                        logger.warning(f"Request ID {request_id} not found in agent's pending_requests")
                        # Check if it exists in global PENDING_TOOL_REQUESTS
                        from src.agents.orchestrator_tools import PENDING_TOOL_REQUESTS
                        if request_id in PENDING_TOOL_REQUESTS:
                            logger.debug(f"TRACKING: Request ID {request_id} found in global PENDING_TOOL_REQUESTS but not in agent.pending_requests")
                            logger.debug(f"TRACKING: PENDING_TOOL_REQUESTS[{request_id}] = {PENDING_TOOL_REQUESTS[request_id]}")
                            
                            # FALLBACK FIX: Add the request to agent's pending_requests
                            logger.debug(f"TRACKING: Adding missing request ID {request_id} to agent.pending_requests (recovery fix)")
                            agent.pending_requests[request_id] = "Recovered request"
                            logger.info(f"Fixed missing request ID tracking: {request_id} added to agent.pending_requests")
                        else:
                            continue
                    
                    # Get the response message and details
                    tool_response = completion.get("response", {})
                    if isinstance(tool_response, dict):
                        message = tool_response.get("message", completion.get("message", ""))
                        status = tool_response.get("status", completion.get("status", "unknown"))
                        tool_name = tool_response.get("name", completion.get("name", "unknown tool"))
                    else:
                        message = completion.get("message", "")
                        status = completion.get("status", "unknown")
                        tool_name = completion.get("name", "unknown tool")
                    
                    # Log details for debugging
                    logger.debug(f"Processing tool completion [ID: {request_id}] from {tool_name}: {status}")
                    logger.debug(f"Tool message: {message}")
                    
                    # Format based on status
                    if status == "error":
                        print(f"\n🛑 Tool Error [{tool_name}]: {message}")
                    else:
                        print(f"\n✅ Tool [{tool_name}] completed: {message}")
                    
                    # Get the original user query
                    original_query = agent.pending_requests.get(request_id, "")
                    if original_query and original_query != "Recovered request":
                        # Tell the agent to process the completed tool results
                        try:
                            print(f"\nProcessing tool results...")
                            tool_result = agent.handle_tool_completion(request_id, original_query)
                            if tool_result and "response" in tool_result:
                                print(f"\nAgent: {tool_result['response']}")
                        except Exception as tool_process_error:
                            logger.error(f"Error processing tool results: {tool_process_error}")
                            print(f"\nError processing tool results. Please try a new request.")
                    
                    # Ensure we're on a fresh line for the next input
                    print("\nYou: ", end="", flush=True)
                    
                    # Remove from pending requests to avoid repeated processing
                    if request_id in agent.pending_requests:
                        logger.debug(f"TRACKING: About to remove request {request_id} from agent.pending_requests")
                        old_value = agent.pending_requests[request_id]
                        agent.pending_requests.pop(request_id)
                        logger.debug(f"TRACKING: Removed request {request_id} from agent.pending_requests. Old value: {old_value}")
                        logger.debug(f"TRACKING: Remaining pending_requests keys: {list(agent.pending_requests.keys())}")
                        logger.debug(f"Removed request {request_id} from pending_requests")
                    
                    completed_found = True
                        
                except Exception as e:
                    print("\n") # Add newline before error
                    logger.error(f"Error processing tool completion: {e}")
                    traceback.print_exc()
        
        return completed_found
        
    except Exception as e:
        print("\n") # Add newline before error
        logger.error(f"Error checking completed tools: {e}")
        traceback.print_exc()
        return False

def background_tool_checker(agent, stop_event):
    """Background thread to periodically check for completed tools."""
    logger.debug("Starting background tool checker thread")
    
    while not stop_event.is_set():
        try:
            # Check for completed tools
            completions_found = check_completed_tools(agent)
            
            # If no tools completed, sleep for a short time
            if not completions_found:
                time.sleep(1.0)  # Check every 1 second
        except Exception as e:
            logger.error(f"Error in background tool checker: {e}")
            time.sleep(1.0)  # Continue checking even if there's an error

def main():
    """Main function to run the orchestrator graph with chat functionality."""
    # Check for debug mode flag
    debug_mode = "--debug" in sys.argv or "-d" in sys.argv
    if debug_mode:
        # Set console log level to DEBUG for this session
        from src.config import Configuration
        config = Configuration(console_level="DEBUG")
        # Configure console handler explicitly instead of setting root logger level
        root_logger = logging.getLogger()
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_format = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_format)
        # Clear existing console handlers and add the new one
        root_logger.handlers = [h for h in root_logger.handlers if not isinstance(h, logging.StreamHandler)]
        root_logger.addHandler(console_handler)
        print("Debug mode enabled - showing detailed logs")
    
    agent = LLMQueryAgent()
    print("Initializing LLM Agent...")
    
    # Ensure user ID is set to developer for consistency
    agent.user_id = "developer"
    print(f"Using user ID: {agent.user_id}")
    
    # Initialize the graph state
    graph_state = create_initial_state()
    state_manager = StateManager(graph_state)
    
    # Handle conversation selection
    print("\nConversation options:")
    print("1. Start a new conversation")
    print("2. Continue an existing conversation")
    
    choice = input("Enter your choice (1/2): ").strip()
    
    if choice == "2":
        # List available conversations
        print("\nQuerying for available conversations...")
        print(f"Filtering for conversations belonging to user: '{agent.user_id}'")
        conversations = agent.list_conversations(limit=20)
        
        if not conversations:
            print(f"No conversations found for user '{agent.user_id}'. Starting a new one.")
            title = input("Title (optional): ").strip()
            agent.start_conversation(title=title if title else None)
        else:
            # Print debug info only when needed (commented out for normal usage)
            # print(f"\nFound {len(conversations)} conversations for user '{agent.user_id}'")
            # print("\nDEBUG: All available conversations with session IDs:")
            # for i, conv in enumerate(conversations, 1):
            #     print(f"  {i}. ID: {conv.session_id}, Title: '{conv.title}', Messages: {conv.message_count}")
            
            print("\nAvailable conversations:")
            for i, conv in enumerate(conversations, 1):
                # Get the name (or "null" if not present)
                name = "null" if conv.title is None else conv.title
                
                # Format the timestamp using ISO 8601
                try:
                    if hasattr(conv, 'updated_at') and conv.updated_at:
                        # Use ISO format but show only date and time without microseconds for readability
                        dt = conv.updated_at
                        if isinstance(dt, datetime):
                            updated = dt.isoformat().split('.')[0]  # Remove microseconds
                        else:
                            updated = str(dt)
                    else:
                        updated = "unknown"
                except Exception:
                    updated = "unknown"
                
                # Print in exactly the format specified
                print(f"{i}. Conversation Name: {name} Last Updated: {updated}")
            
            conv_choice = input("\nEnter conversation number to continue (or 'n' for new): ").strip()
            
            if conv_choice.lower() == 'n':
                title = input("Title (optional): ").strip()
                agent.start_conversation(title=title if title else None)
            else:
                try:
                    # Convert input to 0-indexed position in the list
                    idx = int(conv_choice) - 1
                    
                    if 0 <= idx < len(conversations):
                        # Get the conversation at that position
                        selected_conv = conversations[idx]
                        session_id = selected_conv.session_id
                        title = selected_conv.title if selected_conv.title else "Untitled"
                        
                        print(f"Continuing: {title}")
                        
                        # Continue the conversation using the session ID from the selected conversation
                        result = agent.continue_conversation(session_id)
                        
                        if not result:
                            print(f"Couldn't continue conversation with session ID: {session_id}. Starting a new one.")
                    else:
                        print(f"Invalid selection. Please choose 1-{len(conversations)}.")
                        title = input("Starting a new conversation. Title (optional): ").strip()
                        agent.start_conversation(title=title if title else None)
                except ValueError:
                    print("Please enter a number.")
                    title = input("Starting a new conversation. Title (optional): ").strip()
                    agent.start_conversation(title=title if title else None)
    else:
        # Start a new conversation
        title = input("Title (optional): ").strip()
        agent.start_conversation(title=title if title else None)
    
    # Make sure we're using the agent's state manager after conversation selection
    # This ensures we're using the correct state for the selected conversation
    if agent.conversation_state:
        # Reinitialize the state manager with the current conversation state
        state_manager = agent.state_manager
        
        # Get conversation title (if any)
        title = agent.conversation_state.metadata.title
        if title:
            print(f"Ready: {title}")
        else:
            print("Ready.")
    else:
        print("No active conversation.")
        
    # Display capabilities and instructions
    print("\nYou can start chatting with the agent. Type 'exit' to quit.")
    print("\nAvailable commands:")
    print("- exit: Quit the conversation")
    print("- rename: Change the title of the current conversation")
    if debug_mode:
        print("- debug: Print detailed debugging information about the current conversation")
    
    # Start a background thread to periodically check for completed tools
    stop_event = threading.Event()
    tool_checker_thread = threading.Thread(
        target=background_tool_checker,
        args=(agent, stop_event),
        daemon=True  # Make it a daemon so it exits when the main thread exits
    )
    tool_checker_thread.start()
    
    try:
        # Main chat loop
        while True:
            try:
                # Check for completed tools before asking for new input
                tool_completions_found = check_completed_tools(agent)
                
                # Only prompt for input if no tool completions were just displayed
                if not tool_completions_found:
                    # Get user input
                    user_input = input("\nYou: ").strip()
                    
                    # Check for empty input
                    if not user_input:
                        print("Empty input detected. Please enter a command or message.")
                        continue
                        
                    # Check for special commands
                    if user_input.lower() in ['exit', 'quit', 'bye']:
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
                    
                    elif user_input.lower() == 'tools':
                        # Force check for completed tools
                        if not check_completed_tools(agent):
                            print("No completed tool requests found.")
                        continue  # Skip processing as regular message
                        
                    elif user_input.lower() == 'debug' and debug_mode:
                        # Print debug information about the conversation
                        print("\n--- DEBUG INFORMATION ---")
                        print(f"Session ID: {agent.session_id}")
                        print(f"Model: {agent.model}")
                        print(f"Pending requests: {len(agent.pending_requests)}")
                        print(f"Available tools: {list(TOOL_DEFINITIONS.keys())}")
                        print(f"DB available: {agent.has_db}")
                        print("--- END DEBUG INFO ---")
                        continue  # Skip processing as a regular message
                        
                    # Use the full chat flow
                    logger.debug("Processing user input")
                    result = agent.chat(user_input)
                    logger.debug("Received response from agent")
                    
                    # Update the state with the user input and agent response
                    try:
                        state_manager.update_conversation(MessageRole.USER, user_input)
                        state_manager.update_conversation(MessageRole.ASSISTANT, result['response'])
                    except Exception as state_error:
                        # Log state update errors but don't crash
                        logger.error(f"Error updating state: {state_error}")
                    
                    # Print the main response
                    print(f"\nAgent: {result['response']}")
                    
                    # Store any new pending requests from tools
                    if result.get("tool_requests"):
                        print("\nTool requests initiated:")
                        for req in result["tool_requests"]:
                            request_id = req["request_id"]
                            tool_name = req.get("tool", "unknown")
                            status = req.get("status", "unknown")
                            
                            logger.debug(f"TRACKING: Processing tool request: {req}")
                            logger.debug(f"TRACKING: Adding new tool request {request_id} for {tool_name} to agent.pending_requests from chat result")
                            
                            # Ensure we don't overwrite existing values
                            if request_id not in agent.pending_requests:
                                agent.pending_requests[request_id] = user_input
                            else:
                                logger.debug(f"TRACKING: Request ID {request_id} already in pending_requests, not overwriting")
                                
                            logger.debug(f"TRACKING: Updated pending_requests keys: {list(agent.pending_requests.keys())}")
                            
                            # Notify user that a tool is processing in the background
                            print(f"- {tool_name} (request {request_id[:8]}..., status: {status})")
                else:
                    # If tool completions were just displayed, give the user a moment before checking again
                    time.sleep(0.5)
            except KeyboardInterrupt:
                # Handle Ctrl+C gracefully
                print("\nOperation interrupted by user. Type 'exit' to quit or continue with a new request.")
                continue
            except Exception as e:
                # Last resort exception handler to keep the CLI running
                logger.error(f"Unexpected error in main loop: {e}")
                print(f"\nAn unexpected error occurred. The system will continue operating.")
                # Short pause to avoid CPU spinning on repeated errors
                time.sleep(1)
    finally:
        # Stop the background thread when exiting
        stop_event.set()
        if tool_checker_thread.is_alive():
            tool_checker_thread.join(timeout=2.0)  # Wait for thread to exit
            

if __name__ == "__main__":
    main() 
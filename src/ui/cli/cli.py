from src.agents.ai_agent import LLMQueryAgent
from src.graphs.orchestrator_graph import create_initial_state, StateManager
from src.graphs.orchestrator_graph import TaskStatus, MessageRole
from src.agents.orchestrator_tools import TOOL_DEFINITIONS
from datetime import datetime
import logging
import time
import sys
import os

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

def check_completed_tools(agent):
    """
    Check if any background tool operations have completed.
    
    Args:
        agent: The LLMQueryAgent instance to check for completed tool requests
        
    Returns:
        bool: True if a completed tool was found and processed, False otherwise
    """
    try:
        completed_tool = agent.check_pending_tools()
        if not completed_tool:
            return False
            
        request_id = completed_tool.get('request_id', 'unknown')
        user_input = completed_tool.get('user_input', '')
        response = completed_tool.get('response', {})
        
        if not response:
            logger.warning(f"Empty response for tool request {request_id}")
            print(f"\n--- Tool Response (request {request_id}) ---")
            print("Error: Tool completed but returned no data.")
            return False
            
        print(f"\n--- Tool Response (request {request_id}) ---")
        print(f"Response: {response.get('message', 'No message available')}")
        
        # Check storage verification status if available
        storage_status = response.get('storage_status')
        if storage_status == 'not_verified':
            print(f"Warning: Data may not have been stored properly in the database.")
        
        try:
            # Process the completed tool response
            result = agent.handle_tool_completion(request_id, user_input)
            print(f"\nAgent: {result['response']}")
            return True
        except Exception as e:
            # Recover from error in handling tool completion
            logger.error(f"Error processing tool completion: {e}")
            print(f"\nThere was an error processing the tool result: {str(e)}")
            print("You can continue using the system normally.")
            return True
            
    except Exception as e:
        # Recover from any error in checking tool completion
        logger.error(f"Error checking for completed tools: {e}")
        # Don't show this error to the user unless in debug mode to avoid confusion
        # But continue operating normally
        return False

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
    
    # Main chat loop
    while True:
        try:
            # Check for completed tool requests before each user input
            # This gives tools a chance to complete and report back without blocking the UI
            try:
                found_completed_tool = check_completed_tools(agent)
            except Exception as e:
                logger.error(f"Error checking for completed tools: {e}")
                found_completed_tool = False
                
            # Get user input
            user_input = input("\nYou: ").strip()
            
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
            
            # Process user input and get agent response
            try:
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
                    for req in result["tool_requests"]:
                        request_id = req["request_id"]
                        agent.pending_requests[request_id] = user_input
                        
                        # Notify user that a tool is processing in the background
                        print(f"- Tool request sent: {req['tool']} (request {request_id})")
            except Exception as chat_error:
                # Recover gracefully from chat errors
                logger.error(f"Error processing chat: {chat_error}")
                print(f"\nI apologize, but I encountered an error while processing your request: {str(chat_error)}")
                print("You can continue with a different request.")
            
            # Brief pause to give immediate tool completions a chance to process
            # This improves responsiveness for very quick tool completions
            time.sleep(0.2)
            
            try:
                check_completed_tools(agent)
            except Exception as tool_check_error:
                # Don't let tool check errors crash the program
                logger.error(f"Error during final tool check: {tool_check_error}")
                
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


if __name__ == "__main__":
    main() 
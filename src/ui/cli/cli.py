from src.agents.ai_agent import LLMQueryAgent
from src.graphs.orchestrator_graph import create_initial_state, StateManager
from src.graphs.orchestrator_graph import TaskStatus, MessageRole
from datetime import datetime


def main():
    """Main function to run the orchestrator graph with chat functionality."""
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
    
    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("Goodbye!")
            break
        
        # Use the full chat flow
        result = agent.chat(user_input)
        
        # Update the state with the user input and agent response
        state_manager.update_conversation(MessageRole.USER, user_input)
        state_manager.update_conversation(MessageRole.ASSISTANT, result['response'])
        
        # Print the main response
        print(f"\nAgent: {result['response']}")
        
        # Print any tool results
        if result.get("tool_results"):
            print("\nTool Results:")
            for tool_result in result["tool_results"]:
                print(f"- {tool_result['tool']}: {tool_result['message']}")


if __name__ == "__main__":
    main() 
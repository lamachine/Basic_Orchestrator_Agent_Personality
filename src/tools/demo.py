"""Demo script for using the tools."""

import json
from .initialize_tools import initialize_tools, get_tool_prompt_section


def demo_tools():
    """Demonstrate the use of all available tools."""
    # Initialize the tool registry
    registry = initialize_tools()
    
    print("=== AVAILABLE TOOLS ===")
    for tool in registry.list_tools():
        print(f"\n* {tool.name}: {tool.description}")
    
    print("\n\n=== TOOL PROMPT SECTION ===")
    print(get_tool_prompt_section())
    
    print("\n\n=== TOOL EXECUTION DEMO ===")
    
    # Demo valet tool
    print("\n>> Executing valet tool...")
    result = registry.execute_tool("valet", task="Check my schedule")
    print(f"Response: {result['message']}")
    print(f"Details: {json.dumps(result['data'], indent=2)}")
    
    # Demo personal assistant tool
    print("\n>> Executing personal_assistant tool...")
    result = registry.execute_tool("personal_assistant", task="Send email to mom")
    print(f"Response: {result['message']}")
    print(f"Details: {json.dumps(result['data'], indent=2)}")
    
    # Demo librarian tool
    print("\n>> Executing librarian tool...")
    result = registry.execute_tool("librarian", task="Research Pydantic agents")
    print(f"Response: {result['message']}")
    print(f"Details: {json.dumps(result['data'], indent=2)}")


if __name__ == "__main__":
    demo_tools() 
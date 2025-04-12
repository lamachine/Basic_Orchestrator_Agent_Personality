"""Example of integrating tools with an LLM."""

import os
import sys
import json
import requests
from typing import Dict, Any, List, Optional

from .initialize_tools import get_tool_prompt_section
from .llm_integration import ToolParser


def query_llm(prompt: str, model: str = "llama2", temperature: float = 0.7) -> str:
    """
    Query the LLM using Ollama API.
    
    This is a simplified example. In a real implementation, 
    you'd likely have more sophisticated error handling and retry logic.
    
    Args:
        prompt: The prompt to send to the LLM
        model: The name of the model to use
        temperature: Temperature parameter for generation
        
    Returns:
        The LLM's response text
    """
    # This would use the actual Ollama API in a real implementation
    # For this example, we'll show a mock implementation
    print(f"Sending prompt to LLM (model: {model}):")
    print("-" * 50)
    print(prompt)
    print("-" * 50)
    
    # In a real implementation, this would be:
    # response = requests.post(
    #     "http://localhost:11434/api/generate",
    #     json={
    #         "model": model,
    #         "prompt": prompt,
    #         "temperature": temperature
    #     }
    # )
    # return response.json()["response"]
    
    # Mock response: simulate the LLM choosing a tool to use
    mock_responses = [
        "I'll use the valet tool to check on your daily schedule and any important messages.\n\nvalet(task='Check schedule and messages')",
        "I'll use the personal_assistant tool to check your to-do list.\n\npersonal_assistant(task='Review new tasks')",
        "I'll use the librarian tool to check on your research about Pydantic agents.\n\nlibrarian(task='Get Pydantic research status')"
    ]
    
    # Pick a response based on keywords in the prompt
    if "schedule" in prompt.lower() or "appointment" in prompt.lower():
        return mock_responses[0]
    elif "email" in prompt.lower() or "task" in prompt.lower():
        return mock_responses[1]
    else:
        return mock_responses[2]


def agent_conversation(user_input: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Conduct a single turn of conversation with the agent.
    
    Args:
        user_input: The user's input text
        conversation_history: Optional conversation history
        
    Returns:
        Dict containing the updated conversation state
    """
    # Initialize or use existing conversation history
    history = conversation_history or []
    
    # Add user message to history
    history.append({"role": "user", "content": user_input})
    
    # Create tool parser
    tool_parser = ToolParser()
    
    # Build the prompt with tool descriptions and conversation history
    system_prompt = f"""You are Ronan, an AI assistant with access to specialized tools.
Please help the user by using the appropriate tools when needed.

{get_tool_prompt_section()}

When using a tool, format your response as follows:
1. Say "I'll use the [tool name] tool to [purpose]"
2. On a new line, call the tool with: tool_name(task="your task description")
3. Wait for the tool results before continuing.
"""
    
    # Format conversation history for the prompt
    conversation_text = ""
    for msg in history:
        role = msg["role"].upper()
        conversation_text += f"\n{role}: {msg['content']}\n"
    
    # Add tool results from previous turns if they exist
    tool_results = ""
    if len(history) >= 3 and "tool_results" in history[-2]:
        tool_results = history[-2]["tool_results"]
    
    # Build the full prompt
    full_prompt = f"{system_prompt}\n\nCONVERSATION HISTORY:{conversation_text}\n{tool_results}\nASSISTANT:"
    
    # Query the LLM
    llm_response = query_llm(full_prompt)
    
    # Process the response
    processing_result = tool_parser.process_llm_response(llm_response)
    
    # Format tool results for the next turn
    tool_results_text = tool_parser.format_results_for_llm(processing_result["execution_results"])
    
    # Add assistant response to history
    history.append({
        "role": "assistant", 
        "content": processing_result["original_response"],
        "tool_calls": processing_result["tool_calls"],
        "tool_results": tool_results_text
    })
    
    return {
        "conversation_history": history,
        "response": processing_result["original_response"],
        "tool_results": processing_result["execution_results"]
    }


def run_demo_conversation():
    """Run a demonstration of tool-enabled conversation with the agent."""
    print("=== AGENT CONVERSATION DEMO ===")
    print("You can chat with the agent. It has access to valet, personal_assistant, and librarian tools.")
    print("Type 'exit' to end the demo.\n")
    
    conversation_history = []
    
    while True:
        user_input = input("\nYOU: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        
        result = agent_conversation(user_input, conversation_history)
        conversation_history = result["conversation_history"]
        
        print("\nASSISTANT:", result["response"])
        
        # Print any tool results
        if result["tool_results"]:
            print("\nTOOL RESULTS:")
            for tool_result in result["tool_results"]:
                tool_name = tool_result["name"]
                result_msg = tool_result["result"]["message"]
                print(f"- {tool_name}: {result_msg}")


if __name__ == "__main__":
    run_demo_conversation() 
"""Utility functions for working with tools across graphs and agents."""

from typing import Dict, Any, List, Optional, Callable, TypeVar, Union
from datetime import datetime
import logging
import json

from src.graphs.orchestrator_graph import (
    StateManager,
    GraphState,
    MessageRole,
    TaskStatus,
    Message
)

# Setup logging
logger = logging.getLogger(__name__)

T = TypeVar('T')

def execute_tool_with_state(
    state_manager: StateManager,
    tool_name: str,
    tool_func: Callable[[str], Dict[str, Any]],
    task: str
) -> Dict[str, Any]:
    """
    Execute a tool while updating the graph state.
    
    Args:
        state_manager: The state manager instance
        tool_name: Name of the tool being executed
        tool_func: The tool function to call
        task: The task description for the tool
        
    Returns:
        The tool execution results
    """
    try:
        # Set task in state
        task_id = f"{tool_name}_{datetime.now().isoformat()}"
        state_manager.set_task(task_id)
        
        # Update agent state
        state_manager.update_agent_state(tool_name, {
            "status": TaskStatus.IN_PROGRESS,
            "task": task,
            "start_time": datetime.now().isoformat()
        })
        
        # Record tool call in conversation
        state_manager.update_conversation(
            role=MessageRole.TOOL,
            content=f"Calling {tool_name} with task: {task}",
            metadata={
                "tool": tool_name,
                "task": task,
                "type": "tool_call"
            }
        )
        
        # Execute the tool
        result = tool_func(task)
        
        # Record result in state
        state_manager.update_conversation(
            role=MessageRole.TOOL,
            content=result["message"],
            metadata={
                "tool": tool_name,
                "type": "tool_result",
                "result_data": result["data"]
            }
        )
        
        # Update agent state with completion
        state_manager.update_agent_state(tool_name, {
            "status": TaskStatus.COMPLETED,
            "end_time": datetime.now().isoformat(),
            "result_summary": result["message"]
        })
        
        # Complete the task
        state_manager.complete_task(json.dumps(result))
        
        return result
    except Exception as e:
        # Handle errors
        error_msg = f"Error executing {tool_name}: {str(e)}"
        logger.error(error_msg)
        
        # Update state with error
        try:
            state_manager.update_agent_state(tool_name, {
                "status": TaskStatus.FAILED,
                "error": str(e),
                "end_time": datetime.now().isoformat()
            })
            state_manager.fail_task(error_msg)
        except Exception as state_e:
            logger.error(f"Failed to update state with error: {str(state_e)}")
        
        return {
            "status": "error",
            "message": error_msg,
            "data": {"error": str(e)}
        }


def format_conversation_history(state_manager: StateManager, max_messages: int = 10) -> str:
    """
    Format the recent conversation history for inclusion in prompts.
    
    Args:
        state_manager: The state manager instance
        max_messages: Maximum number of messages to include
        
    Returns:
        Formatted conversation history string
    """
    context = state_manager.get_conversation_context(max_messages)
    
    if not context:
        return ""
    
    history = []
    for msg in context:
        role_prefix = {
            MessageRole.USER: "User",
            MessageRole.ASSISTANT: "Assistant",
            MessageRole.SYSTEM: "System",
            MessageRole.TOOL: "Tool"
        }.get(msg.role, msg.role)
        
        # For tool messages, include the tool name if available
        tool_prefix = ""
        if msg.role == MessageRole.TOOL and msg.metadata and "tool" in msg.metadata:
            tool_prefix = f" [{msg.metadata['tool']}]"
        
        history.append(f"{role_prefix}{tool_prefix}: {msg.content}")
    
    return "\n".join(history)


def create_tool_node_func(
    tool_name: str, 
    tool_func: Callable[[str], Dict[str, Any]]
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """
    Create a graph node function for a tool.
    
    Args:
        tool_name: Name of the tool
        tool_func: The tool function to call
        
    Returns:
        A function suitable for use as a graph node
    """
    async def tool_node(state: GraphState, writer) -> GraphState:
        """Tool node function for use in the graph."""
        state_manager = StateManager(state)
        
        try:
            # Extract task from state
            task = state.get("current_task", "")
            if not task:
                # If no specific task, check the last user message
                last_msg = state_manager.get_conversation_context(1)
                if last_msg and last_msg[0].role == MessageRole.USER:
                    task = last_msg[0].content
            
            writer(f"\n#### Executing {tool_name} with task: {task}\n")
            
            # Execute tool with state updates
            result = execute_tool_with_state(
                state_manager=state_manager,
                tool_name=tool_name,
                tool_func=tool_func,
                task=task
            )
            
            writer(f"\n#### {tool_name} result: {result['message']}\n")
            
            # Return updated state
            return state_manager.get_current_state()
        except Exception as e:
            writer(f"\n#### Error in {tool_name}: {str(e)}\n")
            try:
                state_manager.fail_task(f"Error in {tool_name}: {str(e)}")
            except Exception:
                pass  # Already logged in execute_tool_with_state
            return state_manager.get_current_state()
    
    return tool_node


def extract_tool_call_from_message(message: Message) -> Optional[Dict[str, Any]]:
    """
    Extract tool call information from a message.
    
    Args:
        message: The message to analyze
        
    Returns:
        Tool call information if found, None otherwise
    """
    import re
    
    # Simple pattern to match tool calls in format: tool_name(task="description")
    pattern = r'(\w+)\s*\(\s*task\s*=\s*[\'"]([^\'"]+)[\'"]\s*\)'
    
    if not message or not message.content:
        return None
    
    match = re.search(pattern, message.content)
    if match:
        return {
            "tool": match.group(1),
            "task": match.group(2)
        }
    
    return None


def should_use_tool(message: Message, available_tools: List[str]) -> Optional[Dict[str, str]]:
    """
    Determine if a message should use a tool, and which one.
    
    Args:
        message: The message to analyze
        available_tools: List of available tool names
        
    Returns:
        Dict with tool name and task if a tool should be used, None otherwise
    """
    # First try to extract explicit tool call
    tool_call = extract_tool_call_from_message(message)
    if tool_call and tool_call["tool"] in available_tools:
        return tool_call
    
    # No explicit tool call found
    return None 
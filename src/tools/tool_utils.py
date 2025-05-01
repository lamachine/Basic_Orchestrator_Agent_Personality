"""Utility functions for working with tools across graphs and agents."""

from typing import Dict, Any, List, Optional, Callable, TypeVar, Union
from datetime import datetime
import logging
import json

from src.state.state_manager import StateManager
from src.state.state_models import GraphState, MessageRole, TaskStatus, Message

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
        
        # Record tool call in session
        state_manager.update_session(
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
        state_manager.update_session(
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


def format_session_history(state_manager: StateManager, max_messages: int = 10) -> str:
    """
    Format the recent session message history for inclusion in prompts.
    
    Args:
        state_manager: The state manager instance
        max_messages: Maximum number of messages to include
        
    Returns:
        Formatted session message history string
    """
    context = state_manager.get_session_context(max_messages)
    
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
                last_msg = state_manager.get_session_context(1)
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


def should_use_tool(message: str, available_tools: list[str]) -> bool:
    """
    Determine if a message should use a tool based on available tools.

    Args:
        message (str): The message to check.
        available_tools (list[str]): List of available tool names.

    Returns:
        bool: True if a tool should be used, False otherwise.
    """
    from src.tools.llm_integration import ToolParser
    tool_calls = ToolParser.extract_tool_calls(message)
    if not tool_calls:
        return False
    return any(tc['tool_name'] in available_tools for tc in tool_calls) 
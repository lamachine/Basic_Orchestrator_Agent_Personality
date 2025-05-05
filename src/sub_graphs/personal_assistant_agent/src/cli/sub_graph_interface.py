"""
CLI Message Passing Interface for Personal Assistant Sub-Graph

This interface enables message passing for CLI or direct tool invocation.
"""
from src.sub_graphs.personal_assistant_agent.src.agents.personal_assistant_agent import handle_personal_assistant_task

def handle_cli_tool_request(task: str, parameters: dict, request_id: str) -> dict:
    """
    Receives tool requests from the CLI/tool interface, calls the agent, and returns the response.
    """
    return handle_personal_assistant_task(task, parameters, request_id) 
"""Valet agent handler module."""

import logging
from src.tools.valet import valet_tool
from src.tools.tool_registry import ToolRegistry, ToolDescription

logger = logging.getLogger("orchestrator.valet")

class ValetAgent:
    """Handles valet agent requests and tool registry."""
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.tool_registry.register_tool(
            ToolDescription(
                name="valet",
                description="Manages household staff, daily schedule, and personal affairs.",
                parameters={"task": "Optional[str] - The task or query for the valet"},
                function=valet_tool,
                example="valet(task='Check my schedule for today')"
            )
        )
        self.prompt_section = (
            "You are the Valet agent. You manage schedules, staff, and personal affairs. "
            "Use the valet tool for all related tasks."
        )

    def handle_request(self, user_input: str) -> str:
        """Process a user request and route to the valet tool if appropriate."""
        logger.info(f"Handling valet request: {user_input}")
        # For now, just call the valet tool directly
        return str(valet_tool(task=user_input)) 
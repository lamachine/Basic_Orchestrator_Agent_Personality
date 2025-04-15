"""Personal Assistant agent handler module."""

import logging
from src.tools.personal_assistant import personal_assistant_tool
from src.tools.tool_registry import ToolRegistry, ToolDescription

logger = logging.getLogger("orchestrator.personal_assistant")

class PersonalAssistantAgent:
    """Handles personal assistant agent requests and tool registry."""
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.tool_registry.register_tool(
            ToolDescription(
                name="personal_assistant",
                description="Handles communications, task lists, and personal productivity.",
                parameters={"task": "Optional[str] - The task or query for the personal assistant"},
                function=personal_assistant_tool,
                example="personal_assistant(task='Send email to mom about Sunday plans')"
            )
        )
        self.prompt_section = (
            "You are the Personal Assistant agent. You handle communications, task lists, and productivity. "
            "Use the personal_assistant tool for all related tasks."
        )

    def handle_request(self, user_input: str) -> str:
        """Process a user request and route to the personal assistant tool if appropriate."""
        logger.info(f"Handling personal assistant request: {user_input}")
        return str(personal_assistant_tool(task=user_input)) 
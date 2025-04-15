"""Librarian agent handler module."""

import logging
from src.tools.librarian import librarian_tool
from src.tools.tool_registry import ToolRegistry, ToolDescription

logger = logging.getLogger("orchestrator.librarian")

class LibrarianAgent:
    """Handles librarian agent requests and tool registry."""
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.tool_registry.register_tool(
            ToolDescription(
                name="librarian",
                description="Performs research, documentation crawling, and knowledge management.",
                parameters={"task": "Optional[str] - The research task or query for the librarian"},
                function=librarian_tool,
                example="librarian(task='Research Pydantic agents and save the results')"
            )
        )
        self.prompt_section = (
            "You are the Librarian agent. You perform research, documentation crawling, and knowledge management. "
            "Use the librarian tool for all related tasks."
        )

    def handle_request(self, user_input: str) -> str:
        """Process a user request and route to the librarian tool if appropriate."""
        logger.info(f"Handling librarian request: {user_input}")
        return str(librarian_tool(task=user_input)) 
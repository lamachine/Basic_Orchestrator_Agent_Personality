"""Librarian agent handler module."""

import logging
# Remove the top-level import to avoid circular dependency
# from src.tools.librarian import librarian_tool
from src.tools.tool_registry import ToolRegistry, ToolDescription
from src.agents.base_agent import BaseAgent
from src.config import Configuration

config = Configuration()

class LibrarianAgent(BaseAgent):
    """Handles librarian agent requests and tool registry."""
    def __init__(self):
        super().__init__(
            name="librarian",
            prompt_section="You are the Librarian agent. You perform research, documentation crawling, and knowledge management. Use the librarian tool for all related tasks.",
            api_url=config.ollama_api_url + '/api/generate',
            model=config.ollama_model
        )
        
        # Import the librarian_tool here to avoid circular dependencies
        from src.tools.librarian import librarian_tool
        
        self.tool_registry.register_tool(
            ToolDescription(
                name="librarian",
                description="Performs research, documentation crawling, and knowledge management.",
                parameters={"task": "Optional[str] - The research task or query for the librarian"},
                function=librarian_tool,
                example="librarian(task='Research Pydantic agents and save the results')"
            )
        )

    def handle_request(self, user_input: str) -> dict:
        self.log_message(f"Handling librarian request: {user_input}")
        return self.call_tool("librarian", task=user_input) 
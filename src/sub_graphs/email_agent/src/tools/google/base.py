"""Base class for Google tools."""

from typing import Dict, Any
import logging

# from src.sub_graph_personal_assistant.tools.base import PersonalAssistantTool  # (disabled for minimal orchestrator)
# from src.sub_graph_personal_assistant.tools.google.credentials import CredentialsHandler  # (disabled for minimal orchestrator)

logger = logging.getLogger(__name__)

# class GoogleToolBase(PersonalAssistantTool):
#     """Base class for Google tools with common functionality."""
#     
#     def __init__(self, config: Dict[str, Any], tool_name: str):
#         """Initialize Google tool base.
#         
#         Args:
#             config: Tool configuration
#             tool_name: Name of the specific tool (e.g. 'gmail', 'calendar')
#         """
#         super().__init__(
#             name=tool_name,
#             description=f"Google {tool_name.title()} API tool",
#             config=config
#         )
#         self.tool = None
#         self.source = f"personal_assistant_graph.google.{tool_name}"
#         self._creds_handler = None
#         
#     async def initialize(self) -> bool:
#         """Initialize Google API connection.
#         
#         Returns:
#             bool: True if initialization successful
#         """
#         try:
#             # Initialize credentials handler if not already done
#             if not self._creds_handler:
#                 self._creds_handler = CredentialsHandler()
#             return True
#         except Exception as e:
#             logger.error(f"Failed to initialize Google tool: {e}")
#             return False
#             
#     async def cleanup(self) -> None:
#         """Clean up resources."""
#         if self.tool and hasattr(self.tool, 'cleanup'):
#             await self.tool.cleanup()

# ... existing code ... 
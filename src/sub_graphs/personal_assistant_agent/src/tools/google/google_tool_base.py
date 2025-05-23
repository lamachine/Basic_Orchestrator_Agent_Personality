"""Base class for Google tools."""

import logging
import os
from abc import ABC
from typing import Any, Dict

# from src.sub_graph_personal_assistant.tools.personal_assistant_base_tool import PersonalAssistantTool  # (disabled for minimal orchestrator)
# from src.sub_graph_personal_assistant.tools.google.credentials import CredentialsHandler  # (disabled for minimal orchestrator)

logger = logging.getLogger(__name__)

# class GoogleToolBase(PersonalAssistantTool, ABC):
#     """Base class for Google tools with common functionality.
#     This class may remain abstract if not all abstract methods are implemented.
#     """
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
#                 # Get credentials path from environment or config
#                 credentials_path = os.getenv('GOOGLE_CLIENT_SECRET_FILE') or self.config.get('credentials_path')
#                 if not credentials_path:
#                     logger.error("No credentials path provided in environment or config")
#                     return False
#
#                 # Get token path from environment or config, or use default next to credentials
#                 token_path = os.getenv('GOOGLE_TOKEN_FILE') or self.config.get('token_path')
#                 if not token_path:
#                     # Use same directory as credentials file for token
#                     token_dir = os.path.dirname(credentials_path)
#                     token_path = os.path.join(token_dir, 'token.pickle')
#
#                 logger.debug(f"Initializing credentials handler with paths: {credentials_path}, {token_path}")
#                 self._creds_handler = CredentialsHandler(
#                     credentials_path=credentials_path,
#                     token_path=token_path
#                 )
#             return True
#         except Exception as e:
#             logger.error(f"Failed to initialize Google tool: {e}")
#             return False
#
#     async def cleanup(self) -> None:
#         """Clean up resources."""
#         if self.tool and hasattr(self.tool, 'cleanup'):
#             await self.tool.cleanup()

"""CLI session handling functionality."""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import traceback

from src.sub_graphs.template_agent.src.common.services.logging_service import get_logger

logger = get_logger(__name__)

class CLISessionHandler:
    """Handles session display and user interaction for CLI."""
    
    def __init__(self, display_handler, session_manager):
        """Initialize the session handler."""
        self.display_handler = display_handler
        self.session_manager = session_manager
        logger.debug("CLISessionHandler initialized with session manager")
    
    async def initialize_session(self) -> None:
        """Initialize a new session."""
        try:
            logger.debug("Initializing new session")
            await self.session_manager.create_session()
            logger.debug("Session created successfully")
        except Exception as e:
            logger.error("Error starting new session: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            raise

    async def search_sessions(self) -> None:
        """Search for existing sessions."""
        try:
            logger.debug("Starting session search")
            self.display_handler.display_message({
                "role": "system",
                "content": "Enter search query: "
            })
            query = await asyncio.to_thread(self.display_handler.get_user_input)
            logger.debug("Search query: %s", query["params"]["message"])
            
            results = await self.session_manager.search_sessions(query["params"]["message"])
            logger.debug("Found %d matching sessions", len(results) if results else 0)
            
            if not results:
                self.display_handler.display_message({
                    "role": "system",
                    "content": "No sessions found matching your query."
                })
                return
                
            self.display_handler.display_message({
                "role": "system",
                "content": "\nSearch results:"
            })
            
            for i, (session_id, info) in enumerate(results.items(), 1):
                name = info.get('name', f"Session {session_id}")
                updated = info.get('updated_at', 'Unknown')
                if isinstance(updated, datetime):
                    updated = updated.strftime("%Y-%m-%d %H:%M:%S")
                logger.debug("Displaying search result %d: %s (Last active: %s)", i, name, updated)
                self.display_handler.display_message({
                    "role": "system",
                    "content": f"{i}. {name} (Last active: {updated})"
                })
                
            self.display_handler.display_message({
                "role": "system",
                "content": "\nEnter session number to load (or press Enter to cancel): "
            })
            
            choice = await asyncio.to_thread(self.display_handler.get_user_input)
            logger.debug("User choice: %s", choice["params"]["message"])
            
            if not choice["params"]["message"].strip():
                logger.debug("User cancelled session selection")
                return
            
            try:
                idx = int(choice["params"]["message"]) - 1
                session_id = list(results.keys())[idx]
                logger.debug("Selected session ID: %s", session_id)
                await self.continue_session(session_id)
            except (ValueError, IndexError):
                logger.warning("Invalid session choice: %s", choice["params"]["message"])
                self.display_handler.display_message({
                    "role": "system",
                    "content": "Invalid choice."
                })
            
        except Exception as e:
            logger.error("Error in session search: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            self.display_handler.display_message({
                "role": "system",
                "content": "Error searching sessions."
            })

    async def continue_session(self, session_id: str) -> None:
        """Continue a session using SessionManager."""
        try:
            logger.debug("Continuing session: %s", session_id)
            await self.session_manager.restore_session(session_id)
            self.session_name = self.session_manager.session_name
            self.current_session_id = self.session_manager.current_session_id
            logger.debug("Session restored successfully: %s", self.session_name)
            self.display_handler.display_message({
                "role": "system",
                "content": f"Resumed session: {self.session_name}"
            })
        except Exception as e:
            logger.error("Error continuing session: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            self.display_handler.display_message({
                "role": "system",
                "content": "Error resuming session."
            }) 
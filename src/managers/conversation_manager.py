"""
Conversation Manager Module

This module implements the conversation manager for handling conversations,
including creating, retrieving, updating, and deleting conversations.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from src.managers.db_manager import DatabaseManager
from src.services.logging_service import get_logger

# Initialize logger
logger = get_logger(__name__)


class ConversationManager:
    """
    Manager for handling conversations.

    Provides functionality for creating, retrieving, updating, and
    deleting conversations.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize the conversation manager.

        Args:
            db_manager: Optional DatabaseManager instance
        """
        self.db_manager = db_manager
        """
        Search for conversations by title or content.

        Args:
            query: Search query

        Returns:
            List of matching conversations
        """
        try:
            if not self.db_manager:
                logger.error("No database manager provided for conversation search")
                return []

            # Search conversations using database manager
            return self.db_manager.conversation_manager.search_conversations(query)

        except Exception as e:
            logger.error(f"Error searching conversations: {e}")
            return []

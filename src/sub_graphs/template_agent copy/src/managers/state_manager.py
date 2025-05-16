"""
Template Agent State Manager.

This manager handles state management for the template agent,
inheriting core functionality from the orchestrator's state manager
but adding template-specific state handling and persistence.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from src.managers.state_manager import StateManager as BaseStateManager
from src.state.state_models import MessageRole
from ..services.logging_service import get_logger

logger = get_logger(__name__)

class StateManager(BaseStateManager):
    """
    Template agent state manager.
    
    This manager extends the base state manager with template-specific
    state handling and persistence.
    """
    
    def __init__(self):
        """Initialize the template state manager."""
        super().__init__()
        self.source_prefix = "template"
        self._state_updates: List[Dict[str, Any]] = []
        logger.debug("Initialized template state manager")
    
    async def update_state(
        self,
        session_id: str,
        updates: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update state with template-specific handling.
        
        Args:
            session_id: The session ID
            updates: The state updates to apply
            metadata: Optional metadata
            
        Returns:
            Dict containing the updated state
        """
        # Add template-specific metadata
        if metadata is None:
            metadata = {}
        
        # Track state update
        self._state_updates.append({
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "updates": updates,
            "metadata": metadata
        })
        
        # Update state using base manager
        result = await super().update_state(
            session_id,
            updates,
            {
                **metadata,
                "source": f"{self.source_prefix}.state_manager"
            }
        )
        
        logger.debug(
            f"Updated state for session {session_id}: "
            f"{list(updates.keys())}"
        )
        return result
    
    async def get_state(
        self,
        session_id: str,
        keys: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """
        Get state with template-specific handling.
        
        Args:
            session_id: The session ID
            keys: Optional list of state keys to retrieve
            
        Returns:
            Dict containing the requested state
        """
        # Get state using base manager
        state = await super().get_state(
            session_id,
            keys
        )
        
        logger.debug(
            f"Retrieved state for session {session_id}: "
            f"{list(state.keys())}"
        )
        return state
    
    def get_state_updates(
        self,
        session_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get template-specific state update history.
        
        Args:
            session_id: Optional session ID to filter by
            limit: Optional limit on number of updates to return
            
        Returns:
            List of state updates
        """
        updates = self._state_updates
        
        # Filter by session ID if specified
        if session_id:
            updates = [
                u for u in updates
                if u["session_id"] == session_id
            ]
        
        # Apply limit if specified
        if limit:
            updates = updates[-limit:]
        
        return updates
    
    def clear_state_updates(
        self,
        session_id: Optional[str] = None
    ) -> None:
        """
        Clear template-specific state update history.
        
        Args:
            session_id: Optional session ID to clear updates for
        """
        if session_id:
            self._state_updates = [
                u for u in self._state_updates
                if u["session_id"] != session_id
            ]
        else:
            self._state_updates = []
        
        logger.debug(
            f"Cleared state updates for "
            f"{session_id if session_id else 'all sessions'}"
        ) 
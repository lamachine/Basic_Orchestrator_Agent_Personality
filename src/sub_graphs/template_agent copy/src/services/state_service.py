"""
Template Agent State Service.

This service provides state management for the template agent,
inheriting core functionality from the orchestrator's state service
but maintaining template-specific state in memory.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from src.services.session_service import SessionService as BaseSessionService
from src.state.state_models import MessageRole
from .logging_service import get_logger

logger = get_logger(__name__)

class StateService(BaseSessionService):
    """
    Template agent state service.
    
    This service extends the base session service with template-specific
    state management and logging.
    """
    
    def __init__(self):
        """Initialize the template state service."""
        super().__init__()
        self.source_prefix = "template"
        self._template_state: Dict[str, Any] = {}
        logger.debug("Initialized template state service")
    
    async def update_state(
        self,
        session_id: str,
        updates: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update template-specific state.
        
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
        
        # Update template state
        self._template_state.update(updates)
        
        # Log state update
        logger.debug(
            f"Updated template state for session {session_id}: "
            f"{list(updates.keys())}"
        )
        
        # Update parent state with template context
        return await super().update_state(
            session_id,
            {
                **updates,
                "template_state": self._template_state
            },
            {
                **metadata,
                "source": f"{self.source_prefix}.state_service"
            }
        )
    
    async def get_state(
        self,
        session_id: str,
        keys: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """
        Get template-specific state.
        
        Args:
            session_id: The session ID
            keys: Optional list of state keys to retrieve
            
        Returns:
            Dict containing the requested state
        """
        # Get parent state
        parent_state = await super().get_state(session_id, keys)
        
        # Extract template state
        template_state = parent_state.get("template_state", {})
        
        # Filter by keys if specified
        if keys:
            template_state = {
                k: v for k, v in template_state.items()
                if k in keys
            }
        
        logger.debug(
            f"Retrieved template state for session {session_id}: "
            f"{list(template_state.keys())}"
        )
        
        return template_state
    
    async def clear_state(
        self,
        session_id: str,
        keys: Optional[list[str]] = None
    ) -> None:
        """
        Clear template-specific state.
        
        Args:
            session_id: The session ID
            keys: Optional list of state keys to clear
        """
        if keys:
            # Clear specific keys
            for key in keys:
                self._template_state.pop(key, None)
        else:
            # Clear all template state
            self._template_state.clear()
        
        # Update parent state
        await super().update_state(
            session_id,
            {"template_state": self._template_state},
            {"source": f"{self.source_prefix}.state_service"}
        )
        
        logger.debug(
            f"Cleared template state for session {session_id}: "
            f"{keys if keys else 'all'}"
        ) 
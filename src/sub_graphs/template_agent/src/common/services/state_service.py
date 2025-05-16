"""
State Service Module

This module implements state management functionality as a service layer. It provides:
1. State initialization and management
2. State persistence and restoration
3. State validation and cleanup
4. State history tracking
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from .logging_service import get_logger
from .db_service import DBService
from ..models.state_models import GraphState, Message, MessageType, MessageStatus
from ..models.service_models import StateServiceConfig

logger = get_logger(__name__)

class StateService:
    """
    Service for managing graph state.
    
    This class provides methods for:
    1. Creating and initializing state
    2. Updating and persisting state
    3. Restoring state from storage
    4. Managing state history
    """
    
    def __init__(self, config: StateServiceConfig, db_service: Optional[DBService] = None):
        """
        Initialize the state service.
        
        Args:
            config: State service configuration
            db_service: Optional database service instance
        """
        self.config = config
        self.db_service = db_service
        self._current_state: Optional[GraphState] = None
        self._state_history: List[GraphState] = []
        
    def create_state(self, session_id: str, user_id: str = "developer") -> GraphState:
        """
        Create a new state instance.
        
        Args:
            session_id: Session ID
            user_id: User ID
            
        Returns:
            New GraphState instance
        """
        try:
            state = GraphState(
                session_id=session_id,
                user_id=user_id,
                messages=[],
                metadata={},
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self._current_state = state
            self._state_history.append(state)
            
            logger.debug(f"Created new state for session {session_id}")
            return state
            
        except Exception as e:
            logger.error(f"Error creating state: {e}")
            raise
            
    def get_current_state(self) -> Optional[GraphState]:
        """Get the current state."""
        return self._current_state
        
    def update_state(self, state: GraphState) -> None:
        """
        Update the current state.
        
        Args:
            state: New state to set as current
        """
        try:
            self._current_state = state
            self._state_history.append(state)
            
            # Trim history if needed
            max_history = self.config.get_merged_config().get("max_state_history", 100)
            if len(self._state_history) > max_history:
                self._state_history = self._state_history[-max_history:]
                
            logger.debug(f"Updated state for session {state.session_id}")
            
        except Exception as e:
            logger.error(f"Error updating state: {e}")
            raise
            
    async def persist_state(self, state: Optional[GraphState] = None) -> bool:
        """
        Persist state to storage.
        
        Args:
            state: Optional state to persist (uses current if not provided)
            
        Returns:
            bool: Success status
        """
        try:
            if not self.db_service:
                logger.warning("No DB service available for state persistence")
                return False
                
            target_state = state or self._current_state
            if not target_state:
                logger.warning("No state to persist")
                return False
                
            # Convert state to dict
            state_data = {
                "session_id": target_state.session_id,
                "user_id": target_state.user_id,
                "messages": [msg.dict() for msg in target_state.messages],
                "metadata": target_state.metadata,
                "created_at": target_state.created_at.isoformat(),
                "updated_at": target_state.updated_at.isoformat()
            }
            
            # Store in database
            await self.db_service.insert("graph_states", state_data)
            logger.debug(f"Persisted state for session {target_state.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error persisting state: {e}")
            return False
            
    async def restore_state(self, session_id: str) -> Optional[GraphState]:
        """
        Restore state from storage.
        
        Args:
            session_id: Session ID to restore
            
        Returns:
            Optional[GraphState]: Restored state if found
        """
        try:
            if not self.db_service:
                logger.warning("No DB service available for state restoration")
                return None
                
            # Get state from database
            result = await self.db_service.select(
                "graph_states",
                filters={"session_id": session_id},
                order_by="updated_at",
                order_desc=True,
                limit=1
            )
            
            if not result:
                logger.warning(f"No state found for session {session_id}")
                return None
                
            state_data = result[0]
            
            # Convert messages back to Message objects
            messages = []
            for msg_data in state_data.get("messages", []):
                messages.append(Message(
                    request_id=msg_data.get("request_id"),
                    parent_request_id=msg_data.get("parent_request_id"),
                    type=MessageType(msg_data.get("type", MessageType.REQUEST.value)),
                    status=MessageStatus(msg_data.get("status", MessageStatus.PENDING.value)),
                    timestamp=datetime.fromisoformat(msg_data.get("timestamp")),
                    content=msg_data.get("content", ""),
                    data=msg_data.get("data", {}),
                    metadata=msg_data.get("metadata", {})
                ))
                
            # Create state object
            state = GraphState(
                session_id=state_data["session_id"],
                user_id=state_data["user_id"],
                messages=messages,
                metadata=state_data.get("metadata", {}),
                created_at=datetime.fromisoformat(state_data["created_at"]),
                updated_at=datetime.fromisoformat(state_data["updated_at"])
            )
            
            self._current_state = state
            self._state_history.append(state)
            
            logger.debug(f"Restored state for session {session_id}")
            return state
            
        except Exception as e:
            logger.error(f"Error restoring state: {e}")
            return None
            
    def get_state_history(self) -> List[GraphState]:
        """Get the state history."""
        return self._state_history.copy()
        
    def clear_state_history(self) -> None:
        """Clear the state history."""
        self._state_history.clear()
        
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "has_current_state": self._current_state is not None,
            "history_size": len(self._state_history),
            "max_history": self.config.get_merged_config().get("max_state_history", 100)
        } 
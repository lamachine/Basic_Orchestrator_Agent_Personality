"""
State Manager Module - Central persistence and retrieval system for application state.

Provides a unified interface for storing, retrieving, and manipulating application state, including:
- Conversation persistence
- Message management
- Database abstraction
- State validation
- Transaction management
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
import logging

from .state_models import (
    Message, 
    MessageRole, 
    MessageState, 
    TaskStatus, 
    GraphState,
    MessageType,
    MessageStatus
)
from .state_errors import (
    StateError, 
    ValidationError, 
    StateUpdateError, 
    StateTransitionError,
    MessageError,
    TaskError,
    AgentStateError,
    PersistenceError
)
from .state_validator import StateValidator

class StateManager:
    """Manages application state, validation, and (optionally) persistence."""
    
    def __init__(self, db_manager: Optional[Any] = None) -> None:
        """Initialize the state manager.
        
        Args:
            db_manager: Optional database manager for persistence
        """
        self.sessions: Dict[str, MessageState] = {}
        self.db_manager = db_manager
        self.validator = StateValidator()
        self._last_update = datetime.now()
        self._update_count = 0
        self._error_count = 0
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)

    def _check_rate_limit(self) -> None:
        """Prevent too frequent updates."""
        current_time = datetime.now()
        if (current_time - self._last_update) < timedelta(milliseconds=100):
            self._update_count += 1
            if self._update_count > 100:
                raise StateUpdateError("Too many rapid state updates")
        else:
            self._update_count = 0
        self._last_update = current_time

    async def get_session(self, session_id: str) -> MessageState:
        """Get or create a message state for a session."""
        async with self._lock:
            session_id_int = int(session_id)
            if session_id_int not in self.sessions:
                self.sessions[session_id_int] = MessageState(
                    session_id=session_id_int,
                    db_manager=self.db_manager
                )
            return self.sessions[session_id_int]

    async def update_session(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        sender: Optional[str] = None,
        target: Optional[str] = None
    ) -> MessageState:
        """Update a session with a new message."""
        try:
            self._check_rate_limit()
            session = await self.get_session(session_id)
            last_message = session.get_last_message()
            
            if last_message:
                if role == last_message.role == MessageRole.USER:
                    raise StateUpdateError("Cannot have two consecutive user messages")
                if role == last_message.role == MessageRole.ASSISTANT:
                    raise StateUpdateError("Cannot have two consecutive assistant messages")
                    
            await session.add_message(role, content, metadata, sender, target)
            return session
            
        except Exception as e:
            self._error_count += 1
            raise StateUpdateError(f"Failed to update session: {str(e)}") from e

    async def get_all_sessions(self) -> List[MessageState]:
        """Get all active sessions."""
        return list(self.sessions.values())

    async def update_agent_state(
        self,
        session_id: str,
        agent_id: str,
        status: Dict[str, Any]
    ) -> None:
        """Update an agent's state within a session."""
        try:
            self._check_rate_limit()
            session = await self.get_session(session_id)
            
            if not self.validator.validate_agent_state(agent_id, status):
                raise ValidationError(f"Invalid agent state structure for {agent_id}")
                
            if 'agent_states' not in session.conversation_state:
                session.conversation_state['agent_states'] = {}
                
            session.conversation_state['agent_states'][agent_id] = status
            session.last_updated = datetime.now()
            
        except Exception as e:
            self._error_count += 1
            raise AgentStateError(f"Failed to update agent state: {str(e)}") from e

    async def start_task(
        self,
        session_id: str,
        task: str
    ) -> None:
        """Start a new task in the session."""
        try:
            self._check_rate_limit()
            session = await self.get_session(session_id)
            
            current_status = session.current_task_status
            if not self.validator.validate_task_transition(current_status, TaskStatus.IN_PROGRESS):
                raise StateTransitionError(
                    f"Invalid task transition from {current_status} to {TaskStatus.IN_PROGRESS}"
                )
                
            session.current_task = task
            session.current_task_status = TaskStatus.IN_PROGRESS
            session.last_updated = datetime.now()
            
        except Exception as e:
            self._error_count += 1
            raise TaskError(f"Failed to start task: {str(e)}") from e

    async def complete_task(
        self,
        session_id: str,
        result: Optional[Dict[str, Any]] = None
    ) -> None:
        """Complete the current task in the session."""
        try:
            self._check_rate_limit()
            session = await self.get_session(session_id)
            
            if not session.current_task:
                raise TaskError("No active task to complete")
                
            current_status = session.current_task_status
            if not self.validator.validate_task_transition(current_status, TaskStatus.COMPLETED):
                raise StateTransitionError(
                    f"Invalid task transition from {current_status} to {TaskStatus.COMPLETED}"
                )
                
            session.current_task_status = TaskStatus.COMPLETED
            if result:
                session.conversation_state['task_results'] = result
            session.last_updated = datetime.now()
            
        except Exception as e:
            self._error_count += 1
            raise TaskError(f"Failed to complete task: {str(e)}") from e

    async def fail_task(
        self,
        session_id: str,
        error: str
    ) -> None:
        """Mark the current task as failed in the session."""
        try:
            self._check_rate_limit()
            session = await self.get_session(session_id)
            
            if not session.current_task:
                raise TaskError("No active task to fail")
                
            current_status = session.current_task_status
            if not self.validator.validate_task_transition(current_status, TaskStatus.FAILED):
                raise StateTransitionError(
                    f"Invalid task transition from {current_status} to {TaskStatus.FAILED}"
                )
                
            session.current_task_status = TaskStatus.FAILED
            session.conversation_state['task_error'] = error
            session.last_updated = datetime.now()
            
        except Exception as e:
            self._error_count += 1
            raise TaskError(f"Failed to mark task as failed: {str(e)}") from e

    async def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics."""
        return {
            "error_count": self._error_count,
            "update_count": self._update_count
        }

    async def get_agent_state(
        self,
        session_id: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """Get an agent's state from a session."""
        session = await self.get_session(session_id)
        return session.conversation_state.get('agent_states', {}).get(agent_id, {})

    async def get_session_context(
        self,
        session_id: str,
        window_size: int = 5
    ) -> List[Message]:
        """Get the context window for a session."""
        session = await self.get_session(session_id)
        return session.get_context_window(window_size)

    async def get_task_history(
        self,
        session_id: str
    ) -> List[str]:
        """Get the task history for a session."""
        session = await self.get_session(session_id)
        return session.conversation_state.get('task_history', [])

    async def persist_state(self) -> None:
        """Persist all session states."""
        if not self.db_manager:
            return
            
        try:
            for session_id, session in self.sessions.items():
                if hasattr(self.db_manager, 'save_session'):
                    await self.db_manager.save_session(session_id, session)
        except Exception as e:
            raise PersistenceError(f"Failed to persist state: {str(e)}") from e

    async def load_state(self) -> None:
        """Load all session states."""
        if not self.db_manager:
            return
            
        try:
            if hasattr(self.db_manager, 'get_all_sessions'):
                sessions = await self.db_manager.get_all_sessions()
                for session in sessions:
                    self.sessions[session.session_id] = session
        except Exception as e:
            raise PersistenceError(f"Failed to load state: {str(e)}") from e 
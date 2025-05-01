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

from src.state.state_models import (
    Message, 
    MessageRole, 
    MessageState, 
    TaskStatus, 
    GraphState,
)
from src.state.state_errors import (
    StateError, 
    ValidationError, 
    StateUpdateError, 
    StateTransitionError
)
from src.state.state_validator import StateValidator

def update_agent_state(state: GraphState, agent_id: str, update: Dict[str, Any]) -> GraphState:
    """
    Update an agent's state with validation.

    Args:
        state (GraphState): The current graph state
        agent_id (str): The ID of the agent to update
        update (Dict[str, Any]): The state updates to apply

    Returns:
        GraphState: The updated graph state
    """
    if agent_id not in state['agent_states']:
        state['agent_states'][agent_id] = {}
    state['agent_states'][agent_id].update(update)
    return state

def add_task_to_history(state: GraphState, task: str) -> GraphState:
    """
    Add a task to the history with timestamp.

    Args:
        state (GraphState): The current graph state
        task (str): The task description

    Returns:
        GraphState: The updated graph state
    """
    state['task_history'].append(f"{datetime.now().isoformat()}: {task}")
    return state

class StateManager:
    """
    Manages application state, validation, and (optionally) persistence.
    """
    def __init__(self, db_manager: Optional[Any] = None) -> None:
        """
        Args:
            db_manager (Optional[Any]): Optional database manager for persistence
        """
        self.sessions: Dict[str, MessageState] = {}
        self.db_manager = db_manager
        self.validator = StateValidator()
        self._last_update = datetime.now()
        self._update_count = 0
        self._error_count = 0

    def _check_rate_limit(self) -> None:
        """
        Prevent too frequent updates.

        Raises:
            StateUpdateError: If updates are happening too frequently
        """
        current_time = datetime.now()
        if (current_time - self._last_update) < timedelta(milliseconds=100):
            self._update_count += 1
            if self._update_count > 100:
                raise StateUpdateError("Too many rapid state updates")
        else:
            self._update_count = 0
        self._last_update = current_time

    def get_session(self, session_id: str) -> MessageState:
        """
        Get or create a message state for a session.
        Args:
            session_id (str): The ID of the session
        Returns:
            MessageState: The message state object
        """
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
        metadata: Optional[Dict[str, Any]] = None
    ) -> MessageState:
        """
        Update a session with a new message.

        Args:
            session_id (str): The ID of the session to update
            role (MessageRole): The role of the message sender
            content (str): The message content
            metadata (Optional[Dict[str, Any]]): Optional metadata for the message

        Returns:
            MessageState: The updated message state

        Raises:
            StateUpdateError: If the message sequence is invalid or update fails
        """
        try:
            self._check_rate_limit()
            session = self.get_session(session_id)
            last_message = session.get_last_message()
            if last_message:
                if role == last_message.role == MessageRole.USER:
                    raise StateUpdateError("Cannot have two consecutive user messages")
                if role == last_message.role == MessageRole.ASSISTANT:
                    raise StateUpdateError("Cannot have two consecutive assistant messages")
            await session.add_message(role, content, metadata)
            return session
        except Exception as e:
            self._error_count += 1
            raise StateUpdateError(f"Failed to update session: {str(e)}") from e

    def get_all_sessions(self) -> List[MessageState]:
        """
        Get all active sessions.

        Returns:
            List[MessageState]: All session states
        """
        return list(self.sessions.values())

    async def update_agent_state(
        self,
        session_id: str,
        agent_id: str,
        status: Dict[str, Any]
    ) -> None:
        """
        Update an agent's state within a session.

        Args:
            session_id (str): The session ID
            agent_id (str): The agent's ID
            status (Dict[str, Any]): The new status data

        Raises:
            StateUpdateError: If the update fails
        """
        try:
            self._check_rate_limit()
            session = self.get_session(session_id)
            if not self.validator.validate_agent_state(agent_id, status):
                raise ValidationError(f"Invalid agent state structure for {agent_id}")
            await session.update_agent_state(agent_id, status)
        except Exception as e:
            self._error_count += 1
            raise StateUpdateError(f"Failed to update agent state: {str(e)}") from e

    async def start_task(
        self,
        session_id: str,
        task: str
    ) -> None:
        """
        Start a new task in the session.

        Args:
            session_id (str): The session ID
            task (str): The task description

        Raises:
            StateUpdateError: If the task cannot be started
        """
        try:
            self._check_rate_limit()
            session = self.get_session(session_id)
            current_status = session.current_task_status
            if not self.validator.validate_task_transition(current_status, TaskStatus.IN_PROGRESS):
                raise StateTransitionError(
                    f"Invalid task transition from {current_status} to {TaskStatus.IN_PROGRESS}"
                )
            await session.start_task(task)
        except Exception as e:
            self._error_count += 1
            raise StateUpdateError(f"Failed to start task: {str(e)}") from e

    async def complete_task(
        self,
        session_id: str,
        result: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Complete the current task in the session.

        Args:
            session_id (str): The session ID
            result (Optional[Dict[str, Any]]): Optional task result data

        Raises:
            StateUpdateError: If the task cannot be completed
        """
        try:
            self._check_rate_limit()
            session = self.get_session(session_id)
            if not session.current_task:
                raise StateError("No active task to complete")
            current_status = session.current_task_status
            if not self.validator.validate_task_transition(current_status, TaskStatus.COMPLETED):
                raise StateTransitionError(
                    f"Invalid task transition from {current_status} to {TaskStatus.COMPLETED}"
                )
            await session.complete_task(result)
        except Exception as e:
            self._error_count += 1
            raise StateUpdateError(f"Failed to complete task: {str(e)}") from e

    async def fail_task(
        self,
        session_id: str,
        error: str
    ) -> None:
        """
        Mark the current task as failed in the session.

        Args:
            session_id (str): The session ID
            error (str): The error message

        Raises:
            StateUpdateError: If the task cannot be marked as failed
        """
        try:
            self._check_rate_limit()
            session = self.get_session(session_id)
            if not session.current_task:
                raise StateError("No active task to fail")
            current_status = session.current_task_status
            if not self.validator.validate_task_transition(current_status, TaskStatus.FAILED):
                raise StateTransitionError(
                    f"Invalid task transition from {current_status} to {TaskStatus.FAILED}"
                )
            await session.fail_task(error)
        except Exception as e:
            self._error_count += 1
            raise StateUpdateError(f"Failed to mark task as failed: {str(e)}") from e

    def get_error_stats(self) -> Dict[str, int]:
        """
        Get error statistics.

        Returns:
            Dict[str, int]: Error and update counts
        """
        return {
            "error_count": self._error_count,
            "update_count": self._update_count
        }

    def get_agent_state(
        self,
        session_id: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """
        Get an agent's state from a session.

        Args:
            session_id (str): The session ID
            agent_id (str): The agent's ID

        Returns:
            Dict[str, Any]: The agent's state, or an empty dict if not found
        """
        session = self.get_session(session_id)
        return session.get_agent_state(agent_id)

    def get_session_context(
        self,
        session_id: str,
        window_size: int = 5
    ) -> List[Message]:
        """
        Get recent messages from a session.

        Args:
            session_id (str): The session ID
            window_size (int): Number of recent messages to return

        Returns:
            List[Message]: The most recent messages
        """
        session = self.get_session(session_id)
        return session.get_context_window(window_size)

    def get_task_history(
        self,
        session_id: str
    ) -> List[str]:
        """
        Get the task history for a session.

        Args:
            session_id (str): The session ID

        Returns:
            List[str]: Task history entries
        """
        session = self.get_session(session_id)
        return session.task_history 
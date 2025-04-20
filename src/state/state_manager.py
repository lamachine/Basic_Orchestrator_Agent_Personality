"""
State Manager Module - Central persistence and retrieval system for application state.

This module defines the StateManager class which provides a unified interface for 
storing, retrieving, and manipulating application state, including:

1. Conversation persistence - storing and retrieving conversation history and metadata
2. Message management - adding, retrieving, and organizing messages within conversations
3. Database abstraction - providing a clean interface to the underlying Supabase database
4. State validation - ensuring data integrity through Pydantic models
5. Transaction management - handling atomic operations for data consistency

The StateManager is a critical infrastructure component used by the BaseAgent and its
specialized implementations to maintain persistent state across sessions and 
ensure data consistency throughout the application.

This architecture centralizes all state operations, providing a single source of truth
for the application state while isolating the details of the underlying database
implementation from the rest of the application.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from src.state.state_models import (
    Message, 
    MessageRole, 
    ConversationState, 
    TaskStatus, 
    GraphState
)
from src.state.state_errors import (
    StateError, 
    ValidationError, 
    StateUpdateError, 
    StateTransitionError
)
from src.state.state_validator import StateValidator

def create_initial_state() -> GraphState:
    """
    Create a new GraphState with initial values.
    
    Returns:
        A new initialized GraphState
    """
    return GraphState(
        messages=[],
        conversation_state=ConversationState(),
        agent_states={},
        current_task=None,
        task_history=[],
        agent_results={},
        final_result=None
    )

def update_agent_state(state: GraphState, agent_id: str, update: Dict[str, Any]) -> GraphState:
    """
    Update an agent's state with validation.
    
    Args:
        state: The current graph state
        agent_id: The ID of the agent to update
        update: The state updates to apply
        
    Returns:
        The updated graph state
    """
    if agent_id not in state['agent_states']:
        state['agent_states'][agent_id] = {}
    state['agent_states'][agent_id].update(update)
    return state

def add_task_to_history(state: GraphState, task: str) -> GraphState:
    """
    Add a task to the history with timestamp.
    
    Args:
        state: The current graph state
        task: The task description
        
    Returns:
        The updated graph state
    """
    state['task_history'].append(f"{datetime.now().isoformat()}: {task}")
    return state

class StateManager:
    """
    Manager class for maintaining state consistency and validation.
    """
    
    def __init__(self, state: GraphState):
        """
        Initialize the state manager.
        
        Args:
            state: The initial graph state
        """
        self.state = state
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
            if self._update_count > 100:  # Arbitrary limit
                raise StateUpdateError("Too many rapid state updates")
        else:
            self._update_count = 0
        self._last_update = current_time

    def update_conversation(self, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """
        Add a message and update conversation state with validation.
        
        Args:
            role: The role of the message sender
            content: The message content
            metadata: Optional metadata for the message
            
        Returns:
            The created message
            
        Raises:
            StateUpdateError: If the update fails validation
        """
        try:
            self._check_rate_limit()
            message = Message(role=role, content=content, metadata=metadata or {})
            temp_messages = self.state['messages'] + [message]
            if not self.validator.validate_message_sequence(temp_messages):
                raise ValidationError("Invalid message sequence")
            message = self.state['conversation_state'].add_message(role, content, metadata)
            self.state['messages'].append(message)
            return message
        except Exception as e:
            self._error_count += 1
            raise StateUpdateError(f"Failed to update conversation: {str(e)}") from e

    def update_agent_state(self, agent_id: str, status: Dict[str, Any]) -> None:
        """
        Update agent state with validation.
        
        Args:
            agent_id: The ID of the agent to update
            status: The status updates to apply
            
        Raises:
            StateUpdateError: If the update fails validation
        """
        try:
            self._check_rate_limit()
            if not self.validator.validate_agent_state(agent_id, status):
                raise ValidationError(f"Invalid agent state structure for {agent_id}")
            if agent_id not in self.state['agent_states']:
                self.state['agent_states'][agent_id] = {}
            self.state['agent_states'][agent_id].update(status)
        except Exception as e:
            self._error_count += 1
            raise StateUpdateError(f"Failed to update agent state: {str(e)}") from e

    def set_task(self, task: str) -> None:
        """
        Set task with validation.
        
        Args:
            task: The task description
            
        Raises:
            StateUpdateError: If the task update fails
            StateTransitionError: If the task transition is invalid
        """
        try:
            self._check_rate_limit()
            current_status = self.state['conversation_state'].current_task_status
            if not self.validator.validate_task_transition(current_status, TaskStatus.IN_PROGRESS):
                raise StateTransitionError(
                    f"Invalid task transition from {current_status} to {TaskStatus.IN_PROGRESS}"
                )
            self.state['current_task'] = task
            self.state['task_history'].append(f"{datetime.now().isoformat()}: {task}")
            self.state['conversation_state'].current_task_status = TaskStatus.IN_PROGRESS
        except Exception as e:
            self._error_count += 1
            raise StateUpdateError(f"Failed to set task: {str(e)}") from e

    def complete_task(self, result: Optional[str] = None) -> None:
        """
        Complete task with validation.
        
        Args:
            result: Optional result from the completed task
            
        Raises:
            StateError: If there is no active task
            StateTransitionError: If the task transition is invalid
            StateUpdateError: If the task completion fails
        """
        try:
            self._check_rate_limit()
            if not self.state['current_task']:
                raise StateError("No active task to complete")
            current_status = self.state['conversation_state'].current_task_status
            if not self.validator.validate_task_transition(current_status, TaskStatus.COMPLETED):
                raise StateTransitionError(
                    f"Invalid task transition from {current_status} to {TaskStatus.COMPLETED}"
                )
            self.state['conversation_state'].current_task_status = TaskStatus.COMPLETED
            if result:
                self.state['agent_results'][self.state['current_task']] = result
            self.state['current_task'] = None
        except Exception as e:
            self._error_count += 1
            raise StateUpdateError(f"Failed to complete task: {str(e)}") from e

    def fail_task(self, error: str) -> None:
        """
        Fail task with validation.
        
        Args:
            error: The error description
            
        Raises:
            StateError: If there is no active task
            StateTransitionError: If the task transition is invalid
            StateUpdateError: If the task failure update fails
        """
        try:
            self._check_rate_limit()
            if not self.state['current_task']:
                raise StateError("No active task to fail")
            current_status = self.state['conversation_state'].current_task_status
            if not self.validator.validate_task_transition(current_status, TaskStatus.FAILED):
                raise StateTransitionError(
                    f"Invalid task transition from {current_status} to {TaskStatus.FAILED}"
                )
            self.state['conversation_state'].current_task_status = TaskStatus.FAILED
            task_name = self.state['current_task']
            self.state['task_history'].append(
                f"{datetime.now().isoformat()}: FAILED: {task_name} - {error}"
            )
            self.state['current_task'] = None
        except Exception as e:
            self._error_count += 1
            raise StateUpdateError(f"Failed to update task failure: {str(e)}") from e

    def get_error_stats(self) -> Dict[str, int]:
        """
        Get error statistics.
        
        Returns:
            Dictionary with error statistics
        """
        return {
            "error_count": self._error_count,
            "update_count": self._update_count
        }

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """
        Get the state of a specific agent.
        
        Args:
            agent_id: The ID of the agent
            
        Returns:
            The agent's state, or an empty dict if not found
        """
        return self.state['agent_states'].get(agent_id, {})

    def get_conversation_context(self, window_size: int = 5) -> List[Message]:
        """
        Get the recent conversation context.
        
        Args:
            window_size: The number of recent messages to include
            
        Returns:
            List of the most recent messages
        """
        return self.state['conversation_state'].get_context_window(window_size)

    def get_task_history(self) -> List[str]:
        """
        Get the task history.
        
        Returns:
            List of task history entries
        """
        return self.state['task_history']

    def get_current_state(self) -> GraphState:
        """
        Get the current full graph state.
        
        Returns:
            The current graph state
        """
        return self.state 
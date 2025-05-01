"""
Validator for state operations.

This module provides validation functions for state operations, ensuring that
state transitions and updates meet required constraints.
"""

from typing import Dict, Any, List

from src.state.state_models import TaskStatus, Message

class StateValidator:
    """
    Utility class for validating state operations.
    """
    
    @staticmethod
    def validate_task_transition(current_status: TaskStatus, new_status: TaskStatus) -> bool:
        """
        Validate if a task status transition is allowed.

        Args:
            current_status (TaskStatus): The current task status
            new_status (TaskStatus): The proposed new task status

        Returns:
            bool: True if the transition is valid, False otherwise
        """
        valid_transitions = {
            TaskStatus.PENDING: [TaskStatus.IN_PROGRESS, TaskStatus.FAILED],
            TaskStatus.IN_PROGRESS: [TaskStatus.COMPLETED, TaskStatus.FAILED],
            TaskStatus.COMPLETED: [],  # Terminal state
            TaskStatus.FAILED: [TaskStatus.PENDING]  # Can retry failed tasks
        }
        return new_status in valid_transitions.get(current_status, [])

    @staticmethod
    def validate_message_sequence(messages: List[Message]) -> bool:
        """
        Validate message sequence for consistency.

        Args:
            messages (List[Message]): List of messages to validate

        Returns:
            bool: True if the messages are in chronological order, False otherwise
        """
        if not messages:
            return True
        timestamps = [msg.created_at for msg in messages]
        return all(t1 <= t2 for t1, t2 in zip(timestamps, timestamps[1:]))

    @staticmethod
    def validate_agent_state(agent_id: str, state: Dict[str, Any]) -> bool:
        """
        Validate agent state structure.

        Args:
            agent_id (str): The ID of the agent
            state (Dict[str, Any]): The agent state to validate

        Returns:
            bool: True if the state has all required fields, False otherwise
        """
        required_fields = {'status'}
        return all(field in state for field in required_fields) 
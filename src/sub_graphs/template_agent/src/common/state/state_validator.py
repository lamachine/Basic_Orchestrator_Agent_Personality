"""
Validator for state operations.

This module provides validation functions for state operations, ensuring that
state transitions and updates meet required constraints.
"""

from typing import Dict, Any, List
from datetime import datetime

from .state_models import TaskStatus, Message, MessageStatus, MessageType

class StateValidator:
    """Utility class for validating state operations."""
    
    @staticmethod
    def validate_task_transition(current_status: TaskStatus, new_status: TaskStatus) -> bool:
        """Validate if a task status transition is allowed."""
        valid_transitions = {
            TaskStatus.PENDING: [TaskStatus.IN_PROGRESS, TaskStatus.FAILED],
            TaskStatus.IN_PROGRESS: [TaskStatus.COMPLETED, TaskStatus.FAILED],
            TaskStatus.COMPLETED: [],  # Terminal state
            TaskStatus.FAILED: [TaskStatus.PENDING]  # Can retry failed tasks
        }
        return new_status in valid_transitions.get(current_status, [])

    @staticmethod
    def validate_message_sequence(messages: List[Message]) -> bool:
        """Validate message sequence for consistency."""
        if not messages:
            return True
        timestamps = [msg.timestamp for msg in messages]
        return all(t1 <= t2 for t1, t2 in zip(timestamps, timestamps[1:]))

    @staticmethod
    def validate_agent_state(agent_id: str, state: Dict[str, Any]) -> bool:
        """Validate agent state structure."""
        required_fields = {'status'}
        return all(field in state for field in required_fields)

    @staticmethod
    def validate_message_status_transition(current_status: MessageStatus, new_status: MessageStatus) -> bool:
        """Validate if a message status transition is allowed."""
        valid_transitions = {
            MessageStatus.PENDING: [MessageStatus.RUNNING, MessageStatus.ERROR],
            MessageStatus.RUNNING: [MessageStatus.SUCCESS, MessageStatus.ERROR, MessageStatus.PARTIAL],
            MessageStatus.PARTIAL: [MessageStatus.SUCCESS, MessageStatus.ERROR],
            MessageStatus.SUCCESS: [],  # Terminal state
            MessageStatus.ERROR: [MessageStatus.PENDING],  # Can retry failed messages
            MessageStatus.COMPLETED: []  # Terminal state
        }
        return new_status in valid_transitions.get(current_status, [])

    @staticmethod
    def validate_message_type_for_role(role: str, message_type: MessageType) -> bool:
        """Validate if a message type is valid for a given role."""
        valid_types = {
            'user': [MessageType.USER_INPUT, MessageType.REQUEST],
            'assistant': [MessageType.RESPONSE, MessageType.LLM_RESPONSE, MessageType.TOOL_CALL],
            'system': [MessageType.SYSTEM_PROMPT, MessageType.STATUS],
            'tool': [MessageType.TOOL_RESULT, MessageType.TOOL_CALL]
        }
        return message_type in valid_types.get(role, []) 
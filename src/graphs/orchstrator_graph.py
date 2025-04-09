# Standard library imports
import asyncio
import os
from typing import Annotated, Dict, List, Any, Optional, Union, Type
from typing_extensions import TypedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
import uuid
from enum import Enum

# Third-party imports
from pydantic import ValidationError, BaseModel, Field, field_validator, model_validator

# LangGraph imports
from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import get_stream_writer
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

# Remove duplicate imports and sys.path manipulation
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

# Enums for validation
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

# Message Models with validation
class Message(BaseModel):
    role: MessageRole
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator('content')
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Content cannot be empty')
        return v.strip()

    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        return v or {}

class ConversationState(BaseModel):
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[Message] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)
    current_task_status: TaskStatus = Field(default=TaskStatus.PENDING)

    @model_validator(mode='before')
    @classmethod
    def update_timestamp(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values['last_updated'] = datetime.now()
        return values

    def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """Add a new message to the conversation with validation"""
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.last_updated = datetime.now()
        return message

    def get_last_message(self) -> Optional[Message]:
        """Get the last message in the conversation"""
        return self.messages[-1] if self.messages else None

    def get_context_window(self, n: int = 5) -> List[Message]:
        """Get the last n messages for context"""
        return self.messages[-n:] if self.messages else []

# Graph State with validation helpers
class GraphState(TypedDict):
    messages: Annotated[List[Message], lambda x, y: x + y]
    conversation_state: ConversationState
    agent_states: Dict[str, Any]
    current_task: Optional[str]
    task_history: List[str]
    agent_results: Dict[str, Any]
    final_result: Optional[str]

# Error classes
class StateError(Exception):
    """Base class for state-related errors"""
    pass

class ValidationError(StateError):
    """Raised when state validation fails"""
    pass

class StateUpdateError(StateError):
    """Raised when state update fails"""
    pass

class StateTransitionError(StateError):
    """Raised when state transition is invalid"""
    pass

# State validation class
class StateValidator:
    @staticmethod
    def validate_task_transition(current_status: TaskStatus, new_status: TaskStatus) -> bool:
        """Validate if a task status transition is allowed"""
        valid_transitions = {
            TaskStatus.PENDING: [TaskStatus.IN_PROGRESS, TaskStatus.FAILED],
            TaskStatus.IN_PROGRESS: [TaskStatus.COMPLETED, TaskStatus.FAILED],
            TaskStatus.COMPLETED: [],  # Terminal state
            TaskStatus.FAILED: [TaskStatus.PENDING]  # Can retry failed tasks
        }
        return new_status in valid_transitions.get(current_status, [])

    @staticmethod
    def validate_message_sequence(messages: List[Message]) -> bool:
        """Validate message sequence for consistency"""
        if not messages:
            return True
        timestamps = [msg.created_at for msg in messages]
        return all(t1 <= t2 for t1, t2 in zip(timestamps, timestamps[1:]))

    @staticmethod
    def validate_agent_state(agent_id: str, state: Dict[str, Any]) -> bool:
        """Validate agent state structure"""
        required_fields = {'status'}
        return all(field in state for field in required_fields)

# Helper functions
def create_initial_state() -> GraphState:
    """Create a new GraphState with initial values"""
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
    """Update an agent's state with validation"""
    if agent_id not in state['agent_states']:
        state['agent_states'][agent_id] = {}
    state['agent_states'][agent_id].update(update)
    return state

def add_task_to_history(state: GraphState, task: str) -> GraphState:
    """Add a task to the history with timestamp"""
    state['task_history'].append(f"{datetime.now().isoformat()}: {task}")
    return state

# State Management class
class StateManager:
    def __init__(self, state: GraphState):
        self.state = state
        self.validator = StateValidator()
        self._last_update = datetime.now()
        self._update_count = 0
        self._error_count = 0

    def _check_rate_limit(self) -> None:
        """Prevent too frequent updates"""
        current_time = datetime.now()
        if (current_time - self._last_update) < timedelta(milliseconds=100):
            self._update_count += 1
            if self._update_count > 100:  # Arbitrary limit
                raise StateUpdateError("Too many rapid state updates")
        else:
            self._update_count = 0
        self._last_update = current_time

    def update_conversation(self, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """Add a message and update conversation state with validation"""
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
        """Update agent state with validation"""
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
        """Set task with validation"""
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
        """Complete task with validation"""
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
        """Fail task with validation"""
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
            self.state['agent_results'][self.state['current_task']] = {"error": error}
            self.state['current_task'] = None
        except Exception as e:
            self._error_count += 1
            raise StateUpdateError(f"Failed to fail task: {str(e)}") from e

    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics"""
        return {
            "error_count": self._error_count,
            "update_count": self._update_count
        }

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """Get an agent's current state"""
        return self.state['agent_states'].get(agent_id, {})

    def get_conversation_context(self, window_size: int = 5) -> List[Message]:
        """Get recent conversation context"""
        return self.state['conversation_state'].get_context_window(window_size)

    def get_task_history(self) -> List[str]:
        """Get complete task history"""
        return self.state['task_history']

    def get_current_state(self) -> GraphState:
        """Get current complete state"""
        return self.state

# ## Agent 1 node (Commented out - Missing dependencies and seems like leftover template code)
# async def agent_template_node(ctx: StateGraph, state: GraphState, writer) -> Dict[str, Any]:
#     """Run the agent with enhanced state management."""
#     state_manager = StateManager(state)
    
#     try:
#         # Update agent state
#         state_manager.update_agent_state("agent_template", {"status": "running"})
#         state_manager.set_task("template_task")
        
#         writer("\n#### Getting Agent Template recommendations...\n")
#         # These keys/classes are not defined in this scope:
#         # Key_Input_Data_Structure = state["Key_Input_Data_Structure"]
#         # user_graph_prefs = state['user_graph_prefs'] 
#         # agent_template_dependencies = Agent_Template_Dependencies(user_graph_prefs=user_graph_prefs)
        
#         # prompt = f"I need Agent Template recommendations from ..."
        
#         # This agent is not defined/imported:
#         # result = await input_query_agent.run(prompt, deps=agent_template_dependencies)
#         result_data = "Placeholder result" # Placeholder

#         state_manager.update_conversation(
#             role=MessageRole.ASSISTANT,
#             content=result_data, # Using placeholder
#             metadata={"agent": "template", "status": "success"}
#         )
        
#         state_manager.complete_task(result_data) # Using placeholder
#         return state_manager.get_current_state()
        
#     except StateError as e:
#         # Handle state-specific errors
#         state_manager.fail_task(f"State error: {str(e)}")
#         writer(f"\n#### Error in state management: {str(e)}\n")
#         return state_manager.get_current_state()
        
#     except Exception as e:
#         # Handle unexpected errors
#         state_manager.fail_task(f"Unexpected error: {str(e)}")
#         writer(f"\n#### Unexpected error: {str(e)}\n")
#         raise
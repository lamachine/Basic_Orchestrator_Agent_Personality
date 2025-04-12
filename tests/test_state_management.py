import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

from src.graphs.orchestrator_graph import (
    StateManager, StateValidator, Message, MessageRole, TaskStatus,
    StateError, ValidationError, StateUpdateError, StateTransitionError,
    GraphState, ConversationState
)

# Fixtures
@pytest.fixture
def empty_state() -> GraphState:
    """Create an empty graph state with ConversationState instance."""
    return GraphState(
        messages=[],
        conversation_state=ConversationState(conversation_id='test-123'),
        agent_states={},
        current_task=None,
        task_history=[],
        agent_results={},
        final_result=None
    )

@pytest.fixture
def state_manager(empty_state):
    """Create a state manager instance"""
    return StateManager(empty_state)

@pytest.fixture
def validator():
    """Create a state validator instance"""
    return StateValidator()

# State Validator Tests
class TestStateValidator:
    def test_task_transition_valid(self, validator):
        """Test valid task transitions"""
        assert validator.validate_task_transition(TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
        assert validator.validate_task_transition(TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED)
        assert validator.validate_task_transition(TaskStatus.IN_PROGRESS, TaskStatus.FAILED)

    def test_task_transition_invalid(self, validator):
        """Test invalid task transitions"""
        assert not validator.validate_task_transition(TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS)
        assert not validator.validate_task_transition(TaskStatus.PENDING, TaskStatus.COMPLETED)

    def test_message_sequence_valid(self, validator):
        """Test valid message sequences"""
        messages = [
            Message(
                role=MessageRole.USER,
                content="Hello",
                created_at=datetime.now()
            ),
            Message(
                role=MessageRole.ASSISTANT,
                content="Hi",
                created_at=datetime.now() + timedelta(seconds=1)
            )
        ]
        assert validator.validate_message_sequence(messages)

    def test_message_sequence_invalid(self, validator):
        """Test invalid message sequences"""
        messages = [
            Message(
                role=MessageRole.USER,
                content="Hello",
                created_at=datetime.now() + timedelta(seconds=1)
            ),
            Message(
                role=MessageRole.ASSISTANT,
                content="Hi",
                created_at=datetime.now()
            )
        ]
        assert not validator.validate_message_sequence(messages)

    def test_agent_state_valid(self, validator):
        """Test valid agent state"""
        assert validator.validate_agent_state("agent1", {"status": "running"})

    def test_agent_state_invalid(self, validator):
        """Test invalid agent state"""
        assert not validator.validate_agent_state("agent1", {"invalid": "state"})

# State Manager Tests
class TestStateManager:
    def test_update_conversation(self, state_manager):
        """Test conversation update"""
        message = state_manager.update_conversation(
            role=MessageRole.USER,
            content="Hello",
            metadata={"source": "test"}
        )
        assert message.role == MessageRole.USER
        assert message.content == "Hello"
        assert message.metadata["source"] == "test"
        assert len(state_manager.state['messages']) == 1

    def test_update_conversation_invalid(self, state_manager):
        """Test invalid conversation update"""
        with pytest.raises(StateUpdateError):
            state_manager.update_conversation(
                role=MessageRole.USER,
                content="",  # Empty content should fail
                metadata={}
            )

    def test_rate_limiting(self, state_manager):
        """Test rate limiting"""
        for _ in range(100):  # Should work
            state_manager.update_conversation(
                role=MessageRole.USER,
                content="test",
                metadata={}
            )
        
        with pytest.raises(StateUpdateError, match="Too many rapid state updates"):
            for _ in range(101):  # Should fail
                state_manager.update_conversation(
                    role=MessageRole.USER,
                    content="test",
                    metadata={}
                )

    def test_task_lifecycle(self, state_manager):
        """Test complete task lifecycle"""
        # Set task
        state_manager.set_task("test_task")
        assert state_manager.state['current_task'] == "test_task"
        assert state_manager.state['conversation_state'].current_task_status == TaskStatus.IN_PROGRESS

        # Complete task
        state_manager.complete_task("success")
        assert state_manager.state['current_task'] is None
        assert state_manager.state['conversation_state'].current_task_status == TaskStatus.COMPLETED
        assert state_manager.state['agent_results']["test_task"] == "success"

    def test_task_failure(self, state_manager):
        """Test task failure handling"""
        state_manager.set_task("test_task")
        state_manager.fail_task("error message")
        assert state_manager.state['current_task'] is None
        assert state_manager.state['conversation_state'].current_task_status == TaskStatus.FAILED
        assert state_manager.state['agent_results']["test_task"]["error"] == "error message"

    def test_error_stats(self, state_manager):
        """Test error statistics tracking"""
        try:
            state_manager.update_conversation(
                role=MessageRole.USER,
                content="",  # Should cause error
                metadata={}
            )
        except StateUpdateError:
            pass

        stats = state_manager.get_error_stats()
        assert stats["error_count"] == 1
        assert "update_count" in stats

# Integration Tests
class TestStateIntegration:
    def test_complete_workflow(self, state_manager):
        """Test a complete workflow with multiple state changes"""
        # Start task
        state_manager.set_task("integration_test")
        assert state_manager.state['current_task'] == "integration_test"

        # Update agent state
        state_manager.update_agent_state("agent1", {"status": "running"})
        assert state_manager.state['agent_states']["agent1"]["status"] == "running"

        # Add messages
        state_manager.update_conversation(
            role=MessageRole.USER,
            content="Request",
            metadata={"type": "command"}
        )
        state_manager.update_conversation(
            role=MessageRole.ASSISTANT,
            content="Response",
            metadata={"type": "result"}
        )

        # Complete task
        state_manager.complete_task("workflow complete")

        # Verify final state
        assert len(state_manager.state['messages']) == 2
        assert len(state_manager.state['task_history']) == 1
        assert state_manager.state['conversation_state'].current_task_status == TaskStatus.COMPLETED
        assert state_manager.state['agent_results']["integration_test"] == "workflow complete" 
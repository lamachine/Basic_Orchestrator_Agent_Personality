"""
Tests for state models.
"""

import pytest
from datetime import datetime, timezone
from src.common.state.state_models import (
    State,
    StateType,
    StateStatus,
    StateRole
)

def test_state_creation():
    """Test basic state creation."""
    state = State(
        content="Test state",
        role=StateRole.USER,
        state_type=StateType.TEXT
    )
    assert state.content == "Test state"
    assert state.role == StateRole.USER
    assert state.state_type == StateType.TEXT
    assert state.status == StateStatus.PENDING
    assert isinstance(state.timestamp, datetime)
    assert state.timestamp.tzinfo == timezone.utc

def test_state_with_metadata():
    """Test state creation with metadata."""
    metadata = {"key": "value"}
    state = State(
        content="Test state",
        role=StateRole.ASSISTANT,
        state_type=StateType.TEXT,
        metadata=metadata
    )
    assert state.metadata == metadata

def test_state_status_transitions():
    """Test state status transitions."""
    state = State(
        content="Test state",
        role=StateRole.USER,
        state_type=StateType.TEXT
    )
    assert state.status == StateStatus.PENDING
    
    state.status = StateStatus.PROCESSING
    assert state.status == StateStatus.PROCESSING
    
    state.status = StateStatus.COMPLETED
    assert state.status == StateStatus.COMPLETED
    
    state.status = StateStatus.FAILED
    assert state.status == StateStatus.FAILED

def test_state_types():
    """Test different state types."""
    state = State(
        content="Test state",
        role=StateRole.USER,
        state_type=StateType.TEXT
    )
    assert state.state_type == StateType.TEXT
    
    state = State(
        content="Test code",
        role=StateRole.ASSISTANT,
        state_type=StateType.CODE
    )
    assert state.state_type == StateType.CODE
    
    state = State(
        content="Test error",
        role=StateRole.SYSTEM,
        state_type=StateType.ERROR
    )
    assert state.state_type == StateType.ERROR

def test_state_roles():
    """Test different state roles."""
    state = State(
        content="Test state",
        role=StateRole.USER,
        state_type=StateType.TEXT
    )
    assert state.role == StateRole.USER
    
    state = State(
        content="Test state",
        role=StateRole.ASSISTANT,
        state_type=StateType.TEXT
    )
    assert state.role == StateRole.ASSISTANT
    
    state = State(
        content="Test state",
        role=StateRole.SYSTEM,
        state_type=StateType.TEXT
    )
    assert state.role == StateRole.SYSTEM

def test_state_validation():
    """Test state validation."""
    with pytest.raises(ValueError):
        State(
            content="",
            role=StateRole.USER,
            state_type=StateType.TEXT
        )
    
    with pytest.raises(ValueError):
        State(
            content="Test state",
            role="invalid_role",
            state_type=StateType.TEXT
        )
    
    with pytest.raises(ValueError):
        State(
            content="Test state",
            role=StateRole.USER,
            state_type="invalid_type"
        )

def test_state_serialization():
    """Test state serialization."""
    state = State(
        content="Test state",
        role=StateRole.USER,
        state_type=StateType.TEXT,
        metadata={"key": "value"}
    )
    state_dict = state.dict()
    assert state_dict["content"] == "Test state"
    assert state_dict["role"] == "user"
    assert state_dict["state_type"] == "text"
    assert state_dict["metadata"] == {"key": "value"}
    assert "timestamp" in state_dict
    assert "status" in state_dict 
"""
Tests for state_errors.py

This module tests the error classes for state management, including:
1. StateError base class
2. Specialized error subclasses
3. Error inheritance
"""

import pytest

from ...src.common.state.state_errors import (
    StateError,
    ValidationError,
    StateUpdateError,
    StateTransitionError,
    MessageError,
    TaskError,
    AgentStateError,
    PersistenceError
)


def test_state_error_base_class():
    """Test StateError base class."""
    # Test case: Normal operation - should pass
    error = StateError("Test error message")
    
    # Verify it's a proper exception
    assert isinstance(error, Exception)
    assert str(error) == "Test error message"
    
    # Verify proper inheritance
    assert issubclass(StateError, Exception)


def test_specialized_error_classes():
    """Test specialized error subclasses."""
    # Test case: Normal operation - should pass
    validation_error = ValidationError("Validation failed")
    update_error = StateUpdateError("Update failed")
    transition_error = StateTransitionError("Invalid transition")
    message_error = MessageError("Message operation failed")
    task_error = TaskError("Task operation failed")
    agent_state_error = AgentStateError("Agent state operation failed")
    persistence_error = PersistenceError("Persistence operation failed")
    
    # Verify proper inheritance
    assert isinstance(validation_error, StateError)
    assert isinstance(update_error, StateError)
    assert isinstance(transition_error, StateError)
    assert isinstance(message_error, StateError)
    assert isinstance(task_error, StateError)
    assert isinstance(agent_state_error, StateError)
    assert isinstance(persistence_error, StateError)
    
    # Verify error messages
    assert str(validation_error) == "Validation failed"
    assert str(update_error) == "Update failed"
    assert str(transition_error) == "Invalid transition"
    assert str(message_error) == "Message operation failed"
    assert str(task_error) == "Task operation failed"
    assert str(agent_state_error) == "Agent state operation failed"
    assert str(persistence_error) == "Persistence operation failed"


def test_error_raising():
    """Test raising the errors."""
    # Test case: Error condition - should raise
    with pytest.raises(ValidationError) as excinfo:
        raise ValidationError("Custom validation error")
    assert "Custom validation error" in str(excinfo.value)
    
    with pytest.raises(StateUpdateError) as excinfo:
        raise StateUpdateError("Custom update error")
    assert "Custom update error" in str(excinfo.value)
    
    # Test raising with custom data
    with pytest.raises(TaskError) as excinfo:
        error_data = {"task_id": "123", "status": "failed"}
        raise TaskError("Task error with data", error_data)
    assert "Task error with data" in str(excinfo.value)


def test_error_edge_cases():
    """Test error edge cases."""
    # Test case: Edge case - empty error message
    empty_error = StateError("")
    assert str(empty_error) == ""
    
    # Test case: Edge case - nested exceptions
    try:
        try:
            raise ValueError("Original error")
        except ValueError as ve:
            raise StateError("Wrapped error") from ve
    except StateError as se:
        assert "Wrapped error" in str(se)
        assert isinstance(se.__cause__, ValueError)
        assert "Original error" in str(se.__cause__)
    
    # Test case: Edge case - error with non-string arg
    try:
        raise StateError(123)
    except StateError as se:
        assert "123" in str(se)


def test_error_class_hierarchy():
    """Test the error class hierarchy."""
    # Test case: Edge case - hierarchical error handling
    def handle_errors(error):
        if isinstance(error, ValidationError):
            return "Validation"
        elif isinstance(error, StateUpdateError):
            return "Update"
        elif isinstance(error, StateError):
            return "Generic"
        else:
            return "Unknown"
    
    # Verify that the error hierarchy is correctly detected
    assert handle_errors(ValidationError("Test")) == "Validation"
    assert handle_errors(StateUpdateError("Test")) == "Update"
    assert handle_errors(StateError("Test")) == "Generic"
    assert handle_errors(Exception("Test")) == "Unknown" 
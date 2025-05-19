"""
Tests for base_manager.py

This module tests the base manager functionality, including:
1. Initialization and configuration
2. State management
3. Message creation
4. Capability management
5. Logging functionality
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ...src.common.managers.base_manager import BaseManager, ManagerState
from ...src.common.managers.service_models import ServiceCapability, ServiceConfig
from ...src.common.managers.state_models import GraphState, Message, MessageStatus, MessageType


@pytest.fixture
def service_config():
    """Create a service configuration for testing."""
    # Create a mock ServiceConfig
    config = MagicMock(spec=ServiceConfig)
    config.enabled = True
    config.get_capability = MagicMock(
        return_value=ServiceCapability(
            name="test_capability",
            enabled=True,
            metadata={"description": "Test capability"},
        )
    )
    config.is_capability_enabled = MagicMock(return_value=True)
    config.get_merged_config = MagicMock(
        return_value={
            "name": "test_service",
            "capabilities": ["test_capability"],
            "api_url": "http://test.service",
        }
    )
    return config


@pytest.fixture
def base_manager(service_config):
    """Create a base manager for testing."""
    with patch("src.common.managers.base_manager.get_log_level", return_value=logging.DEBUG):
        manager = BaseManager(service_config)
        # Mock state_service
        manager.state_service = AsyncMock()
        manager.state_service.save_state = AsyncMock()
        manager.state_service.load_state = AsyncMock(return_value=None)
        return manager


def test_initialization(service_config):
    """Test manager initialization."""
    # Test case: Normal operation - should pass
    with patch("src.common.managers.base_manager.get_log_level", return_value=logging.DEBUG):
        manager = BaseManager(service_config)

        # Verify basic properties
        assert manager.config == service_config
        assert isinstance(manager.state, GraphState)
        assert manager._error_count == 0
        assert manager._success_count == 0
        assert manager._initialized is False
        assert manager.logger is not None


def test_manager_state_validation():
    """Test ManagerState validation."""
    # Test case: Normal operation - should pass
    state = ManagerState()
    assert isinstance(state.created_at, datetime)
    assert isinstance(state.updated_at, datetime)
    assert state.metadata == {}

    # Initialize with custom values
    custom_time = datetime(2023, 1, 1, 12, 0, 0)
    state = ManagerState(
        created_at=custom_time,
        updated_at=custom_time,
        metadata={"test_key": "test_value"},
    )
    assert state.created_at == custom_time
    assert state.updated_at == custom_time
    assert state.metadata["test_key"] == "test_value"


@pytest.mark.asyncio
async def test_context_manager(base_manager):
    """Test async context manager functionality."""
    # Mock initialize and cleanup methods
    base_manager.initialize = AsyncMock()
    base_manager.cleanup = AsyncMock()

    # Use as context manager
    async with base_manager as manager:
        assert manager == base_manager
        base_manager.initialize.assert_called_once()

    # Verify cleanup was called
    base_manager.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_initialize(base_manager):
    """Test manager initialization method."""
    # Test case: Normal operation - should pass
    await base_manager.initialize()
    assert base_manager._initialized is True


@pytest.mark.asyncio
async def test_cleanup(base_manager):
    """Test manager cleanup method."""
    # Initialize first
    base_manager._initialized = True

    # Test cleanup
    await base_manager.cleanup()

    # Verify state was persisted and manager was deinitialized
    base_manager.state_service.save_state.assert_called_once()
    assert base_manager._initialized is False


def test_setup_logging(service_config):
    """Test logging setup."""
    # Test case: Normal operation - should pass
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Initialize manager
        with patch("src.common.managers.base_manager.get_log_level", return_value=logging.DEBUG):
            manager = BaseManager(service_config)

            # Verify logger was configured
            assert manager.logger == mock_logger
            assert mock_logger.setLevel.called_with(logging.DEBUG)
            assert mock_logger.addHandler.called


def test_is_enabled(base_manager):
    """Test is_enabled property."""
    # Test case: Normal operation - should pass
    assert base_manager.is_enabled is True

    # Test case: Disabled service
    base_manager.config.enabled = False
    assert base_manager.is_enabled is False


def test_property_getters(base_manager):
    """Test property getters."""
    # Test case: Normal operation - should pass
    assert isinstance(base_manager.last_update, datetime)
    assert base_manager.error_count == 0
    assert base_manager.success_count == 0


def test_update_state_with_message(base_manager):
    """Test updating state with a message."""
    # Create test messages
    success_message = Message(
        type=MessageType.RESPONSE,
        status=MessageStatus.SUCCESS,
        content="Success message",
    )

    error_message = Message(
        type=MessageType.ERROR, status=MessageStatus.ERROR, content="Error message"
    )

    # Update state with success message
    base_manager.update_state(success_message)
    assert base_manager.state.messages[-1] == success_message
    assert base_manager._success_count == 1
    assert base_manager._error_count == 0

    # Update state with error message
    base_manager.update_state(error_message)
    assert base_manager.state.messages[-1] == error_message
    assert base_manager._success_count == 1
    assert base_manager._error_count == 1


def test_get_capability(base_manager):
    """Test getting a capability."""
    # Test case: Normal operation - should pass
    capability = base_manager.get_capability("test_capability")
    assert capability.name == "test_capability"
    assert capability.enabled is True

    # Test case: Unknown capability
    base_manager.config.get_capability.return_value = None
    assert base_manager.get_capability("unknown_capability") is None


def test_is_capability_enabled(base_manager):
    """Test checking if a capability is enabled."""
    # Test case: Normal operation - should pass
    assert base_manager.is_capability_enabled("test_capability") is True

    # Test case: Disabled capability
    base_manager.config.is_capability_enabled.return_value = False
    assert base_manager.is_capability_enabled("disabled_capability") is False


def test_get_merged_config(base_manager):
    """Test getting merged configuration."""
    # Test case: Normal operation - should pass
    config = base_manager.get_merged_config()
    assert config["name"] == "test_service"
    assert "capabilities" in config
    assert "api_url" in config


def test_create_message(base_manager):
    """Test creating a message."""
    # Test case: Normal operation - should pass
    message = base_manager.create_message(
        content="Test message",
        message_type=MessageType.REQUEST,
        data={"key": "value"},
        metadata={"source": "test"},
    )

    # Verify message
    assert message.content == "Test message"
    assert message.type == MessageType.REQUEST
    assert message.status == MessageStatus.PENDING
    assert message.data["key"] == "value"
    assert message.metadata["source"] == "test"

    # Test with minimal parameters
    minimal_message = base_manager.create_message(
        content="Minimal message", message_type=MessageType.RESPONSE
    )
    assert minimal_message.content == "Minimal message"
    assert minimal_message.type == MessageType.RESPONSE
    assert minimal_message.data == {}
    assert minimal_message.metadata == {}


def test_create_error_message(base_manager):
    """Test creating an error message."""
    # Test case: Normal operation - should pass
    error_message = base_manager.create_error_message(
        content="Test error", error_data={"error_code": 404, "reason": "Not found"}
    )

    # Verify message
    assert error_message.content == "Test error"
    assert error_message.type == MessageType.ERROR
    assert error_message.status == MessageStatus.ERROR
    assert error_message.data["error_code"] == 404
    assert error_message.data["reason"] == "Not found"
    assert "error_timestamp" in error_message.metadata

    # Test with minimal parameters
    minimal_error = base_manager.create_error_message(content="Minimal error")
    assert minimal_error.content == "Minimal error"
    assert minimal_error.type == MessageType.ERROR
    assert minimal_error.data == {}


@pytest.mark.asyncio
async def test_update_state_with_dict(base_manager):
    """Test updating state with a dictionary."""
    # Test case: Normal operation - should pass

    # Create a custom GraphState with a known attribute
    class TestState(GraphState):
        test_value: str = "initial"

    base_manager.state = TestState()

    # Update state
    await base_manager.update_state({"test_value": "updated"})

    # Verify state was updated
    assert base_manager.state.test_value == "updated"
    assert base_manager.state.updated_at > base_manager.state.created_at


@pytest.mark.asyncio
async def test_get_state(base_manager):
    """Test getting the current state."""
    # Test case: Normal operation - should pass
    state = await base_manager.get_state()
    assert state == base_manager.state


@pytest.mark.asyncio
async def test_persist_state_success(base_manager):
    """Test successfully persisting state."""
    # Test case: Normal operation - should pass
    await base_manager.persist_state()

    # Verify state service was called
    base_manager.state_service.save_state.assert_called_once_with(
        manager_name="BaseManager", state=base_manager.state
    )


@pytest.mark.asyncio
async def test_persist_state_error(base_manager):
    """Test error handling when persisting state."""
    # Test case: Error condition - should fail but handle gracefully
    base_manager.state_service.save_state.side_effect = Exception("Save failed")

    # This should not raise an exception
    await base_manager.persist_state()

    # Verify state service was called
    base_manager.state_service.save_state.assert_called_once()


@pytest.mark.asyncio
async def test_load_state_success(base_manager):
    """Test successfully loading state."""
    # Create a mock state to load
    mock_state = GraphState()
    mock_state.messages.append(
        Message(
            type=MessageType.RESPONSE,
            status=MessageStatus.SUCCESS,
            content="Loaded message",
        )
    )

    # Configure state service to return the mock state
    base_manager.state_service.load_state.return_value = mock_state

    # Load state
    await base_manager.load_state()

    # Verify state was loaded
    assert base_manager.state == mock_state
    assert len(base_manager.state.messages) == 1
    assert base_manager.state.messages[0].content == "Loaded message"

    # Verify state service was called
    base_manager.state_service.load_state.assert_called_once_with(
        manager_name="BaseManager", state_class=GraphState
    )


@pytest.mark.asyncio
async def test_load_state_error(base_manager):
    """Test error handling when loading state."""
    # Test case: Error condition - should fail but handle gracefully
    base_manager.state_service.load_state.side_effect = Exception("Load failed")

    # This should not raise an exception
    await base_manager.load_state()

    # Verify state service was called
    base_manager.state_service.load_state.assert_called_once()

    # State should remain unchanged
    assert isinstance(base_manager.state, GraphState)


@pytest.mark.asyncio
async def test_load_state_not_found(base_manager):
    """Test loading state when none is found."""
    # Test case: Edge case - no state found
    base_manager.state_service.load_state.return_value = None

    # Load state
    await base_manager.load_state()

    # Verify state service was called
    base_manager.state_service.load_state.assert_called_once()

    # State should remain unchanged
    assert isinstance(base_manager.state, GraphState)

"""
Tests for the orchestrator agent.

These tests validate the orchestrator agent's ability to process messages,
handle tools, and manage conversation state.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional

from src.agents.orchestrator_agent import OrchestratorAgent
from src.state.state_models import MessageState, MessageRole, MessageType
from src.tools.registry.tool_registry import ToolRegistry
from src.services.message_service import log_and_persist_message

# Test fixtures
@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service."""
    llm_service = MagicMock()
    llm_service.query_llm = AsyncMock(return_value={
        "response": "Test response",
        "tool_calls": []
    })
    return llm_service

@pytest.fixture
def mock_tool_registry():
    """Create a mock tool registry."""
    registry = MagicMock(spec=ToolRegistry)
    registry.get_tool = MagicMock(return_value=AsyncMock(return_value="Tool result"))
    registry.list_tools = MagicMock(return_value=["test_tool"])
    return registry

@pytest.fixture
def mock_message_state():
    """Create a mock message state."""
    state = MagicMock(spec=MessageState)
    state.add_message = AsyncMock()
    state.get_messages = MagicMock(return_value=[])
    return state

@pytest.fixture
def orchestrator_agent(mock_llm_service, mock_tool_registry):
    """Create an orchestrator agent instance with mock dependencies."""
    return OrchestratorAgent(
        llm_service=mock_llm_service,
        tool_registry=mock_tool_registry
    )

# Tests for message processing
@pytest.mark.asyncio
async def test_process_message_basic(orchestrator_agent, mock_message_state, mock_llm_service):
    """Test basic message processing."""
    # Arrange
    content = "Hello, how are you?"
    role = MessageRole.USER
    message_type = MessageType.TEXT
    
    # Act
    response = await orchestrator_agent.process_message(
        session_state=mock_message_state,
        content=content,
        role=role,
        message_type=message_type
    )
    
    # Assert
    assert response is not None
    mock_llm_service.query_llm.assert_called_once()
    mock_message_state.add_message.assert_called()

@pytest.mark.asyncio
async def test_process_message_with_tool_call(orchestrator_agent, mock_message_state, mock_llm_service, mock_tool_registry):
    """Test message processing with tool call."""
    # Arrange
    content = "Use test_tool"
    role = MessageRole.USER
    message_type = MessageType.TEXT
    
    # Mock LLM response with tool call
    mock_llm_service.query_llm.return_value = {
        "response": "I'll use the test tool",
        "tool_calls": [{
            "name": "test_tool",
            "arguments": {}
        }]
    }
    
    # Act
    response = await orchestrator_agent.process_message(
        session_state=mock_message_state,
        content=content,
        role=role,
        message_type=message_type
    )
    
    # Assert
    assert response is not None
    mock_tool_registry.get_tool.assert_called_once_with("test_tool")
    mock_message_state.add_message.assert_called()

@pytest.mark.asyncio
async def test_process_message_error_handling(orchestrator_agent, mock_message_state, mock_llm_service):
    """Test error handling in message processing."""
    # Arrange
    content = "Test message"
    role = MessageRole.USER
    message_type = MessageType.TEXT
    
    # Mock LLM service to raise an exception
    mock_llm_service.query_llm.side_effect = Exception("Test error")
    
    # Act & Assert
    with pytest.raises(Exception):
        await orchestrator_agent.process_message(
            session_state=mock_message_state,
            content=content,
            role=role,
            message_type=message_type
        )

# Tests for tool handling
@pytest.mark.asyncio
async def test_execute_tool(orchestrator_agent, mock_tool_registry):
    """Test tool execution."""
    # Arrange
    tool_name = "test_tool"
    tool_args = {"arg1": "value1"}
    
    # Act
    result = await orchestrator_agent._execute_tool(tool_name, tool_args)
    
    # Assert
    assert result == "Tool result"
    mock_tool_registry.get_tool.assert_called_once_with(tool_name)

@pytest.mark.asyncio
async def test_execute_tool_not_found(orchestrator_agent, mock_tool_registry):
    """Test tool execution with non-existent tool."""
    # Arrange
    tool_name = "non_existent_tool"
    tool_args = {}
    
    # Mock tool registry to return None for non-existent tool
    mock_tool_registry.get_tool.return_value = None
    
    # Act & Assert
    with pytest.raises(ValueError):
        await orchestrator_agent._execute_tool(tool_name, tool_args)

# Tests for conversation state management
@pytest.mark.asyncio
async def test_update_conversation_state(orchestrator_agent, mock_message_state):
    """Test conversation state updates."""
    # Arrange
    content = "Test message"
    role = MessageRole.USER
    message_type = MessageType.TEXT
    
    # Act
    await orchestrator_agent._update_conversation_state(
        session_state=mock_message_state,
        content=content,
        role=role,
        message_type=message_type
    )
    
    # Assert
    mock_message_state.add_message.assert_called_once_with(
        role=role,
        content=content,
        message_type=message_type
    )

@pytest.mark.asyncio
async def test_get_conversation_history(orchestrator_agent, mock_message_state):
    """Test getting conversation history."""
    # Arrange
    mock_message_state.get_messages.return_value = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"}
    ]
    
    # Act
    history = await orchestrator_agent._get_conversation_history(mock_message_state)
    
    # Assert
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant" 
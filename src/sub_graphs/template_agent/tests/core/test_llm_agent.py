"""Tests for LLM agent functionality."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import ValidationError

from ...src.common.agents.base_agent import BaseAgentConfig
from ...src.common.agents.llm_agent import LLMAgent
from ...src.common.messages.message_models import Message, MessageStatus, MessageType


@pytest.fixture
def llm_agent_config():
    """Create a base configuration for LLM agent tests."""
    return BaseAgentConfig(
        name="test_llm_agent",
        prompt_section="Test LLM prompt",
        api_url="http://test-llm-api",
        model="test-model",
        max_tokens=1000,
        context_window=4000,
        enable_history=True,
        enable_logging=True,
        graph_name="test_graph",
    )


@pytest.fixture
def llm_agent(llm_agent_config):
    """Create an LLM agent for testing."""
    agent = LLMAgent(llm_agent_config)
    # Mock the LLM service
    agent.llm = Mock()
    agent.llm.generate = AsyncMock()
    return agent


@pytest.fixture
def test_message():
    """Create a test message for LLM agent."""
    return Message(
        content="Test message content",
        type=MessageType.USER,
        status=MessageStatus.PENDING,
    )


def test_agent_config_validation():
    """Test BaseAgentConfig Pydantic validation."""
    # Test valid configuration
    valid_config = BaseAgentConfig(name="test_agent", prompt_section="Test prompt")
    assert valid_config.name == "test_agent"
    assert valid_config.prompt_section == "Test prompt"

    # Test required fields (name is required)
    with pytest.raises(ValidationError):
        BaseAgentConfig(prompt_section="Missing name")

    # Test type validation
    with pytest.raises(ValidationError):
        BaseAgentConfig(name="test", max_tokens="not_an_integer")

    # Test default values
    default_config = BaseAgentConfig(name="test_defaults")
    assert default_config.user_id == "developer"
    assert default_config.max_tokens == 2000
    assert default_config.context_window == 4096
    assert default_config.enable_history is True
    assert default_config.graph_name == "unknown"


def test_llm_agent_initialization_validation():
    """Test LLMAgent initialization with Pydantic validation."""
    # Test initialization with non-BaseAgentConfig
    with pytest.raises(ValidationError):
        LLMAgent({"name": "invalid_type"})

    # Test initialization with invalid config object
    invalid_config = {"name": "test", "max_tokens": "invalid"}
    with pytest.raises(ValidationError):
        LLMAgent(BaseAgentConfig(**invalid_config))


@pytest.mark.asyncio
async def test_message_validation_in_llm_query(llm_agent):
    """Test message validation in query_llm method."""
    # Test with invalid message type (not a Message object)
    with pytest.raises(AttributeError):
        await llm_agent.query_llm("not a message object")

    # Test with empty content message
    empty_message = Message(content="", type=MessageType.USER, status=MessageStatus.PENDING)
    response = await llm_agent.query_llm(empty_message)
    assert response.status == MessageStatus.ERROR

    # Test with invalid message type
    try:
        invalid_message = Message(
            content="Test content", type="INVALID_TYPE", status=MessageStatus.PENDING
        )
        await llm_agent.query_llm(invalid_message)
        pytest.fail("Should have raised ValidationError")
    except ValidationError:
        pass  # Expected behavior


@pytest.mark.asyncio
async def test_response_message_validation(llm_agent, test_message):
    """Test response message validation."""
    # Ensure the response is a valid Message object
    llm_agent.llm.generate.return_value = "Test response"
    response = await llm_agent.query_llm(test_message)

    # Validate the response is a Message object
    assert isinstance(response, Message)

    # Validate required fields
    assert response.content is not None
    assert response.type is not None
    assert response.status is not None
    assert response.request_id is not None

    # Validate field types
    assert isinstance(response.content, str)
    assert isinstance(response.type, MessageType)
    assert isinstance(response.status, MessageStatus)
    assert isinstance(response.metadata, dict)


@pytest.mark.asyncio
async def test_chat_return_value_validation(llm_agent):
    """Test validation of chat method return values."""
    # Setup
    expected_response = "Test response"
    llm_agent.query_llm = AsyncMock(return_value=expected_response)

    # Execute
    result = await llm_agent.chat("test input")

    # Validate return structure
    assert isinstance(result, dict)
    assert "response" in result
    assert "status" in result

    # Validate return types
    assert isinstance(result["response"], str)
    assert isinstance(result["status"], str)

    # Validate expected values
    assert result["status"] in ["success", "error"]
    if result["status"] == "success":
        assert result["response"] == expected_response


@pytest.mark.asyncio
async def test_query_llm_success(llm_agent, test_message):
    """Test successful LLM query with message format."""
    # Test case: Normal operation - should pass

    # Setup
    expected_response = "This is a test LLM response"
    llm_agent.llm.generate.return_value = expected_response

    # Execute
    response_message = await llm_agent.query_llm(test_message)

    # Verify
    assert response_message.content == expected_response
    assert response_message.type == MessageType.RESPONSE
    assert response_message.status == MessageStatus.SUCCESS
    assert response_message.parent_request_id == test_message.request_id
    llm_agent.llm.generate.assert_called_once_with(test_message.content)


@pytest.mark.asyncio
async def test_query_llm_failure(llm_agent, test_message):
    """Test LLM query with error handling."""
    # Test case: Error condition - should fail but handle gracefully

    # Setup
    error_message = "Test LLM service error"
    llm_agent.llm.generate.side_effect = Exception(error_message)

    # Execute
    response_message = await llm_agent.query_llm(test_message)

    # Verify
    assert error_message in response_message.content
    assert response_message.type == MessageType.ERROR
    assert response_message.status == MessageStatus.ERROR
    assert "error_details" in response_message.metadata
    assert response_message.metadata["error_details"]["error"] == error_message


@pytest.mark.asyncio
async def test_query_llm_no_service(llm_agent_config, test_message):
    """Test LLM query with no LLM service."""
    # Test case: Edge case - no LLM service configured

    # Setup
    config = llm_agent_config.copy()
    config.api_url = None
    agent = LLMAgent(config)

    # Execute
    response_message = await agent.query_llm(test_message)

    # Verify
    assert "LLM service not initialized" in response_message.content
    assert response_message.type == MessageType.ERROR
    assert response_message.status == MessageStatus.ERROR


@pytest.mark.asyncio
async def test_query_llm_override(llm_agent, test_message):
    """Test LLM query with override implementation."""
    # Test case: Edge case - custom override implementation

    # Setup
    override_response = Message(
        content="Override response",
        type=MessageType.RESPONSE,
        status=MessageStatus.SUCCESS,
    )
    llm_agent.query_llm_override = AsyncMock(return_value=override_response)

    # Execute
    response_message = await llm_agent.query_llm(test_message)

    # Verify
    assert response_message == override_response
    llm_agent.query_llm_override.assert_called_once_with(test_message)
    # Ensure generate was not called since override handled it
    llm_agent.llm.generate.assert_not_called()


@pytest.mark.asyncio
async def test_preprocessing(llm_agent, test_message):
    """Test prompt preprocessing."""
    # Test case: Normal operation with preprocessing - should pass

    # Setup
    expected_response = "Processed LLM response"
    llm_agent.llm.generate.return_value = expected_response

    # Create custom preprocessing that adds a prefix
    original_preprocess = llm_agent.preprocess_prompt

    async def custom_preprocess(message):
        message.content = f"PREPROCESSED: {message.content}"
        return message

    llm_agent.preprocess_prompt = custom_preprocess

    # Execute
    response_message = await llm_agent.query_llm(test_message)

    # Verify
    assert response_message.content == expected_response
    # Verify the LLM was called with the preprocessed content
    llm_agent.llm.generate.assert_called_once_with(f"PREPROCESSED: {test_message.content}")

    # Restore original preprocessing
    llm_agent.preprocess_prompt = original_preprocess


@pytest.mark.asyncio
async def test_postprocessing(llm_agent, test_message):
    """Test response postprocessing."""
    # Test case: Normal operation with postprocessing - should pass

    # Setup
    llm_response = "Original LLM response"
    llm_agent.llm.generate.return_value = llm_response

    # Create custom postprocessing that adds a suffix
    original_postprocess = llm_agent.postprocess_response

    async def custom_postprocess(message):
        message.content = f"{message.content} [POSTPROCESSED]"
        return message

    llm_agent.postprocess_response = custom_postprocess

    # Execute
    response_message = await llm_agent.query_llm(test_message)

    # Verify
    assert response_message.content == f"{llm_response} [POSTPROCESSED]"

    # Restore original postprocessing
    llm_agent.postprocess_response = original_postprocess


@pytest.mark.asyncio
async def test_chat_functionality(llm_agent):
    """Test chat implementation."""
    # Test case: Normal chat operation - should pass

    # Setup
    user_input = "Test user message"
    expected_response = "Test LLM chat response"

    # Mock the query_llm method to avoid complexity
    llm_agent.query_llm = AsyncMock(return_value=expected_response)

    # For this test, we'll add a mock graph_state
    llm_agent.graph_state = {"conversation_state": {"add_message": AsyncMock()}}

    # Execute
    result = await llm_agent.chat(user_input)

    # Verify
    assert result["status"] == "success"
    assert result["response"] == expected_response
    llm_agent.query_llm.assert_called_once_with(user_input)

    # Verify conversation history was updated
    assert len(llm_agent.conversation_history) == 1
    assert llm_agent.conversation_history[0]["user"] == user_input
    assert llm_agent.conversation_history[0]["assistant"] == expected_response

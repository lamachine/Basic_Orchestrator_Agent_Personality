"""Tests for base agent functionality."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from ..src.common.agents.base_agent import BaseAgent


def test_base_agent_initialization(base_agent):
    """Test basic agent initialization."""
    assert base_agent.name == "test_agent"
    assert base_agent.prompt_section == "Test prompt"
    assert base_agent.model == "test-model"
    assert base_agent.llm is not None


def test_base_agent_conversation_tracking(base_agent):
    """Test conversation tracking initialization."""
    assert base_agent.conversation_id is not None
    assert base_agent.session_id == base_agent.conversation_id
    assert base_agent.conversation_history == []


def test_base_agent_config_defaults(base_config):
    """Test agent configuration defaults."""
    agent = BaseAgent(name="test_defaults", config=base_config)
    assert agent.user_id == "developer"
    assert agent.conversation_history == []
    assert agent.llm is None


@pytest.mark.asyncio
async def test_query_llm_no_service(base_config):
    """Test LLM query with no service initialized."""
    agent = BaseAgent(name="test_no_llm", config=base_config)
    result = await agent.query_llm("test prompt")
    assert "Error: LLM service not initialized" in result


@pytest.mark.asyncio
async def test_query_llm_success(base_agent, mock_llm_response):
    """Test successful LLM query."""
    # Mock the LLM service
    base_agent.llm.generate = Mock(return_value=mock_llm_response)

    result = await base_agent.query_llm("test prompt")
    assert result == mock_llm_response
    base_agent.llm.generate.assert_called_once_with("test prompt")


@pytest.mark.asyncio
async def test_query_llm_error(base_agent):
    """Test LLM query with error."""
    # Mock LLM service to raise an exception
    base_agent.llm.generate = Mock(side_effect=Exception("Test error"))

    result = await base_agent.query_llm("test prompt")
    assert "Error: Test error" in result


def test_conversation_history_disabled(base_config):
    """Test agent with conversation history disabled."""
    config = base_config.copy()
    config.agent.enable_history = False

    agent = BaseAgent(name="test_no_history", config=config)
    assert agent.conversation_history is None


def test_tool_registry_initialization(base_agent):
    """Test tool registry initialization."""
    assert base_agent.tool_registry is not None
    # Add more specific tool registry tests based on your implementation

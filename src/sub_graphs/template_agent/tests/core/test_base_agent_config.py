"""
Tests for BaseAgentConfig.
"""

import pytest

from src.common.agents.base_agent import BaseAgentConfig


def test_base_agent_config_defaults():
    """Test BaseAgentConfig with default values."""
    config = BaseAgentConfig(name="test_agent")
    assert config.name == "test_agent"
    assert config.prompt_section == ""
    assert config.api_url is None
    assert config.model is None
    assert config.max_tokens == 2000
    assert config.context_window == 4096
    assert config.user_id == "developer"
    assert config.enable_history is True
    assert config.enable_logging is True
    assert config.graph_name == "unknown"


def test_base_agent_config_custom():
    """Test BaseAgentConfig with custom values."""
    config = BaseAgentConfig(
        name="test_agent",
        prompt_section="test_prompt",
        api_url="http://test.com",
        model="test_model",
        max_tokens=1000,
        context_window=2048,
        user_id="test_user",
        enable_history=False,
        enable_logging=False,
        graph_name="test_graph",
    )
    assert config.name == "test_agent"
    assert config.prompt_section == "test_prompt"
    assert config.api_url == "http://test.com"
    assert config.model == "test_model"
    assert config.max_tokens == 1000
    assert config.context_window == 2048
    assert config.user_id == "test_user"
    assert config.enable_history is False
    assert config.enable_logging is False
    assert config.graph_name == "test_graph"


def test_base_agent_config_validation():
    """Test BaseAgentConfig validation."""
    with pytest.raises(ValueError):
        BaseAgentConfig()  # name is required

    with pytest.raises(ValueError):
        BaseAgentConfig(name="")  # name cannot be empty


def test_base_agent_config_optional_fields():
    """Test BaseAgentConfig optional fields."""
    config = BaseAgentConfig(name="test_agent", api_url=None, model=None)
    assert config.api_url is None
    assert config.model is None

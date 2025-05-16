"""Test fixtures for template agent tests."""

import pytest
from typing import Dict, Any
from datetime import datetime

from ..src.common.config.base_config import BaseConfig, LLMConfig
from ..src.specialty.config.template_config import TemplateConfig
from ..src.common.agents.base_agent import BaseAgent
from ..src.specialty.agents.template_agent import TemplateAgent

@pytest.fixture
def base_config() -> BaseConfig:
    """Provide a basic configuration for testing."""
    return BaseConfig(
        llm={
            "test": LLMConfig(
                api_url="http://test.local",
                default_model="test-model"
            )
        }
    )

@pytest.fixture
def template_config() -> TemplateConfig:
    """Provide a template configuration for testing."""
    return TemplateConfig(
        llm={
            "test": LLMConfig(
                api_url="http://test.local",
                default_model="test-model"
            )
        },
        template_agent={
            "enable_tool_specialization": True,
            "specialized_tools": ["test_tool"]
        }
    )

@pytest.fixture
def mock_session_state() -> Dict[str, Any]:
    """Provide a mock session state for testing."""
    return {
        "conversation_state": {
            "messages": [],
            "add_message": lambda **kwargs: None  # Mock add_message function
        }
    }

@pytest.fixture
def mock_llm_response() -> str:
    """Provide a mock LLM response."""
    return "This is a test response from the LLM"

@pytest.fixture
def base_agent(base_config) -> BaseAgent:
    """Provide a configured base agent for testing."""
    return BaseAgent(
        name="test_agent",
        prompt_section="Test prompt",
        api_url="http://test.local",
        model="test-model",
        config=base_config
    )

@pytest.fixture
def template_agent(template_config) -> TemplateAgent:
    """Provide a configured template agent for testing."""
    return TemplateAgent(
        name="test_template",
        prompt_section="Test template prompt",
        api_url="http://test.local",
        model="test-model",
        config=template_config
    ) 
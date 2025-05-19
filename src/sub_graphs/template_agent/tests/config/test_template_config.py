"""Test suite for template configuration system."""

import os
from typing import Any, Dict

import pytest
import yaml

from ..src.specialty.config.template_config import (
    TemplateAgentConfig,
    TemplateConfig,
    TemplateDatabaseConfig,
    TemplateGraphConfig,
    TemplateLLMConfig,
    TemplateLoggingConfig,
    TemplatePersonalityConfig,
    TemplateToolConfig,
    load_template_config,
)

# Test data
VALID_CONFIG = {
    "template_agent": {
        "enable_tool_specialization": True,
        "specialized_tools": ["tool1", "tool2"],
        "custom_prompt_template": "You are a helpful assistant",
        "max_tokens": 4096,
        "context_window": 16384,
    },
    "template_tools": {
        "allowed_tools": ["tool1", "tool2"],
        "tool_descriptions": {"tool1": "First test tool", "tool2": "Second test tool"},
        "tool_timeout": 60,
        "max_retries": 5,
    },
    "template_llm": {
        "model_family": "gpt",
        "model_version": "4",
        "temperature": 0.8,
        "top_p": 0.95,
    },
    "template_logging": {
        "log_prefix": "test_",
        "log_rotation_size": "100MB",
        "log_level": "DEBUG",
        "log_to_file": True,
    },
    "template_database": {
        "custom_pool_settings": {"pool_recycle": 1800, "pool_pre_ping": True},
        "pool_size": 10,
        "max_overflow": 20,
    },
    "template_graph": {
        "custom_node_types": ["node1", "node2"],
        "custom_edge_types": ["edge1", "edge2"],
        "max_depth": 15,
        "max_breadth": 8,
    },
    "template_personality": {
        "custom_traits": ["friendly", "helpful"],
        "custom_goals": ["be helpful", "be clear"],
        "system_prompt": "You are a helpful template agent.",
    },
}

INVALID_CONFIG = {
    "template_agent": {
        "enable_tool_specialization": True,
        "specialized_tools": [],  # Invalid: empty list when enabled
        "max_tokens": -1,  # Invalid: negative value
        "context_window": 0,  # Invalid: zero value
    }
}

EDGE_CASE_CONFIG = {
    "template_agent": {
        "enable_tool_specialization": False,
        "specialized_tools": [],  # Valid when disabled
        "max_tokens": 1,  # Minimum valid value
        "context_window": 1,  # Minimum valid value
    },
    "template_tools": {
        "allowed_tools": ["tool1"],
        "tool_descriptions": {"tool1": ""},  # Empty description
        "tool_timeout": 1,  # Minimum valid value
        "max_retries": 0,  # Minimum valid value
    },
}


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file for testing."""

    def _create_config(config: Dict[str, Any]) -> str:
        file_path = tmp_path / "test_config.yaml"
        with open(file_path, "w") as f:
            yaml.dump(config, f)
        return str(file_path)

    return _create_config


class TestTemplateAgentConfig:
    """Test suite for TemplateAgentConfig."""

    def test_valid_config(self):
        """Test valid configuration."""
        config = TemplateAgentConfig(**VALID_CONFIG["template_agent"])
        assert config.enable_tool_specialization is True
        assert config.specialized_tools == ["tool1", "tool2"]
        assert config.max_tokens == 4096
        assert config.context_window == 16384

    def test_invalid_config(self):
        """Test invalid configuration."""
        with pytest.raises(ValueError):
            TemplateAgentConfig(**INVALID_CONFIG["template_agent"])

    def test_edge_case_config(self):
        """Test edge case configuration."""
        config = TemplateAgentConfig(**EDGE_CASE_CONFIG["template_agent"])
        assert config.enable_tool_specialization is False
        assert config.specialized_tools == []
        assert config.max_tokens == 1
        assert config.context_window == 1


class TestTemplateToolConfig:
    """Test suite for TemplateToolConfig."""

    def test_valid_config(self):
        """Test valid configuration."""
        config = TemplateToolConfig(**VALID_CONFIG["template_tools"])
        assert config.allowed_tools == ["tool1", "tool2"]
        assert config.tool_descriptions["tool1"] == "First test tool"
        assert config.tool_timeout == 60
        assert config.max_retries == 5

    def test_invalid_config(self):
        """Test invalid configuration."""
        invalid_tools = {
            "allowed_tools": ["tool1"],
            "tool_descriptions": {},  # Missing description
        }
        with pytest.raises(ValueError):
            TemplateToolConfig(**invalid_tools)

    def test_edge_case_config(self):
        """Test edge case configuration."""
        config = TemplateToolConfig(**EDGE_CASE_CONFIG["template_tools"])
        assert config.allowed_tools == ["tool1"]
        assert config.tool_descriptions["tool1"] == ""
        assert config.tool_timeout == 1
        assert config.max_retries == 0


class TestTemplateLLMConfig:
    """Test suite for TemplateLLMConfig."""

    def test_valid_config(self):
        """Test valid configuration."""
        config = TemplateLLMConfig(**VALID_CONFIG["template_llm"])
        assert config.model_family == "gpt"
        assert config.model_version == "4"
        assert config.temperature == 0.8
        assert config.top_p == 0.95

    def test_invalid_config(self):
        """Test invalid configuration."""
        invalid_llm = {
            "temperature": 2.1,  # Invalid: above maximum
            "top_p": 1.1,  # Invalid: above maximum
        }
        with pytest.raises(ValueError):
            TemplateLLMConfig(**invalid_llm)

    def test_edge_case_config(self):
        """Test edge case configuration."""
        edge_llm = {
            "model_family": "gpt",
            "model_version": "4",
            "temperature": 0.0,  # Minimum valid value
            "top_p": 0.0,  # Minimum valid value
        }
        config = TemplateLLMConfig(**edge_llm)
        assert config.temperature == 0.0
        assert config.top_p == 0.0


class TestTemplateLoggingConfig:
    """Test suite for TemplateLoggingConfig."""

    def test_valid_config(self):
        """Test valid configuration."""
        config = TemplateLoggingConfig(**VALID_CONFIG["template_logging"])
        assert config.log_prefix == "test_"
        assert config.log_rotation_size == "100MB"
        assert config.log_level == "DEBUG"
        assert config.log_to_file is True

    def test_invalid_config(self):
        """Test invalid configuration."""
        invalid_logging = {
            "log_rotation_size": "100",  # Invalid: missing unit
            "log_level": "INVALID",  # Invalid: not in enum
        }
        with pytest.raises(ValueError):
            TemplateLoggingConfig(**invalid_logging)

    def test_edge_case_config(self):
        """Test edge case configuration."""
        edge_logging = {
            "log_prefix": "",  # Empty prefix
            "log_rotation_size": "1KB",  # Minimum size
            "log_level": "CRITICAL",  # Most severe level
            "log_to_file": False,  # Disabled
        }
        config = TemplateLoggingConfig(**edge_logging)
        assert config.log_prefix == ""
        assert config.log_rotation_size == "1KB"
        assert config.log_level == "CRITICAL"
        assert config.log_to_file is False


class TestTemplateDatabaseConfig:
    """Test suite for TemplateDatabaseConfig."""

    def test_valid_config(self):
        """Test valid configuration."""
        config = TemplateDatabaseConfig(**VALID_CONFIG["template_database"])
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.custom_pool_settings["pool_recycle"] == 1800
        assert config.custom_pool_settings["pool_pre_ping"] is True

    def test_invalid_config(self):
        """Test invalid configuration."""
        invalid_db = {
            "pool_size": 0,  # Invalid: zero value
            "max_overflow": -1,  # Invalid: negative value
        }
        with pytest.raises(ValueError):
            TemplateDatabaseConfig(**invalid_db)

    def test_edge_case_config(self):
        """Test edge case configuration."""
        edge_db = {
            "pool_size": 1,  # Minimum valid value
            "max_overflow": 0,  # Minimum valid value
            "custom_pool_settings": {
                "pool_recycle": 1,  # Minimum valid value
                "pool_pre_ping": False,
            },
        }
        config = TemplateDatabaseConfig(**edge_db)
        assert config.pool_size == 1
        assert config.max_overflow == 0
        assert config.custom_pool_settings["pool_recycle"] == 1
        assert config.custom_pool_settings["pool_pre_ping"] is False


class TestTemplateGraphConfig:
    """Test suite for TemplateGraphConfig."""

    def test_valid_config(self):
        """Test valid configuration."""
        config = TemplateGraphConfig(**VALID_CONFIG["template_graph"])
        assert config.custom_node_types == ["node1", "node2"]
        assert config.custom_edge_types == ["edge1", "edge2"]
        assert config.max_depth == 15
        assert config.max_breadth == 8

    def test_invalid_config(self):
        """Test invalid configuration."""
        invalid_graph = {
            "max_depth": 0,  # Invalid: zero value
            "max_breadth": -1,  # Invalid: negative value
        }
        with pytest.raises(ValueError):
            TemplateGraphConfig(**invalid_graph)

    def test_edge_case_config(self):
        """Test edge case configuration."""
        edge_graph = {
            "custom_node_types": [],  # Empty list
            "custom_edge_types": [],  # Empty list
            "max_depth": 1,  # Minimum valid value
            "max_breadth": 1,  # Minimum valid value
        }
        config = TemplateGraphConfig(**edge_graph)
        assert config.custom_node_types == []
        assert config.custom_edge_types == []
        assert config.max_depth == 1
        assert config.max_breadth == 1


class TestTemplatePersonalityConfig:
    """Test suite for TemplatePersonalityConfig."""

    def test_valid_config(self):
        """Test valid configuration."""
        config = TemplatePersonalityConfig(**VALID_CONFIG["template_personality"])
        assert config.custom_traits == ["friendly", "helpful"]
        assert config.custom_goals == ["be helpful", "be clear"]
        assert config.system_prompt == "You are a helpful template agent."

    def test_invalid_config(self):
        """Test invalid configuration."""
        invalid_personality = {"system_prompt": ""}  # Invalid: empty prompt
        with pytest.raises(ValueError):
            TemplatePersonalityConfig(**invalid_personality)

    def test_edge_case_config(self):
        """Test edge case configuration."""
        edge_personality = {
            "custom_traits": [],  # Empty list
            "custom_goals": [],  # Empty list
            "system_prompt": "A",  # Minimum length
        }
        config = TemplatePersonalityConfig(**edge_personality)
        assert config.custom_traits == []
        assert config.custom_goals == []
        assert config.system_prompt == "A"


class TestTemplateConfig:
    """Test suite for TemplateConfig."""

    def test_valid_config(self):
        """Test valid configuration."""
        config = TemplateConfig(**VALID_CONFIG)
        assert isinstance(config.template_agent, TemplateAgentConfig)
        assert isinstance(config.template_tools, TemplateToolConfig)
        assert isinstance(config.template_llm["default"], TemplateLLMConfig)
        assert isinstance(config.template_logging, TemplateLoggingConfig)
        assert isinstance(config.template_database, TemplateDatabaseConfig)
        assert isinstance(config.template_graph, TemplateGraphConfig)
        assert isinstance(config.template_personality, TemplatePersonalityConfig)

    def test_invalid_config(self):
        """Test invalid configuration."""
        with pytest.raises(ValueError):
            TemplateConfig(**INVALID_CONFIG)

    def test_edge_case_config(self):
        """Test edge case configuration."""
        config = TemplateConfig(**EDGE_CASE_CONFIG)
        assert isinstance(config.template_agent, TemplateAgentConfig)
        assert isinstance(config.template_tools, TemplateToolConfig)


class TestLoadTemplateConfig:
    """Test suite for load_template_config function."""

    def test_valid_config_file(self, temp_config_file):
        """Test loading valid config file."""
        config_path = temp_config_file(VALID_CONFIG)
        config = load_template_config(config_path)
        assert isinstance(config, TemplateConfig)
        assert isinstance(config.template_agent, TemplateAgentConfig)

    def test_invalid_config_file(self, temp_config_file):
        """Test loading invalid config file."""
        config_path = temp_config_file(INVALID_CONFIG)
        with pytest.raises(ValueError):
            load_template_config(config_path)

    def test_missing_config_file(self):
        """Test loading non-existent config file."""
        with pytest.raises(FileNotFoundError):
            load_template_config("nonexistent.yaml")

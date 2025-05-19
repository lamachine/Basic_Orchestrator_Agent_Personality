"""Test suite for base configuration system."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import jsonschema
import pytest
import yaml
from pydantic import ValidationError

from ...src.common.config.base_config import (
    AgentConfig,
    BaseConfig,
    CommonSettings,
    DatabaseConfig,
    DatabaseProvidersConfig,
    GraphConfig,
    LLMConfig,
    LoggingConfig,
    ModelConfig,
    PersonalitiesConfig,
    PersonalityConfig,
    PostgresConfig,
    SupabaseConfig,
    ToolConfig,
    get_default_model,
    load_config,
)

# Test data
VALID_CONFIG = {
    "llm": {
        "default": {
            "api_url": "http://localhost:11434",
            "default_model": "llama3.1:latest",
            "timeout": 30,
            "settings": {
                "max_tokens": 4096,
                "context_window": 16384,
                "temperature": 0.1,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
            },
            "models": {
                "embedding": {
                    "model": "nomic-embed-text",
                    "settings": {"temperature": 0.0, "max_tokens": 512},
                }
            },
        }
    },
    "logging": {
        "enable_logging": True,
        "log_level": "INFO",
        "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "log_to_console": True,
        "log_to_file": True,
        "log_file": "app.log",
        "log_rotation": "1 day",
        "log_retention": "7 days",
        "file_level": "DEBUG",
        "console_level": "INFO",
        "log_dir": "./logs",
        "max_log_size_mb": 10,
        "backup_count": 5,
        "formatters": {
            "file": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
            "console": {"format": "%(levelname)s: %(message)s"},
        },
        "noisy_loggers": ["httpcore.http11", "httpx"],
    },
    "database": {
        "provider": "supabase_local",
        "providers": {
            "supabase_local": {
                "url": "http://localhost:54321",
                "anon_key": "test-anon-key",
                "service_role_key": "test-service-role-key",
            }
        },
        "pool_size": 5,
        "max_overflow": 10,
        "echo": False,
        "pool_timeout": 30,
        "pool_recycle": 3600,
    },
    "graph": {
        "name": "test_graph",
        "description": "Test graph configuration",
        "version": "1.0.0",
        "max_depth": 10,
        "max_breadth": 5,
        "timeout": 300,
        "retry_count": 3,
        "nodes": {"node1": {"type": "test"}},
        "edges": [{"from": "node1", "to": "node1", "type": "self-loop"}],
    },
    "agent": {
        "enable_history": True,
        "user_id": "test_user",
        "graph_name": "test_graph",
        "settings": {
            "max_tokens": 4096,
            "context_window": 16384,
            "temperature": 0.1,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        },
        "enable_logging": True,
        "prompt_section": "test",
    },
    "personalities": {
        "default_personality": "default",
        "personalities": {
            "default": {
                "name": "default",
                "description": "Default personality",
                "traits": ["helpful", "friendly"],
                "goals": ["assist user"],
                "constraints": ["be ethical"],
                "system_prompt": "You are a helpful assistant",
                "examples": [{"user": "Hello", "assistant": "Hi there!"}],
                "enabled": True,
                "file_path": None,
                "use_by_default": True,
            }
        },
    },
    "tools": {
        "tool_timeout": 30,
        "max_retries": 3,
        "inherit_from_parent": True,
        "allowed_tools": ["search"],
        "tool_descriptions": {"search": "Search the web for information"},
    },
}

INVALID_CONFIG = {
    "llm": {
        "default": {
            "api_url": "invalid-url",  # Invalid URL format
            "default_model": "",  # Empty model name
            "settings": {
                "max_tokens": -1,  # Negative tokens
                "context_window": 0,  # Zero context window
            },
        }
    },
    "logging": {
        "enable_logging": True,
        "log_level": "INVALID",  # Invalid log level
        "log_to_console": False,
        "log_to_file": True,
        "log_file": None,  # Missing log file when log_to_file is True
        "file_level": "DEBUG",
        "console_level": "INFO",
        "max_log_size_mb": 0,  # Invalid size
        "formatters": {},  # Empty formatters
        "noisy_loggers": [],
    },
    "database": {
        "provider": "nonexistent",  # Provider doesn't exist
        "providers": {},  # No providers configured
        "pool_size": 0,  # Invalid pool size
        "max_overflow": -1,  # Negative overflow
        "echo": False,
        "pool_timeout": 0,  # Invalid timeout
        "pool_recycle": 0,  # Invalid recycle
    },
    "graph": {
        "name": "",  # Empty name
        "description": "Test",
        "version": "invalid",  # Invalid version format
        "max_depth": 0,  # Invalid depth
        "max_breadth": 0,  # Invalid breadth
        "timeout": 0,  # Invalid timeout
        "retry_count": -1,  # Invalid retry count
        "nodes": {"node1": {"type": "test"}},
        "edges": [{"from": "node1", "to": "node2", "type": "invalid"}],  # node2 doesn't exist
    },
    "agent": {
        "enable_history": True,
        "user_id": "",  # Empty user ID
        "graph_name": "",  # Empty graph name
        "settings": {
            "max_tokens": -1,  # Invalid tokens
            "context_window": 0,  # Invalid context window
        },
        "enable_logging": True,
        "prompt_section": "test",
    },
    "personalities": {
        "default_personality": "nonexistent",  # Personality doesn't exist
        "personalities": {
            "default": {
                "name": "",  # Empty name
                "description": "Default",
                "traits": [],
                "goals": [],
                "constraints": [],
                "system_prompt": "",  # Empty prompt when enabled is True
                "examples": [],
                "enabled": True,
                "file_path": "/path/that/doesnt/exist",  # File doesn't exist
                "use_by_default": False,  # No personality is use_by_default
            }
        },
    },
    "tools": {
        "tool_timeout": 0,  # Invalid timeout
        "max_retries": -1,  # Invalid retries
        "inherit_from_parent": True,
        "allowed_tools": ["search"],
        "tool_descriptions": {},  # Missing descriptions for allowed tools
    },
}

EDGE_CASE_CONFIG = {
    "llm": {
        "default": {
            "api_url": "http://localhost:11434",
            "default_model": "a",  # Minimal model name
            "timeout": 1,  # Minimal timeout
            "settings": {
                "max_tokens": 1,  # Minimal tokens
                "context_window": 1,  # Minimal context window
                "temperature": 0.0,  # Minimal temperature
                "top_p": 0.0,  # Minimal top_p
                "frequency_penalty": -2.0,  # Min frequency penalty
                "presence_penalty": -2.0,  # Min presence penalty
            },
            "models": {},  # Empty models dict
        }
    },
    "logging": {
        "enable_logging": False,
        "log_level": "DEBUG",
        "log_format": "",  # Empty format
        "log_to_console": True,
        "log_to_file": False,  # No file logging
        "log_rotation": "1 second",  # Minimal rotation
        "log_retention": "1 second",  # Minimal retention
        "file_level": "DEBUG",
        "console_level": "DEBUG",
        "log_dir": ".",  # Current directory
        "max_log_size_mb": 1,  # Minimal size
        "backup_count": 0,  # No backups
        "formatters": {"console": {"format": ""}},  # Empty format
        "noisy_loggers": [],  # Empty loggers
    },
    "database": {
        "provider": "supabase_local",
        "providers": {
            "supabase_local": {
                "url": "http://localhost",
                "anon_key": "a",  # Minimal key
                "service_role_key": "a",  # Minimal key
            }
        },
        "pool_size": 1,  # Minimal pool size
        "max_overflow": 0,  # No overflow
        "echo": True,  # Enable echo
        "pool_timeout": 1,  # Minimal timeout
        "pool_recycle": 1,  # Minimal recycle
    },
    "graph": {
        "name": "a",  # Minimal name
        "description": "",  # Empty description
        "version": "0.0.0",  # Minimal version
        "max_depth": 1,  # Minimal depth
        "max_breadth": 1,  # Minimal breadth
        "timeout": 1,  # Minimal timeout
        "retry_count": 0,  # No retries
        "nodes": {"a": {}},
        "edges": [],  # No edges
    },
    "agent": {
        "enable_history": False,  # Disable history
        "user_id": "a",  # Minimal user ID
        "graph_name": "a",  # Minimal graph name
        "settings": {
            "max_tokens": 1,  # Minimal tokens
            "context_window": 1,  # Minimal context window
            "temperature": 0.0,  # Minimal temperature
            "top_p": 0.0,  # Minimal top_p
            "frequency_penalty": -2.0,  # Min frequency penalty
            "presence_penalty": -2.0,  # Min presence penalty
        },
        "enable_logging": False,  # Disable logging
        "prompt_section": "",  # Empty prompt section
    },
    "personalities": {
        "default_personality": "default",
        "personalities": {
            "default": {
                "name": "default",
                "description": "",  # Empty description
                "traits": [],  # Empty traits
                "goals": [],  # Empty goals
                "constraints": [],  # Empty constraints
                "system_prompt": "a",  # Minimal prompt
                "examples": [],  # Empty examples
                "enabled": False,  # Disabled
                "file_path": None,
                "use_by_default": True,
            }
        },
    },
    "tools": {
        "tool_timeout": 1,  # Minimal timeout
        "max_retries": 0,  # No retries
        "inherit_from_parent": False,  # Don't inherit
        "allowed_tools": [],  # No tools
        "tool_descriptions": {},  # Empty descriptions
    },
}


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""

    def _create_config(config_data: Dict[str, Any]) -> str:
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp:
            yaml.dump(config_data, temp)
            temp_path = temp.name
        return temp_path

    yield _create_config
    # Cleanup temp files after tests
    for file in Path(tempfile.gettempdir()).glob("*.yaml"):
        try:
            os.unlink(file)
        except:
            pass


class TestCommonSettings:
    """Test suite for CommonSettings."""

    def test_valid_settings(self):
        """Test valid settings creation."""
        settings = CommonSettings(
            max_tokens=1000,
            context_window=4000,
            temperature=0.7,
            top_p=0.9,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        )
        assert settings.max_tokens == 1000
        assert settings.context_window == 4000
        assert settings.temperature == 0.7
        assert settings.top_p == 0.9
        assert settings.frequency_penalty == 0.0
        assert settings.presence_penalty == 0.0

    def test_invalid_settings(self):
        """Test invalid settings raise validation errors."""
        # Test negative max_tokens
        with pytest.raises(ValidationError):
            CommonSettings(max_tokens=-1, context_window=4000, temperature=0.7, top_p=0.9)

        # Test temperature out of range
        with pytest.raises(ValidationError):
            CommonSettings(
                max_tokens=1000,
                context_window=4000,
                temperature=2.1,  # > 2.0
                top_p=0.9,
            )

        # Test top_p out of range
        with pytest.raises(ValidationError):
            CommonSettings(
                max_tokens=1000,
                context_window=4000,
                temperature=0.7,
                top_p=1.1,  # > 1.0
            )

    def test_max_tokens_validator(self):
        """Test that max_tokens cannot exceed context_window."""
        # Valid case
        valid = CommonSettings(max_tokens=1000, context_window=4000, temperature=0.7, top_p=0.9)
        assert valid.max_tokens == 1000

        # Invalid case - max_tokens > context_window
        with pytest.raises(ValueError):
            CommonSettings(max_tokens=5000, context_window=4000, temperature=0.7, top_p=0.9)

    def test_edge_case_settings(self):
        """Test edge case settings."""
        # Minimum valid values
        settings = CommonSettings(
            max_tokens=1,
            context_window=1,
            temperature=0.0,
            top_p=0.0,
            frequency_penalty=-2.0,
            presence_penalty=-2.0,
        )
        assert settings.max_tokens == 1
        assert settings.context_window == 1
        assert settings.temperature == 0.0
        assert settings.top_p == 0.0
        assert settings.frequency_penalty == -2.0
        assert settings.presence_penalty == -2.0

        # Maximum valid values
        settings = CommonSettings(
            max_tokens=100,
            context_window=100,
            temperature=2.0,
            top_p=1.0,
            frequency_penalty=2.0,
            presence_penalty=2.0,
        )
        assert settings.temperature == 2.0
        assert settings.top_p == 1.0
        assert settings.frequency_penalty == 2.0
        assert settings.presence_penalty == 2.0


class TestModelConfig:
    """Test suite for ModelConfig."""

    def test_valid_model_config(self):
        """Test valid model configuration."""
        config = ModelConfig(
            model="test-model",
            system_prompt="You are a helpful assistant",
            dimensions=768,
            normalize=True,
        )
        assert config.model == "test-model"
        assert config.system_prompt == "You are a helpful assistant"
        assert config.dimensions == 768
        assert config.normalize is True

    def test_minimal_model_config(self):
        """Test minimal model configuration."""
        config = ModelConfig(model="test-model")
        assert config.model == "test-model"
        assert config.system_prompt == ""
        assert config.dimensions is None
        assert config.normalize is None

    def test_settings_inheritance(self):
        """Test settings inheritance in model config."""
        settings = CommonSettings(
            max_tokens=1000,
            context_window=4000,
            temperature=0.7,
            top_p=0.9,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        )
        config = ModelConfig(model="test-model", settings=settings)
        assert config.settings.max_tokens == 1000
        assert config.settings.temperature == 0.7


class TestLLMConfig:
    """Test suite for LLMConfig."""

    def test_valid_llm_config(self):
        """Test valid LLM configuration."""
        config = LLMConfig(api_url="http://localhost:11434", default_model="test-model", timeout=30)
        assert config.api_url == "http://localhost:11434"
        assert config.default_model == "test-model"
        assert config.timeout == 30

    def test_models_dict(self):
        """Test models dictionary in LLM config."""
        models = {"test": ModelConfig(model="test-model", system_prompt="Test prompt")}
        config = LLMConfig(
            api_url="http://localhost:11434", default_model="test-model", models=models
        )
        assert "test" in config.models
        assert config.models["test"].model == "test-model"
        assert config.models["test"].system_prompt == "Test prompt"


class TestLoggingConfig:
    """Test suite for LoggingConfig."""

    def test_valid_logging_config(self):
        """Test valid logging configuration."""
        config = LoggingConfig(
            enable_logging=True,
            log_level="INFO",
            log_format="%(asctime)s - %(levelname)s - %(message)s",
            log_to_console=True,
            log_to_file=True,
            log_file="app.log",
            log_rotation="1 day",
            log_retention="7 days",
            file_level="DEBUG",
            console_level="INFO",
            log_dir="./logs",
            max_log_size_mb=10,
            backup_count=5,
            formatters={"console": {"format": "%(levelname)s: %(message)s"}},
            noisy_loggers=["httpx"],
        )
        assert config.enable_logging is True
        assert config.log_level == "INFO"
        assert config.log_to_console is True
        assert config.log_to_file is True
        assert config.log_file == "app.log"

    def test_invalid_logging_config(self):
        """Test invalid logging configuration raises validation errors."""
        # Test missing log_file when log_to_file is True
        with pytest.raises(ValueError):
            LoggingConfig(
                enable_logging=True,
                log_level="INFO",
                log_format="%(asctime)s - %(levelname)s - %(message)s",
                log_to_console=False,
                log_to_file=True,
                log_file=None,
                log_rotation="1 day",
                log_retention="7 days",
                file_level="DEBUG",
                console_level="INFO",
                log_dir="./logs",
                max_log_size_mb=10,
                backup_count=5,
                formatters={"console": {"format": "%(levelname)s: %(message)s"}},
                noisy_loggers=["httpx"],
            )

        # Test neither log_to_console nor log_to_file is True
        with pytest.raises(ValueError):
            LoggingConfig(
                enable_logging=True,
                log_level="INFO",
                log_format="%(asctime)s - %(levelname)s - %(message)s",
                log_to_console=False,
                log_to_file=False,
                log_rotation="1 day",
                log_retention="7 days",
                file_level="DEBUG",
                console_level="INFO",
                log_dir="./logs",
                max_log_size_mb=10,
                backup_count=5,
                formatters={"console": {"format": "%(levelname)s: %(message)s"}},
                noisy_loggers=["httpx"],
            )

        # Test invalid log level
        with pytest.raises(ValidationError):
            LoggingConfig(
                enable_logging=True,
                log_level="INVALID",
                log_format="%(asctime)s - %(levelname)s - %(message)s",
                log_to_console=True,
                log_to_file=False,
                log_rotation="1 day",
                log_retention="7 days",
                file_level="DEBUG",
                console_level="INFO",
                log_dir="./logs",
                max_log_size_mb=10,
                backup_count=5,
                formatters={"console": {"format": "%(levelname)s: %(message)s"}},
                noisy_loggers=["httpx"],
            )


class TestDatabaseConfig:
    """Test suite for DatabaseConfig."""

    def test_valid_database_config(self):
        """Test valid database configuration."""
        providers = DatabaseProvidersConfig(
            supabase_local=SupabaseConfig(
                url="http://localhost:54321",
                anon_key="test-key",
                service_role_key="test-role-key",
            )
        )
        config = DatabaseConfig(
            provider="supabase_local",
            providers=providers,
            pool_size=5,
            max_overflow=10,
            echo=False,
            pool_timeout=30,
            pool_recycle=3600,
        )
        assert config.provider == "supabase_local"
        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.echo is False
        assert config.pool_timeout == 30
        assert config.pool_recycle == 3600

    def test_provider_validation(self):
        """Test provider validation in database config."""
        # Test non-existent provider
        providers = DatabaseProvidersConfig(
            supabase_local=SupabaseConfig(
                url="http://localhost:54321",
                anon_key="test-key",
                service_role_key="test-role-key",
            )
        )
        with pytest.raises(ValueError):
            DatabaseConfig(
                provider="nonexistent",
                providers=providers,
                pool_size=5,
                max_overflow=10,
                echo=False,
                pool_timeout=30,
                pool_recycle=3600,
            )

        # Test empty providers
        with pytest.raises(ValueError):
            DatabaseProvidersConfig()


class TestGraphConfig:
    """Test suite for GraphConfig."""

    def test_valid_graph_config(self):
        """Test valid graph configuration."""
        config = GraphConfig(
            name="test-graph",
            description="Test graph",
            version="1.0.0",
            max_depth=10,
            max_breadth=5,
            timeout=300,
            retry_count=3,
            nodes={"node1": {"type": "test"}},
            edges=[{"from": "node1", "to": "node1", "type": "self-loop"}],
        )
        assert config.name == "test-graph"
        assert config.description == "Test graph"
        assert config.version == "1.0.0"
        assert config.max_depth == 10
        assert config.max_breadth == 5
        assert config.timeout == 300
        assert config.retry_count == 3
        assert "node1" in config.nodes
        assert len(config.edges) == 1

    def test_edge_validation(self):
        """Test edge validation in graph config."""
        # Test edge with non-existent from node
        with pytest.raises(ValueError):
            GraphConfig(
                name="test-graph",
                description="Test graph",
                version="1.0.0",
                max_depth=10,
                max_breadth=5,
                timeout=300,
                retry_count=3,
                nodes={"node1": {"type": "test"}},
                edges=[{"from": "nonexistent", "to": "node1", "type": "test-edge"}],
            )

        # Test edge with non-existent to node
        with pytest.raises(ValueError):
            GraphConfig(
                name="test-graph",
                description="Test graph",
                version="1.0.0",
                max_depth=10,
                max_breadth=5,
                timeout=300,
                retry_count=3,
                nodes={"node1": {"type": "test"}},
                edges=[{"from": "node1", "to": "nonexistent", "type": "test-edge"}],
            )


class TestPersonalitiesConfig:
    """Test suite for PersonalitiesConfig."""

    def test_valid_personalities_config(self):
        """Test valid personalities configuration."""
        personalities = {
            "default": PersonalityConfig(
                name="default",
                description="Default personality",
                traits=["helpful", "friendly"],
                goals=["assist user"],
                constraints=["be ethical"],
                system_prompt="You are a helpful assistant",
                examples=[{"user": "Hello", "assistant": "Hi there!"}],
                enabled=True,
                file_path=None,
                use_by_default=True,
            )
        }
        config = PersonalitiesConfig(default_personality="default", personalities=personalities)
        assert config.default_personality == "default"
        assert "default" in config.personalities
        assert config.personalities["default"].name == "default"
        assert "helpful" in config.personalities["default"].traits

    def test_personalities_validation(self):
        """Test personalities validation."""
        # Test no personalities
        with pytest.raises(ValueError):
            PersonalitiesConfig(default_personality="default", personalities={})

        # Test non-existent default personality
        personalities = {
            "test": PersonalityConfig(
                name="test",
                description="Test personality",
                traits=[],
                goals=[],
                constraints=[],
                system_prompt="You are a test assistant",
                examples=[],
                enabled=True,
                file_path=None,
                use_by_default=True,
            )
        }
        with pytest.raises(ValueError):
            PersonalitiesConfig(default_personality="nonexistent", personalities=personalities)

        # Test no personality with use_by_default=True
        personalities = {
            "test": PersonalityConfig(
                name="test",
                description="Test personality",
                traits=[],
                goals=[],
                constraints=[],
                system_prompt="You are a test assistant",
                examples=[],
                enabled=True,
                file_path=None,
                use_by_default=False,
            )
        }
        with pytest.raises(ValueError):
            PersonalitiesConfig(default_personality="test", personalities=personalities)


class TestToolConfig:
    """Test suite for ToolConfig."""

    def test_valid_tool_config(self):
        """Test valid tool configuration."""
        config = ToolConfig(
            tool_timeout=30,
            max_retries=3,
            inherit_from_parent=True,
            allowed_tools=["search", "weather"],
            tool_descriptions={
                "search": "Search for information",
                "weather": "Get weather information",
            },
        )
        assert config.tool_timeout == 30
        assert config.max_retries == 3
        assert config.inherit_from_parent is True
        assert "search" in config.allowed_tools
        assert "weather" in config.allowed_tools
        assert config.tool_descriptions["search"] == "Search for information"

    def test_tool_descriptions_validation(self):
        """Test tool descriptions validation."""
        # Test missing tool description
        with pytest.raises(ValueError):
            ToolConfig(
                tool_timeout=30,
                max_retries=3,
                inherit_from_parent=True,
                allowed_tools=["search", "weather"],
                tool_descriptions={
                    "search": "Search for information"
                    # Missing weather description
                },
            )


class TestBaseConfig:
    """Test suite for BaseConfig."""

    def test_valid_base_config(self):
        """Test valid base configuration."""
        # Create a base config from the valid test data
        config = BaseConfig(**VALID_CONFIG)
        assert "default" in config.llm
        assert config.logging.enable_logging is True
        assert config.database.provider == "supabase_local"
        assert config.graph.name == "test_graph"
        assert config.agent.user_id == "test_user"
        assert config.personalities.default_personality == "default"
        assert config.tools.tool_timeout == 30

    def test_invalid_base_config(self):
        """Test invalid base configuration raises validation errors."""
        with pytest.raises(Exception):
            BaseConfig(**INVALID_CONFIG)

    def test_edge_case_base_config(self):
        """Test edge case base configuration."""
        # Create a base config from the edge case test data
        config = BaseConfig(**EDGE_CASE_CONFIG)
        assert "default" in config.llm
        assert config.logging.enable_logging is False
        assert config.database.provider == "supabase_local"
        assert config.graph.name == "a"
        assert config.agent.user_id == "a"


class TestLoadConfig:
    """Test suite for load_config function."""

    def test_valid_config_loading(self, temp_config_file):
        """Test loading a valid configuration file."""
        config_path = temp_config_file(VALID_CONFIG)
        config = load_config(config_path)
        assert isinstance(config, BaseConfig)
        assert "default" in config.llm
        assert config.logging.enable_logging is True
        assert config.database.provider == "supabase_local"

    def test_invalid_config_loading(self, temp_config_file):
        """Test loading an invalid configuration file raises errors."""
        config_path = temp_config_file(INVALID_CONFIG)
        with pytest.raises(Exception):
            load_config(config_path)

    def test_nonexistent_config_file(self):
        """Test loading a non-existent configuration file raises an error."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.yaml")

    def test_malformed_yaml(self, temp_config_file):
        """Test loading malformed YAML raises an error."""
        # Create a file with invalid YAML
        with open(temp_config_file({}), "w") as f:
            f.write('this is not valid yaml:\n  - missing colon\n  unclosed quote"')

        with pytest.raises(yaml.YAMLError):
            load_config(temp_config_file({}))


class TestGetDefaultModel:
    """Test suite for get_default_model function."""

    def test_valid_provider_and_purpose(self):
        """Test getting default model with valid provider and purpose."""
        model = get_default_model("ollama", "embedding")
        assert model == "nomic-embed-text"

        model = get_default_model("openai", "chat")
        assert model == "gpt-4"

    def test_invalid_provider(self):
        """Test getting default model with invalid provider."""
        model = get_default_model("nonexistent", "chat")
        assert model == ""  # Should return empty string for invalid provider

    def test_invalid_purpose(self):
        """Test getting default model with invalid purpose."""
        model = get_default_model("ollama", "nonexistent")
        assert model == ""  # Should return empty string for invalid purpose

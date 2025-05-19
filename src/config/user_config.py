"""
User-editable configuration for the application.

# CONFIG STRUCTURE NOTE:
# - Logging config: src/config/logging_config.py
# - LLM config: src/config/llm_config.py
# - Database config: src/config/database_config.py
# - Orchestrator/agent config: src/config/orchestrator_config.py
# - Personality config: src/config/personality_config.py
# - Only user/general config should be here.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field, model_validator

from src.config.llm_config import LLMProvidersConfig, OllamaConfig, OpenAIConfig
from src.config.personality_config import PersonalityConfig, get_personality_config

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATHS = [
    "src/config/developer_user_config.yaml",
]

# Only user/general config keys (with duplicates, preferred name first)
DEFAULT_CONFIG = {
    "general": {
        "user_id": "developer",
        "debug_mode": False,
        "session_timeout_minutes": 30,
        "location": "San Jose, CA",
        "timezone": "America/Los_Angeles",
    },
    "llm": {
        "default_provider": "ollama",
        "providers": {
            "ollama": {
                "enabled": True,
                "api_url": "http://localhost:11434",
                "default_model": "llama3.1:latest",
                "temperature": 0.7,
                "max_tokens": 2048,
                "context_window": 8192,
                "models": {},
            },
            "openai": {
                "enabled": False,
                "api_url": "https://api.openai.com/v1",
                "default_model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 4096,
                "models": {},
            },
            "anthropic": {"enabled": False},
            "grok": {"enabled": False},
            "huggingface": {"enabled": False},
            "google": {"enabled": False},
        },
    },
    "database": {
        "provider": "supabase_local",
        "providers": {
            "supabase_local": {
                "url": "http://localhost:54321",
                "anon_key": "local-anon-key",
                "service_role_key": "local-service-role-key",
            }
        },
    },
    "logging": {
        "file_level": "DEBUG",
        "console_level": "INFO",
        "log_dir": "./logs",
        "max_log_size_mb": 10,
        "backup_count": 5,
    },
    "personality": {
        "default_personality": "valet",
        "personalities": {
            "valet": {
                "enabled": True,
                "file_path": "src/agents/Character_Ronan_valet_orchestrator.json",
                "use_by_default": True,
            }
        },
    },
    "ui": {
        "provider": "local",
        "options": {
            "theme": "dark",
            "enable_voice": False,
            "enable_web": True,
            "enable_cli": True,
        },
    },
}


class UserConfig:
    """User configuration loaded from YAML file with defaults."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = UserConfig()
        return cls._instance

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = self._find_config_file(config_path)
        self.config = self._load_config()
        self.logger = logging.getLogger(__name__)

    def _find_config_file(self, config_path: Optional[str] = None) -> Optional[str]:
        if config_path and os.path.isfile(config_path):
            return config_path
        for path in DEFAULT_CONFIG_PATHS:
            expanded_path = os.path.expanduser(path)
            if os.path.isfile(expanded_path):
                return expanded_path
        return None

    def _deep_merge_dicts(self, base: dict, updates: dict) -> dict:
        """Recursively merge updates into base dict."""
        for k, v in updates.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                base[k] = self._deep_merge_dicts(base[k], v)
            else:
                base[k] = v
        return base

    def _load_config(self) -> Dict[str, Any]:
        config = DEFAULT_CONFIG.copy()
        if self.config_path:
            try:
                with open(self.config_path, "r") as f:
                    user_config = yaml.safe_load(f) or {}
                if user_config:
                    config = self._deep_merge_dicts(config, user_config)
                logger.debug(
                    f"user_config:_load_config: Loaded configuration from {self.config_path}"
                )
            except Exception as e:
                logger.debug(
                    f"user_config:_load_config: Error loading configuration from {self.config_path}: {e}"
                )
                logger.debug("user_config:_load_config: Using default configuration")
        else:
            logger.debug("user_config:_load_config: No configuration file found, using defaults")
            self._create_default_config()
        return config

    def _create_default_config(self):
        try:
            default_path = os.path.expanduser(DEFAULT_CONFIG_PATHS[0])
            os.makedirs(os.path.dirname(default_path), exist_ok=True)
            with open(default_path, "w") as f:
                f.write(
                    """# User Configuration for Basic Orchestrator Agent Personality
#
# This file contains user-editable settings for the application.
# Edit the values below to customize the behavior of the system.
#
# Note: Do not remove any sections, only modify values.
#       Use # to add comments or disable settings.
#
# For more information, see the project documentation.
#
"""
                )
                yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, sort_keys=False)
            logger.debug(f"Created default configuration file at {default_path}")
            self.config_path = default_path
        except Exception as e:
            logger.debug(f"Error creating default configuration file: {e}")

    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        if section not in self.config:
            return default
        if key is None:
            return self.config[section]
        return self.config[section].get(key, default)

    def set(self, section: str, key: str, value: Any) -> bool:
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        if self.config_path:
            try:
                with open(self.config_path, "w") as f:
                    yaml.dump(self.config, f, default_flow_style=False)
                return True
            except Exception as e:
                logger.debug(f"Error saving configuration: {e}")
                return False
        return False

    def get_llm_config(self) -> dict:
        return self.config.get("llm", DEFAULT_CONFIG["llm"])

    def get_database_config(self) -> dict:
        return self.config.get("database", DEFAULT_CONFIG["database"])

    def get_logging_config(self) -> dict:
        return self.config.get("logging", DEFAULT_CONFIG["logging"])

    def get_personality_config(self) -> dict:
        """
        Get personality configuration.

        Returns:
            Dictionary with personality configuration
        """
        personality_config = self.config.get("personality", DEFAULT_CONFIG["personality"])

        # If the personalities section contains a list instead of a dict, convert it
        if "personalities" in personality_config and isinstance(
            personality_config["personalities"], list
        ):
            # Convert from list format to dict format
            converted = {}
            for item in personality_config["personalities"]:
                if "name" in item and isinstance(item["name"], str):
                    name = item.pop("name")  # Remove name key and get its value
                    converted[name] = item

            # Replace the list with the dict
            personality_config["personalities"] = converted

            # Log the conversion
            self.logger.debug(
                f"Converted personalities from list to dict format: {converted.keys()}"
            )

        return personality_config

    def get_ui_config(self) -> dict:
        return self.config.get("ui", DEFAULT_CONFIG["ui"])

    def to_dict(self) -> Dict[str, Any]:
        return self.config.copy()

    def __repr__(self) -> str:
        safe_config = self.to_dict()
        return f"UserConfig(path={self.config_path}, config={safe_config})"

    def get_timezone(self) -> str:
        return self.config.get("general", {}).get("timezone", "UTC")

    def get_location(self) -> str:
        return self.config.get("general", {}).get("location", "Unknown")


def get_user_config() -> UserConfig:
    return UserConfig.get_instance()

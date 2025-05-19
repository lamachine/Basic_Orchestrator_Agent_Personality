"""
Configuration Package

This package provides configuration management for the template agent.
It includes configuration for:
1. Core services (LLM, DB, State)
2. Tools and utilities
3. Logging and monitoring
4. User settings
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .base_config import BaseConfig, SessionConfig
from .database_config import DBServiceConfig
from .llm_config import LLMConfig
from .logging_config import LoggingServiceConfig
from .service_config import ServiceConfig
from .state_config import StateServiceConfig
from .tool_config import CodeToolConfig, EmbeddingToolConfig, SearchToolConfig, ToolConfig


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Optional path to config file. If not provided, uses default location.

    Returns:
        Dict containing configuration values
    """
    if not config_path:
        # Use default config path
        config_path = os.path.join(os.path.dirname(__file__), "base_config.yaml")

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        raise RuntimeError(f"Failed to load config from {config_path}: {str(e)}")


__all__ = [
    # Base configs
    "BaseConfig",
    "ServiceConfig",
    "SessionConfig",
    # Service configs
    "LLMConfig",
    "DBServiceConfig",
    "LoggingServiceConfig",
    "StateServiceConfig",
    # Tool configs
    "ToolConfig",
    "EmbeddingToolConfig",
    "SearchToolConfig",
    "CodeToolConfig",
    # Functions
    "load_config",
]

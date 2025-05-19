"""
Configuration Manager Module

This module implements the manager layer for configuration operations.
It handles loading, validating, and accessing configuration across the application.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..config.base_config import (
    AgentConfig,
    BaseConfig,
    DatabaseConfig,
    GraphConfig,
    LoggingConfig,
    PersonalitiesConfig,
    ToolConfig,
    load_config,
)
from .base_manager import BaseManager, ManagerState


class ConfigState(ManagerState):
    """State model for configuration management."""

    last_loaded: Optional[datetime] = None
    config_path: Optional[str] = None
    config_hash: Optional[str] = None
    load_errors: List[str] = Field(default_factory=list)


class ConfigManager(BaseManager):
    """Manager for configuration operations and state."""

    def __init__(self, config: Optional[BaseConfig] = None, config_path: Optional[str] = None):
        """
        Args:
            config: Optional BaseConfig instance
            config_path: Optional path to configuration file
        """
        if config is None and config_path is not None:
            config = load_config(config_path)
        elif config is None:
            config = BaseConfig(**{})  # or raise an error if config is required
        super().__init__(config)
        self._config_path = config_path
        self._config = config
        self._state = ConfigState()

    async def initialize(self) -> None:
        """Initialize the configuration manager."""
        await super().initialize()
        if self._config_path:
            await self.load_config(self._config_path)
        else:
            await self._find_and_load_config()

    async def _find_and_load_config(self) -> None:
        """Find and load configuration from standard locations."""
        possible_paths = [
            "base_config.yaml",
            "config/base_config.yaml",
            "../config/base_config.yaml",
            "src/common/config/base_config.yaml",
            "../src/common/config/base_config.yaml",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                await self.load_config(path)
                return

        raise FileNotFoundError("Could not find base_config.yaml in standard locations")

    async def load_config(self, config_path: str) -> BaseConfig:
        """Load configuration from file.

        Args:
            config_path: Path to configuration file

        Returns:
            Loaded configuration

        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config is invalid
        """
        try:
            self._config = load_config(config_path)
            self._config_path = config_path
            self._state.last_loaded = datetime.now()
            self._state.config_path = config_path
            # TODO: Add config hash calculation
            return self._config

        except Exception as e:
            self._state.load_errors.append(str(e))
            raise

    async def reload_config(self) -> BaseConfig:
        """Reload configuration from file.

        Returns:
            Reloaded configuration

        Raises:
            ValueError: If no config file has been loaded
        """
        if not self._config_path:
            raise ValueError("No configuration file has been loaded yet")
        return await self.load_config(self._config_path)

    def get_config(self) -> BaseConfig:
        """Get the current configuration.

        Returns:
            Current configuration

        Raises:
            ValueError: If no config has been loaded
        """
        if not self._config:
            raise ValueError("No configuration has been loaded")
        return self._config

    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration.

        Returns:
            LLM configuration dictionary
        """
        return self.get_config().llm

    def get_model_config(self, provider: str, model_type: str) -> Dict[str, Any]:
        """Get specific model configuration.

        Args:
            provider: Provider name
            model_type: Model type

        Returns:
            Model configuration dictionary
        """
        llm_config = self.get_llm_config()
        return llm_config.get("models", {}).get(model_type, {})

    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration.

        Returns:
            Logging configuration
        """
        return self.get_config().logging

    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration.

        Returns:
            Database configuration
        """
        return self.get_config().database

    def get_graph_config(self) -> GraphConfig:
        """Get graph configuration.

        Returns:
            Graph configuration
        """
        return self.get_config().graph

    def get_agent_config(self) -> AgentConfig:
        """Get agent configuration.

        Returns:
            Agent configuration
        """
        return self.get_config().agent

    def get_tools_config(self) -> ToolConfig:
        """Get tools configuration.

        Returns:
            Tools configuration
        """
        return self.get_config().tools

    def get_personalities_config(self) -> PersonalitiesConfig:
        """Get personalities configuration.

        Returns:
            Personalities configuration
        """
        return self.get_config().personalities

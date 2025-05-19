"""
Service Configuration Module

This module defines the base configuration for all services.
It provides common configuration fields and methods that are
inherited by specific service configurations.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ServiceConfig(BaseModel):
    """Base configuration for all services."""

    service_name: str = Field(..., description="Name of the service")
    enabled: bool = Field(default=True, description="Whether the service is enabled")
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Service-specific configuration"
    )

    def get_merged_config(self) -> Dict[str, Any]:
        """Get merged configuration including defaults."""
        return self.config


class DBServiceConfig(ServiceConfig):
    """Configuration for database service."""

    provider: str = Field(..., description="Database provider (e.g., postgresql, supabase)")
    connection_params: Dict[str, Any] = Field(..., description="Database connection parameters")


class LoggingServiceConfig(ServiceConfig):
    """Configuration for logging service."""

    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(None, description="Path to log file")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )


class StateServiceConfig(ServiceConfig):
    """Configuration for state service."""

    max_state_history: int = Field(
        default=100, description="Maximum number of states to keep in history"
    )
    persistence_enabled: bool = Field(default=True, description="Whether to persist state")
    cleanup_interval: int = Field(default=3600, description="State cleanup interval in seconds")


class LLMConfig(ServiceConfig):
    """Configuration for LLM service."""

    model_name: str = Field(..., description="Name of the LLM model to use")
    model_type: str = Field(default="ollama", description="Type of LLM (e.g., ollama, openai)")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Sampling temperature")
    max_tokens: int = Field(default=2000, gt=0, description="Maximum tokens to generate")
    stop_sequences: List[str] = Field(default_factory=list, description="Stop sequences")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Top-p sampling parameter")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")
    cache_enabled: bool = Field(default=True, description="Whether to cache responses")
    streaming_enabled: bool = Field(default=False, description="Whether to enable streaming")
    api_url: Optional[str] = Field(None, description="API URL for the LLM service")
    api_key: Optional[str] = Field(None, description="API key for the LLM service")

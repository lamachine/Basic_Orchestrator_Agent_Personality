"""
Service configuration models for the template agent.

This module provides models for service configuration and capabilities.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ServiceCapability(BaseModel):
    """Model for service capabilities."""

    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    required: bool = False
    enabled: bool = True


class ServiceConfig(BaseModel):
    """Base configuration for all services."""

    name: str = Field(..., description="Name of the service")
    enabled: bool = Field(default=True, description="Whether the service is enabled")
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Service-specific configuration"
    )

    @model_validator(mode="after")
    def validate_config(self) -> "ServiceConfig":
        """Validate service configuration."""
        if not self.name:
            raise ValueError("Service name cannot be empty")
        return self


class LLMConfig(BaseModel):
    """Configuration for LLM service."""

    model_name: str = Field(..., description="Name of the LLM model to use")
    temperature: float = Field(default=0.7, description="Sampling temperature")
    max_tokens: int = Field(default=2000, description="Maximum tokens to generate")
    top_p: float = Field(default=1.0, description="Top-p sampling parameter")
    frequency_penalty: float = Field(default=0.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, description="Presence penalty")
    stop: Optional[List[str]] = Field(default=None, description="Stop sequences")

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature value."""
        if not 0 <= v <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        """Validate max tokens value."""
        if v < 1:
            raise ValueError("Max tokens must be at least 1")
        return v


class PoolConfig(BaseModel):
    """Configuration for connection pool."""

    pool_size: int = Field(default=5, description="Maximum number of connections")
    timeout: float = Field(default=30.0, description="Connection timeout in seconds")
    retry_count: int = Field(default=3, description="Number of retry attempts")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")


class LLMServiceConfig(ServiceConfig):
    """Configuration specific to LLM services."""

    model_name: str
    temperature: float = 0.7
    max_tokens: int = 2000
    stop_sequences: List[str] = Field(default_factory=list)

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v):
        """Validate temperature value."""
        if not 0 <= v <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v):
        """Validate max tokens value."""
        if v < 1:
            raise ValueError("Max tokens must be at least 1")
        return v


class DBServiceConfig(ServiceConfig):
    """Configuration specific to database services."""

    connection_string: str
    pool_size: int = 5
    timeout: int = 30
    retry_count: int = 3

    @field_validator("pool_size")
    @classmethod
    def validate_pool_size(cls, v):
        """Validate pool size."""
        if v < 1:
            raise ValueError("Pool size must be at least 1")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v):
        """Validate timeout."""
        if v < 1:
            raise ValueError("Timeout must be at least 1 second")
        return v

    @field_validator("retry_count")
    @classmethod
    def validate_retry_count(cls, v):
        """Validate retry count."""
        if v < 0:
            raise ValueError("Retry count cannot be negative")
        return v


class SessionServiceConfig(ServiceConfig):
    """Configuration specific to session services."""

    session_timeout: int = 3600
    max_sessions: int = 100
    cleanup_interval: int = 300

    @field_validator("session_timeout")
    @classmethod
    def validate_session_timeout(cls, v):
        """Validate session timeout."""
        if v < 60:
            raise ValueError("Session timeout must be at least 60 seconds")
        return v

    @field_validator("max_sessions")
    @classmethod
    def validate_max_sessions(cls, v):
        """Validate max sessions."""
        if v < 1:
            raise ValueError("Max sessions must be at least 1")
        return v

    @field_validator("cleanup_interval")
    @classmethod
    def validate_cleanup_interval(cls, v):
        """Validate cleanup interval."""
        if v < 60:
            raise ValueError("Cleanup interval must be at least 60 seconds")
        return v


class LoggingServiceConfig(ServiceConfig):
    """Configuration specific to logging services."""

    log_level: str = "INFO"
    console_level: str = "INFO"
    file_level: str = "DEBUG"
    log_file_path: Optional[str] = None
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5

    @field_validator("log_level", "console_level", "file_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    @field_validator("max_file_size")
    @classmethod
    def validate_max_file_size(cls, v):
        """Validate max file size."""
        if v < 1024:
            raise ValueError("Max file size must be at least 1KB")
        return v

    @field_validator("backup_count")
    @classmethod
    def validate_backup_count(cls, v):
        """Validate backup count."""
        if v < 0:
            raise ValueError("Backup count must be non-negative")
        return v

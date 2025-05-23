"""
Base Configuration - Common settings for all agents.

This module defines the base configuration settings that are common across all agents.
All default values are defined in base_config.yaml, not in these classes.
These classes define the structure and validation rules only.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import jsonschema
import yaml
from jsonschema import validate
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LLMSettings(BaseModel):
    """Base LLM settings that can be shared between models and services."""

    max_tokens: int = Field(gt=0, description="Maximum tokens to generate")
    context_window: int = Field(gt=0, description="Maximum context window size")
    temperature: float = Field(ge=0.0, le=2.0, description="Sampling temperature")
    top_p: float = Field(ge=0.0, le=1.0, description="Nucleus sampling parameter")
    frequency_penalty: float = Field(ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(ge=-2.0, le=2.0, description="Presence penalty")

    @field_validator("max_tokens")
    def validate_max_tokens(cls, v, info):
        """Ensure max_tokens doesn't exceed context_window."""
        if "context_window" in info.data and v > info.data["context_window"]:
            raise ValueError("max_tokens cannot exceed context_window")
        return v


class ModelConfig(BaseModel):
    """LLM model configuration."""

    model: str
    settings: LLMSettings
    system_prompt: str = ""
    dimensions: Optional[int] = None
    normalize: Optional[bool] = None


class LLMConfig(BaseModel):
    """LLM service configuration."""

    api_url: str
    default_model: str
    timeout: int = Field(gt=0, description="Request timeout in seconds")
    settings: LLMSettings
    models: Dict[str, ModelConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_config(self) -> "LLMConfig":
        """Validate LLM configuration."""
        if self.timeout < 1:
            raise ValueError("Timeout must be at least 1 second")
        if not self.models:
            raise ValueError("At least one model must be configured")
        return self


class LoggingConfig(BaseModel):
    """Logging configuration structure."""

    enable_logging: bool
    log_level: str = Field(pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_format: str
    log_file: Optional[str]
    log_to_console: bool
    log_to_file: bool
    log_rotation: str = Field(pattern="^\\d+\\s+(day|hour|minute|second)s?$")
    log_retention: str = Field(pattern="^\\d+\\s+(day|hour|minute|second)s?$")
    file_level: str = Field(pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    console_level: str = Field(pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_dir: str
    max_log_size_mb: int = Field(gt=0)
    backup_count: int = Field(ge=0)
    formatters: Dict[str, Dict[str, str]]
    noisy_loggers: List[str]

    @model_validator(mode="after")
    def validate_logging_config(self) -> "LoggingConfig":
        """Validate logging configuration."""
        if self.log_to_file and not self.log_file:
            raise ValueError("log_file must be set when log_to_file is True")
        if not self.log_to_console and not self.log_to_file:
            raise ValueError("At least one of log_to_console or log_to_file must be True")
        return self


class SupabaseConfig(BaseModel):
    """Supabase configuration structure."""

    url: str = Field(pattern="^https?://.+")
    anon_key: str = Field(min_length=1)
    service_role_key: str = Field(min_length=1)


class PostgresConfig(BaseModel):
    """Postgres configuration structure."""

    url: str = Field(pattern="^postgresql://.+")


class DatabaseProvidersConfig(BaseModel):
    """Database providers configuration structure."""

    supabase_local: Optional[SupabaseConfig]
    supabase_web: Optional[SupabaseConfig]
    postgres: Optional[PostgresConfig]

    @model_validator(mode="after")
    def validate_providers(self) -> "DatabaseProvidersConfig":
        """Ensure at least one provider is configured."""
        if not any([self.supabase_local, self.supabase_web, self.postgres]):
            raise ValueError("At least one database provider must be configured")
        return self


class DatabaseConfig(BaseModel):
    """Database configuration structure."""

    provider: str = Field(pattern="^(supabase_local|supabase_web|postgres)$")
    providers: DatabaseProvidersConfig
    pool_size: int = Field(gt=0)
    max_overflow: int = Field(ge=0)
    echo: bool
    pool_timeout: int = Field(gt=0)
    pool_recycle: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_provider_exists(self) -> "DatabaseConfig":
        """Ensure configured provider exists."""
        provider_config = getattr(self.providers, self.provider, None)
        if not provider_config:
            raise ValueError(f"Provider '{self.provider}' is not configured")
        return self


class GraphConfig(BaseModel):
    """Graph configuration structure."""

    name: str = Field(min_length=1)
    description: str
    version: str = Field(pattern="^\\d+\\.\\d+\\.\\d+$")
    max_depth: int = Field(gt=0)
    max_breadth: int = Field(gt=0)
    timeout: int = Field(gt=0)
    retry_count: int = Field(ge=0)
    nodes: Dict[str, Any]
    edges: List[Dict[str, Any]]

    @model_validator(mode="after")
    def validate_edges(self) -> "GraphConfig":
        """Validate edge references."""
        node_ids = set(self.nodes.keys())
        for edge in self.edges:
            if edge.get("from") not in node_ids:
                raise ValueError(f"Edge references non-existent node: {edge.get('from')}")
            if edge.get("to") not in node_ids:
                raise ValueError(f"Edge references non-existent node: {edge.get('to')}")
        return self


class PersonalityConfig(BaseModel):
    """Personality configuration structure."""

    name: str = Field(min_length=1)
    description: str
    traits: List[str]
    goals: List[str]
    constraints: List[str]
    system_prompt: str
    examples: List[Dict[str, str]]
    enabled: bool
    file_path: Optional[str]
    use_by_default: bool

    @model_validator(mode="after")
    def validate_personality(self) -> "PersonalityConfig":
        """Validate personality configuration."""
        if self.enabled and not self.system_prompt:
            raise ValueError("system_prompt is required when personality is enabled")
        if self.file_path and not os.path.exists(self.file_path):
            raise ValueError(f"Personality file not found: {self.file_path}")
        return self


class PersonalitiesConfig(BaseModel):
    """Multiple personalities configuration structure."""

    default_personality: str
    personalities: Dict[str, PersonalityConfig]

    @model_validator(mode="after")
    def validate_personalities(self) -> "PersonalitiesConfig":
        """Validate personalities configuration."""
        if not self.personalities:
            raise ValueError("At least one personality must be configured")
        if self.default_personality not in self.personalities:
            raise ValueError(f"Default personality '{self.default_personality}' not found")
        if not any(p.use_by_default for p in self.personalities.values()):
            raise ValueError("At least one personality must be marked as use_by_default")
        return self


class AgentConfig(BaseModel):
    """Common agent configuration structure."""

    enable_history: bool
    user_id: str = Field(min_length=1)
    graph_name: str = Field(min_length=1)
    settings: LLMSettings
    enable_logging: bool
    prompt_section: str
    personality: Optional[PersonalityConfig]


class ToolConfig(BaseModel):
    """Common tool configuration structure."""

    tool_timeout: int = Field(gt=0)
    max_retries: int = Field(ge=0)
    inherit_from_parent: bool
    allowed_tools: List[str]
    tool_descriptions: Dict[str, str]

    @model_validator(mode="after")
    def validate_tools(self) -> "ToolConfig":
        """Validate tool configuration."""
        if self.allowed_tools and not self.tool_descriptions:
            raise ValueError("tool_descriptions must be provided when allowed_tools is set")
        for tool in self.allowed_tools:
            if tool not in self.tool_descriptions:
                raise ValueError(f"Missing description for tool: {tool}")
        return self


class SessionRetentionPolicy(BaseModel):
    """Session retention policy configuration."""

    user_sessions: str = Field(pattern="^\\d+\\s+(day|hour|minute|second)s?$")
    system_sessions: str = Field(pattern="^\\d+\\s+(day|hour|minute|second)s?$")
    temporary_sessions: str = Field(pattern="^\\d+\\s+(day|hour|minute|second)s?$")


class SessionConfig(BaseModel):
    """Session configuration structure."""

    session_timeout: int = Field(gt=0, description="Session timeout in seconds")
    max_sessions: int = Field(gt=0, description="Maximum number of concurrent sessions")
    cleanup_interval: int = Field(gt=0, description="Session cleanup interval in seconds")
    session_dir: str = Field(min_length=1, description="Directory for session storage")
    session_file: str = Field(min_length=1, description="Session file name")
    backup_count: int = Field(ge=0, description="Number of backup files to keep")
    auto_cleanup: bool = Field(description="Whether to automatically clean up expired sessions")
    compression_enabled: bool = Field(description="Whether to compress session data")
    encryption_enabled: bool = Field(description="Whether to encrypt session data")
    session_types: List[str] = Field(min_items=1, description="Supported session types")
    retention_policy: SessionRetentionPolicy

    @model_validator(mode="after")
    def validate_config(self) -> "SessionConfig":
        """Validate session configuration."""
        if self.session_timeout < self.cleanup_interval:
            raise ValueError("session_timeout must be greater than cleanup_interval")
        if not os.path.exists(self.session_dir):
            try:
                os.makedirs(self.session_dir)
            except Exception as e:
                raise ValueError(f"Could not create session directory: {e}")
        return self


class BaseConfig(BaseModel):
    """Base configuration model."""

    model_config = ConfigDict(extra="forbid")  # Prevent extra fields

    llm: Dict[str, Any]  # Will be validated by provider-specific models
    logging: LoggingConfig
    database: DatabaseConfig
    graph: GraphConfig
    agent: AgentConfig
    tools: ToolConfig
    personalities: PersonalitiesConfig
    session: SessionConfig  # Add session configuration


def load_config(config_path: str) -> BaseConfig:
    """Load and validate configuration from YAML file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}

    return BaseConfig(**config)

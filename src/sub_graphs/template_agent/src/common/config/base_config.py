"""
Base Configuration - Common settings for all agents.

This module defines the base configuration settings that are common across all agents.
All default values are defined in base_config.yaml, not in these classes.
These classes define the structure and validation rules only.
"""

from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict
from datetime import datetime
import yaml
import os
import logging
import jsonschema
from jsonschema import validate

class CommonSettings(BaseModel):
    """Common settings shared across different configs."""
    max_tokens: int = Field(gt=0, description="Maximum tokens to generate")
    context_window: int = Field(gt=0, description="Maximum context window size")
    temperature: float = Field(ge=0.0, le=2.0, description="Sampling temperature")
    top_p: float = Field(ge=0.0, le=1.0, description="Nucleus sampling parameter")
    frequency_penalty: float = Field(ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(ge=-2.0, le=2.0, description="Presence penalty")

    @field_validator('max_tokens')
    def validate_max_tokens(cls, v, info):
        """Ensure max_tokens doesn't exceed context_window."""
        if 'context_window' in info.data and v > info.data['context_window']:
            raise ValueError("max_tokens cannot exceed context_window")
        return v

# LLM Provider Defaults
PROVIDER_DEFAULTS = {
    'ollama': {
        'api_url': 'http://localhost:11434',
        'default_model': 'llama3.1:latest',
        'temperature': 0.7,
        'max_tokens': 2048,
        'context_window': 16384,
        'models': {}
    },
    'openai': {
        'api_url': 'https://api.openai.com/v1',
        'default_model': 'gpt-4',
        'temperature': 0.7,
        'max_tokens': 4096,
        'models': {}
    }
}

# LLM Model Defaults
PROVIDER_DEFAULT_MODELS = {
    'ollama': {
        'embedding': 'nomic-embed-text',
        'programming': 'llama3.1:latest',
        'reasoning': 'deepseek-r1',
        'chat': 'llama3.1:latest',
    },
    'openai': {
        'embedding': 'text-embedding-ada-002',
        'programming': 'gpt-4',
        'reasoning': 'gpt-4',
        'chat': 'gpt-4',
    }
}

class ModelConfig(BaseModel):
    """LLM model configuration."""
    model: str
    settings: CommonSettings = CommonSettings()
    system_prompt: str = ""
    dimensions: Optional[int] = None
    normalize: Optional[bool] = None

class LLMConfig(BaseModel):
    """LLM service configuration."""
    api_url: str
    default_model: str
    timeout: int = 30
    settings: CommonSettings = CommonSettings()
    models: Dict[str, ModelConfig] = Field(default_factory=dict)

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

    @model_validator(mode='after')
    def validate_logging_config(self) -> 'LoggingConfig':
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

    @model_validator(mode='after')
    def validate_providers(self) -> 'DatabaseProvidersConfig':
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

    @model_validator(mode='after')
    def validate_provider_exists(self) -> 'DatabaseConfig':
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

    @model_validator(mode='after')
    def validate_edges(self) -> 'GraphConfig':
        """Validate edge references."""
        node_ids = set(self.nodes.keys())
        for edge in self.edges:
            if edge.get('from') not in node_ids:
                raise ValueError(f"Edge references non-existent node: {edge.get('from')}")
            if edge.get('to') not in node_ids:
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

    @model_validator(mode='after')
    def validate_personality(self) -> 'PersonalityConfig':
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

    @model_validator(mode='after')
    def validate_personalities(self) -> 'PersonalitiesConfig':
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
    settings: CommonSettings
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

    @model_validator(mode='after')
    def validate_tools(self) -> 'ToolConfig':
        """Validate tool configuration."""
        if self.allowed_tools and not self.tool_descriptions:
            raise ValueError("tool_descriptions must be provided when allowed_tools is set")
        for tool in self.allowed_tools:
            if tool not in self.tool_descriptions:
                raise ValueError(f"Missing description for tool: {tool}")
        return self

class BaseConfig(BaseModel):
    """Base configuration model."""
    model_config = ConfigDict(extra='forbid')  # Prevent extra fields
    
    llm: Dict[str, Any]  # Will be validated by provider-specific models
    logging: LoggingConfig
    database: DatabaseConfig
    graph: GraphConfig
    agent: AgentConfig
    tools: ToolConfig
    personalities: PersonalitiesConfig

def get_default_model(provider: str, purpose: str) -> str:
    """Return the default model for a provider and purpose."""
    return PROVIDER_DEFAULT_MODELS.get(provider, {}).get(purpose, '')

def load_config(config_path: str) -> BaseConfig:
    """Load and validate configuration from YAML file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
        
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}
    
    # Validate YAML structure against schema
    try:
        validate(instance=config, schema=YAML_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        raise ValueError(f"Invalid YAML structure: {str(e)}")
        
    return BaseConfig(**config) 
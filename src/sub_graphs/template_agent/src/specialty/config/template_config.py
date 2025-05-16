"""
Template Configuration - Example of configuration specialization.

This module demonstrates how to extend the base configuration with template-specific settings.
This is just example code showing the override points, not meant for production use.

To use these overrides:
1. Copy the override class you want to use
2. Replace the example values with your actual values
3. Comment out or remove any overrides you don't need
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict
from ...common.config.base_config import (
    BaseConfig, AgentConfig, ToolConfig, LLMConfig, LoggingConfig,
    DatabaseConfig, GraphConfig, PersonalityConfig
)
import os
import yaml
import jsonschema
from jsonschema import validate

# YAML Schema for template-specific settings
TEMPLATE_YAML_SCHEMA = {
    "type": "object",
    "properties": {
        "template_agent": {
            "type": "object",
            "properties": {
                "enable_tool_specialization": {"type": "boolean"},
                "specialized_tools": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "custom_prompt_template": {"type": "string"},
                "max_tokens": {"type": "integer", "minimum": 1},
                "context_window": {"type": "integer", "minimum": 1}
            }
        },
        "template_tools": {
            "type": "object",
            "properties": {
                "allowed_tools": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "tool_descriptions": {
                    "type": "object",
                    "additionalProperties": {"type": "string"}
                },
                "tool_timeout": {"type": "integer", "minimum": 1},
                "max_retries": {"type": "integer", "minimum": 0}
            }
        },
        "template_llm": {
            "type": "object",
            "properties": {
                "model_family": {"type": "string"},
                "model_version": {"type": "string"},
                "temperature": {"type": "number", "minimum": 0.0, "maximum": 2.0},
                "top_p": {"type": "number", "minimum": 0.0, "maximum": 1.0}
            }
        },
        "template_logging": {
            "type": "object",
            "properties": {
                "log_prefix": {"type": "string"},
                "log_rotation_size": {"type": "string", "pattern": "^\\d+[KMG]B$"},
                "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
                "log_to_file": {"type": "boolean"}
            }
        },
        "template_database": {
            "type": "object",
            "properties": {
                "custom_pool_settings": {
                    "type": "object",
                    "properties": {
                        "pool_recycle": {"type": "integer", "minimum": 1},
                        "pool_pre_ping": {"type": "boolean"}
                    }
                },
                "pool_size": {"type": "integer", "minimum": 1},
                "max_overflow": {"type": "integer", "minimum": 0}
            }
        },
        "template_graph": {
            "type": "object",
            "properties": {
                "custom_node_types": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "custom_edge_types": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "max_depth": {"type": "integer", "minimum": 1},
                "max_breadth": {"type": "integer", "minimum": 1}
            }
        },
        "template_personality": {
            "type": "object",
            "properties": {
                "custom_traits": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "custom_goals": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "system_prompt": {"type": "string"}
            }
        }
    }
}

class TemplateAgentConfig(AgentConfig):
    """
    Example: Override agent configuration with template-specific settings.
    
    To use this override:
    1. Copy this class
    2. Replace the example values with your actual values
    3. Comment out any overrides you don't need
    """
    # Example: Add template-specific settings
    enable_tool_specialization: bool = Field(default=False, description="Enable/disable tool specialization")
    specialized_tools: List[str] = Field(default_factory=list, description="List of specialized tools")
    custom_prompt_template: Optional[str] = Field(default=None, description="Custom prompt template")
    
    # Example: Override base settings
    max_tokens: int = Field(default=4096, gt=0, description="Override base max_tokens")
    context_window: int = Field(default=16384, gt=0, description="Override base context_window")

    @model_validator(mode='after')
    def validate_specialized_tools(self) -> 'TemplateAgentConfig':
        """Validate specialized tools configuration."""
        if self.enable_tool_specialization and not self.specialized_tools:
            raise ValueError("specialized_tools must be set when enable_tool_specialization is True")
        return self

class TemplateToolConfig(ToolConfig):
    """
    Example: Override tool configuration with template-specific settings.
    
    To use this override:
    1. Copy this class
    2. Replace the example values with your actual values
    3. Comment out any overrides you don't need
    """
    # Example: Add template-specific tool settings
    allowed_tools: List[str] = Field(default_factory=list, description="List of allowed tools")
    tool_descriptions: Dict[str, str] = Field(default_factory=dict, description="Tool descriptions")
    
    # Example: Override base settings
    tool_timeout: int = Field(default=60, gt=0, description="Override base tool_timeout")
    max_retries: int = Field(default=5, ge=0, description="Override base max_retries")

    @model_validator(mode='after')
    def validate_tools(self) -> 'TemplateToolConfig':
        """Validate tool configuration."""
        if self.allowed_tools and not self.tool_descriptions:
            raise ValueError("tool_descriptions must be provided when allowed_tools is set")
        for tool in self.allowed_tools:
            if tool not in self.tool_descriptions:
                raise ValueError(f"Missing description for tool: {tool}")
        return self

class TemplateLLMConfig(LLMConfig):
    """
    Example: Override LLM configuration with template-specific settings.
    
    To use this override:
    1. Copy this class
    2. Replace the example values with your actual values
    3. Comment out any overrides you don't need
    """
    # Example: Add template-specific LLM settings
    model_family: str = Field(default="gpt", description="Model family")
    model_version: str = Field(default="4", description="Model version")
    
    # Example: Override base settings
    temperature: float = Field(default=0.8, ge=0.0, le=2.0, description="Override base temperature")
    top_p: float = Field(default=0.95, ge=0.0, le=1.0, description="Override base top_p")

class TemplateLoggingConfig(LoggingConfig):
    """
    Example: Override logging configuration with template-specific settings.
    
    To use this override:
    1. Copy this class
    2. Replace the example values with your actual values
    3. Comment out any overrides you don't need
    """
    # Example: Add template-specific logging settings
    log_prefix: str = Field(default="template_", description="Log file prefix")
    log_rotation_size: str = Field(default="100MB", pattern="^\\d+[KMG]B$", description="Log rotation size")
    
    # Example: Override base settings
    log_level: str = Field(default="DEBUG", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$", description="Override base log_level")
    log_to_file: bool = Field(default=True, description="Override base log_to_file")

class TemplateDatabaseConfig(DatabaseConfig):
    """
    Example: Override database configuration with template-specific settings.
    
    To use this override:
    1. Copy this class
    2. Replace the example values with your actual values
    3. Comment out any overrides you don't need
    """
    # Example: Add template-specific database settings
    custom_pool_settings: Dict[str, Any] = Field(
        default_factory=lambda: {"pool_recycle": 1800, "pool_pre_ping": True},
        description="Custom pool settings"
    )
    
    # Example: Override base settings
    pool_size: int = Field(default=10, gt=0, description="Override base pool_size")
    max_overflow: int = Field(default=20, ge=0, description="Override base max_overflow")

class TemplateGraphConfig(GraphConfig):
    """
    Example: Override graph configuration with template-specific settings.
    
    To use this override:
    1. Copy this class
    2. Replace the example values with your actual values
    3. Comment out any overrides you don't need
    """
    # Example: Add template-specific graph settings
    custom_node_types: List[str] = Field(default_factory=list, description="Custom node types")
    custom_edge_types: List[str] = Field(default_factory=list, description="Custom edge types")
    
    # Example: Override base settings
    max_depth: int = Field(default=15, gt=0, description="Override base max_depth")
    max_breadth: int = Field(default=8, gt=0, description="Override base max_breadth")

class TemplatePersonalityConfig(PersonalityConfig):
    """
    Example: Override personality configuration with template-specific settings.
    
    To use this override:
    1. Copy this class
    2. Replace the example values with your actual values
    3. Comment out any overrides you don't need
    """
    # Example: Add template-specific personality settings
    custom_traits: List[str] = Field(default_factory=list, description="Custom traits")
    custom_goals: List[str] = Field(default_factory=list, description="Custom goals")
    
    # Example: Override base settings
    system_prompt: str = Field(default="You are a helpful template agent.", description="Override base system_prompt")

class TemplateConfig(BaseConfig):
    """
    Example: Override base configuration with template-specific settings.
    
    To use this override:
    1. Copy this class
    2. Replace the example values with your actual values
    3. Comment out any overrides you don't need
    """
    model_config = ConfigDict(extra='forbid')  # Prevent extra fields
    
    # Example: Override component configs with template-specific versions
    template_agent: TemplateAgentConfig = Field(default_factory=TemplateAgentConfig)
    template_tools: TemplateToolConfig = Field(default_factory=TemplateToolConfig)
    template_llm: Dict[str, TemplateLLMConfig] = Field(
        default_factory=lambda: {
            "default": TemplateLLMConfig(
                api_url="https://api.example.com/v1",
                default_model="gpt-4"
            )
        }
    )
    template_logging: TemplateLoggingConfig = Field(default_factory=TemplateLoggingConfig)
    template_database: TemplateDatabaseConfig = Field(default_factory=TemplateDatabaseConfig)
    template_graph: TemplateGraphConfig = Field(default_factory=TemplateGraphConfig)
    template_personality: TemplatePersonalityConfig = Field(default_factory=TemplatePersonalityConfig)

def load_template_config(config_path: str) -> TemplateConfig:
    """Load and validate template configuration from YAML file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Template config file not found: {config_path}")
        
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}
    
    # Validate YAML structure against schema
    try:
        validate(instance=config, schema=TEMPLATE_YAML_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        raise ValueError(f"Invalid template YAML structure: {str(e)}")
        
    return TemplateConfig(**config) 
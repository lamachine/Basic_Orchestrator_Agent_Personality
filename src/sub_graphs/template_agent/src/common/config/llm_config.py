"""
LLM Configuration Module

This module defines the configuration for LLM services.
It includes settings for model selection, generation parameters,
and API configuration.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """Configuration for LLM service."""

    service_name: str = Field(..., description="Name of the service")
    enabled: bool = Field(default=True, description="Whether the service is enabled")
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Service-specific configuration"
    )

    # Model settings
    model_name: str = Field(..., description="Name of the LLM model to use")
    model_type: str = Field(default="ollama", description="Type of LLM (e.g., ollama, openai)")

    # Generation parameters
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Sampling temperature")
    max_tokens: int = Field(default=2000, gt=0, description="Maximum tokens to generate")
    stop_sequences: List[str] = Field(default_factory=list, description="Stop sequences")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Top-p sampling parameter")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")

    # Feature flags
    cache_enabled: bool = Field(default=True, description="Whether to cache responses")
    streaming_enabled: bool = Field(default=False, description="Whether to enable streaming")

    # API settings
    api_url: Optional[str] = Field(None, description="API URL for the LLM service")
    api_key: Optional[str] = Field(None, description="API key for the LLM service")

    def get_merged_config(self) -> Dict[str, Any]:
        """Get merged configuration including defaults."""
        return self.config

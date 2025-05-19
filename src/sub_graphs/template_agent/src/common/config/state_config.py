"""
State Configuration Module

This module defines the configuration for state management services.
It includes settings for state persistence, history tracking,
and state transitions.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StateServiceConfig(BaseModel):
    """Configuration for state service."""

    service_name: str = Field(..., description="Name of the service")
    enabled: bool = Field(default=True, description="Whether the service is enabled")
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Service-specific configuration"
    )

    # State management
    max_state_history: int = Field(
        default=100, description="Maximum number of states to keep in history"
    )
    persistence_enabled: bool = Field(default=True, description="Whether to persist state")
    cleanup_interval: int = Field(default=3600, description="State cleanup interval in seconds")

    # State transitions
    transition_timeout: int = Field(
        default=30, gt=0, description="Timeout for state transitions in seconds"
    )
    max_retries: int = Field(default=3, ge=0, description="Maximum number of transition retries")
    retry_delay: int = Field(default=1, gt=0, description="Delay between retries in seconds")

    # Feature flags
    validation_enabled: bool = Field(
        default=True, description="Whether to validate state transitions"
    )
    rollback_enabled: bool = Field(default=True, description="Whether to enable state rollback")
    compression_enabled: bool = Field(default=False, description="Whether to compress state data")

    def get_merged_config(self) -> Dict[str, Any]:
        """Get merged configuration including defaults."""
        return self.config

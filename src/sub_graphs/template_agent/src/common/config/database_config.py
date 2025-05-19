"""
Database Configuration Module

This module defines the configuration for database services.
It includes settings for connection parameters, pooling,
and database-specific features.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DBServiceConfig(BaseModel):
    """Configuration for database service."""

    service_name: str = Field(..., description="Name of the service")
    enabled: bool = Field(default=True, description="Whether the service is enabled")
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Service-specific configuration"
    )

    # Database settings
    provider: str = Field(..., description="Database provider (e.g., postgresql, supabase)")
    connection_params: Dict[str, Any] = Field(..., description="Database connection parameters")

    # Pool settings
    pool_size: int = Field(default=5, gt=0, description="Connection pool size")
    max_overflow: int = Field(default=10, ge=0, description="Maximum overflow connections")
    pool_timeout: int = Field(default=30, gt=0, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=3600, gt=0, description="Pool recycle time in seconds")

    # Feature flags
    echo: bool = Field(default=False, description="Whether to echo SQL statements")
    autocommit: bool = Field(default=True, description="Whether to autocommit transactions")
    autoflush: bool = Field(default=True, description="Whether to autoflush sessions")

    def get_merged_config(self) -> Dict[str, Any]:
        """Get merged configuration including defaults."""
        return self.config

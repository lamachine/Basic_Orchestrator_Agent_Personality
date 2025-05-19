"""
Logging Configuration Module

This module defines the configuration for logging services.
It includes settings for log levels, formats, handlers,
and log file management.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LoggingServiceConfig(BaseModel):
    """Configuration for logging service."""

    service_name: str = Field(..., description="Name of the service")
    enabled: bool = Field(default=True, description="Whether the service is enabled")
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Service-specific configuration"
    )

    # Log settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(None, description="Path to log file")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )

    # Handler settings
    console_enabled: bool = Field(default=True, description="Whether to log to console")
    file_enabled: bool = Field(default=True, description="Whether to log to file")
    max_file_size: int = Field(default=10485760, gt=0, description="Maximum log file size in bytes")
    backup_count: int = Field(default=5, ge=0, description="Number of backup files to keep")

    # Filter settings
    exclude_loggers: List[str] = Field(
        default_factory=list, description="List of logger names to exclude"
    )
    include_loggers: List[str] = Field(
        default_factory=list, description="List of logger names to include"
    )

    def get_merged_config(self) -> Dict[str, Any]:
        """Get merged configuration including defaults."""
        return self.config

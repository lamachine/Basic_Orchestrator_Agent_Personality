"""
Service Models Module

This module defines the base models for services and their configurations.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ServiceCapability(BaseModel):
    """Service capability model."""

    name: str
    description: str
    enabled: bool = True
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ServiceConfig(BaseModel):
    """Base service configuration model."""

    service_name: str
    enabled: bool = True
    capabilities: Dict[str, ServiceCapability] = Field(default_factory=dict)

    def get_capability(self, name: str) -> Optional[ServiceCapability]:
        """Get a capability by name."""
        return self.capabilities.get(name)

    def is_capability_enabled(self, name: str) -> bool:
        """Check if a capability is enabled."""
        capability = self.get_capability(name)
        return bool(capability and capability.enabled)

    def get_merged_config(self) -> Dict[str, Any]:
        """Get merged configuration."""
        return {
            "service_name": self.service_name,
            "enabled": self.enabled,
            "capabilities": {name: cap.model_dump() for name, cap in self.capabilities.items()},
        }


class PoolConfig(BaseModel):
    """Database connection pool configuration."""

    pool_size: int = Field(gt=0, default=5)
    max_overflow: int = Field(ge=0, default=10)
    pool_timeout: int = Field(gt=0, default=30)
    pool_recycle: int = Field(gt=0, default=3600)
    pool_pre_ping: bool = True
    echo: bool = False
    max_identifier_length: Optional[int] = None
    pool_use_lifo: bool = False
    pool_reset_on_return: str = "rollback"
    pool_overflow: int = Field(ge=0, default=10)
    pool_recycle_time: int = Field(gt=0, default=3600)
    pool_use_threadlocal: bool = True
    pool_use_unicode: bool = True
    pool_use_unicode_errors: str = "strict"
    pool_use_unicode_errors_encoding: str = "utf-8"
    pool_use_unicode_errors_replace: bool = False
    pool_use_unicode_errors_ignore: bool = False
    pool_use_unicode_errors_xmlcharrefreplace: bool = False
    pool_use_unicode_errors_backslashreplace: bool = False
    pool_use_unicode_errors_surrogateescape: bool = False
    pool_use_unicode_errors_surrogatepass: bool = False
    pool_use_unicode_errors_ignore: bool = False
    pool_use_unicode_errors_replace: bool = False
    pool_use_unicode_errors_xmlcharrefreplace: bool = False
    pool_use_unicode_errors_backslashreplace: bool = False
    pool_use_unicode_errors_surrogateescape: bool = False
    pool_use_unicode_errors_surrogatepass: bool = False


class StateServiceConfig(ServiceConfig):
    """State service configuration."""

    state_dir: str
    state_file: str
    backup_count: int = Field(ge=0)
    auto_save: bool = True
    save_interval: int = Field(gt=0)
    max_state_history: int = Field(gt=0)
    cleanup_interval: int = Field(gt=0)
    compression_enabled: bool = False
    encryption_enabled: bool = False


class DBServiceConfig(ServiceConfig):
    """Database service configuration."""

    provider: str
    pool_config: PoolConfig = Field(default_factory=PoolConfig)
    connection_params: Dict[str, Any] = Field(default_factory=dict)


class LoggingServiceConfig(ServiceConfig):
    """Logging service configuration."""

    log_level: str
    log_format: str
    log_file: Optional[str] = None
    log_to_console: bool = True
    log_to_file: bool = False
    log_rotation: str
    log_retention: str
    file_level: str
    console_level: str
    log_dir: str
    max_log_size_mb: int = Field(gt=0)
    backup_count: int = Field(ge=0)
    formatters: Dict[str, Dict[str, str]]
    noisy_loggers: List[str]


class LLMConfig(ServiceConfig):
    """LLM service configuration."""

    model_name: str
    model_type: str
    temperature: float = Field(ge=0.0, le=1.0)
    max_tokens: int = Field(gt=0)
    top_p: float = Field(ge=0.0, le=1.0)
    frequency_penalty: float = Field(ge=-2.0, le=2.0)
    presence_penalty: float = Field(ge=-2.0, le=2.0)
    stop_sequences: List[str] = Field(default_factory=list)
    timeout: int = Field(gt=0)
    retry_count: int = Field(ge=0)
    retry_delay: int = Field(gt=0)
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    deployment_name: Optional[str] = None
    context_window: int = Field(gt=0)
    embedding_model: Optional[str] = None
    embedding_dimensions: Optional[int] = None
    cache_enabled: bool = True
    cache_ttl: int = Field(gt=0)
    cache_dir: Optional[str] = None
    streaming_enabled: bool = False
    streaming_chunk_size: int = Field(gt=0)
    streaming_timeout: int = Field(gt=0)
    fallback_models: List[str] = Field(default_factory=list)
    fallback_strategy: str = "round_robin"
    rate_limit: Optional[int] = None
    rate_limit_window: Optional[int] = None
    rate_limit_strategy: str = "token_bucket"
    cost_tracking: bool = False
    cost_per_token: Optional[float] = None
    cost_per_request: Optional[float] = None
    cost_currency: str = "USD"
    monitoring_enabled: bool = False
    monitoring_metrics: List[str] = Field(default_factory=list)
    monitoring_interval: int = Field(gt=0)
    monitoring_exporters: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    prompt_templates: Dict[str, str] = Field(default_factory=dict)
    system_prompts: Dict[str, str] = Field(default_factory=dict)
    default_system_prompt: Optional[str] = None
    default_user_prompt: Optional[str] = None
    default_assistant_prompt: Optional[str] = None
    default_stop_sequences: List[str] = Field(default_factory=list)
    default_temperature: float = Field(ge=0.0, le=1.0)
    default_max_tokens: int = Field(gt=0)
    default_top_p: float = Field(ge=0.0, le=1.0)
    default_frequency_penalty: float = Field(ge=-2.0, le=2.0)
    default_presence_penalty: float = Field(ge=-2.0, le=2.0)
    default_timeout: int = Field(gt=0)
    default_retry_count: int = Field(ge=0)
    default_retry_delay: int = Field(gt=0)
    default_context_window: int = Field(gt=0)
    default_streaming_chunk_size: int = Field(gt=0)
    default_streaming_timeout: int = Field(gt=0)
    default_cost_per_token: Optional[float] = None
    default_cost_per_request: Optional[float] = None
    default_cost_currency: str = "USD"
    default_monitoring_interval: int = Field(gt=0)
    default_monitoring_metrics: List[str] = Field(default_factory=list)
    default_monitoring_exporters: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    default_prompt_templates: Dict[str, str] = Field(default_factory=dict)
    default_system_prompts: Dict[str, str] = Field(default_factory=dict)

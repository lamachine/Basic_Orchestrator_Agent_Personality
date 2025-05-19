"""
Original YAML (for traceability):
llm:
  default_provider: ollama
  providers:
    ollama:
      api_url: http://localhost:11434
      default_model: llama3.1:latest
      temperature: 0.7
      max_tokens: 2048
      context_window: 8192
      models:
        conversation:
          model: llama3.1:latest
          temperature: 0.7
          max_tokens: 2048
          system_prompt: You are a helpful assistant named Ronan.
        coding:
          model: codellama:latest
          temperature: 0.2
          max_tokens: 4096
          system_prompt: You are an expert programming assistant.
        reasoning:
          model: deepseek-r1
          temperature: 0.3
          max_tokens: 4096
          system_prompt: You are a logical reasoning assistant that thinks step by step.
        embedding:
          model: nomic-embed-text
          dimensions: 768
          normalize: true
    # openai:
    #   api_key: sk-...
    #   api_url: https://api.openai.com/v1
    #   default_model: gpt-4
    #   temperature: 0.7
    #   max_tokens: 4096
    #   models: {}

# Additional LLM config names found in the codebase (for consolidation):
# LLM_MODEL, LLM_PROVIDER, OLLAMA_HOST, EMBEDDING_MODEL, OLLAMA_API_URL, OLLAMA_EMBEDDING_MODEL
# ollama_api_url, ollama_model, llm_temperature, llm_max_tokens, llm_context_window, llm_models
# api_url, model, temperature, max_tokens, context_window, models, system_prompt, dimensions, normalize
"""

import logging
import os
from typing import Any, Dict, Optional, Union

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

EMBEDDING_MODEL = "nomic-embed-text"
PROGRAMMING_MODEL = "llama3.1:latest"
REASONING_MODEL = "deepseek-r1"
CHAT_MODEL = "llama3.1:latest"

# Always use the config in src/config, not a separate ./config folder
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "developer_user_config.yaml")


class ModelConfig(BaseModel):
    model: str
    temperature: float = 0.7
    max_tokens: int = 2048
    system_prompt: str = ""
    dimensions: Optional[int] = None
    normalize: Optional[bool] = None


class OllamaConfig(BaseModel):
    api_url: str = "http://localhost:11434"  # Preferred name
    default_model: str = "llama3.1:latest"  # Preferred name
    temperature: float = 0.7  # Preferred name
    max_tokens: int = 2048  # Preferred name
    context_window: int = 16384  # Preferred name
    models: Dict[str, ModelConfig] = Field(default_factory=dict)  # Preferred name


class OpenAIConfig(BaseModel):
    api_key: Optional[str]
    api_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4096
    models: Dict[str, ModelConfig] = Field(default_factory=dict)


class LLMProvidersConfig(BaseModel):
    ollama: Optional[OllamaConfig] = Field(default=None)
    openai: Optional[OpenAIConfig] = Field(default=None)

    model_config = {"extra": "ignore"}

    @model_validator(mode="after")
    def at_least_one_provider(self) -> "LLMProvidersConfig":
        if not self.ollama and not self.openai:
            raise ValueError("At least one LLM provider (ollama or openai) must be configured.")
        return self


class LLMConfig(BaseModel):
    default_provider: str = "ollama"  # Preferred name
    providers: LLMProvidersConfig  # Preferred name


PROVIDER_DEFAULTS = {
    "ollama": {
        "api_url": "http://localhost:11434",
        "default_model": "llama3.1:latest",
        "temperature": 0.7,
        "max_tokens": 2048,
        "context_window": 16384,
        "models": {},
    },
    "openai": {
        "api_url": "https://api.openai.com/v1",
        "default_model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 4096,
        "models": {},
    },
    "anthropic": {},
    "grok": {},
    "huggingface": {},
    "google": {},
}

PROVIDER_DEFAULT_MODELS = {
    "ollama": {
        "embedding": "nomic-embed-text",
        "programming": "llama3.1:latest",
        "reasoning": "deepseek-r1",
        "chat": "llama3.1:latest",
    },
    # Add other providers as needed
    "openai": {
        "embedding": "text-embedding-ada-002",
        "programming": "gpt-4",
        "reasoning": "gpt-4",
        "chat": "gpt-4",
    },
    # Extend for anthropic, grok, etc.
}


def get_default_model(provider: str, purpose: str) -> str:
    """Return the default model for a provider and purpose (embedding, programming, reasoning, chat)."""
    return PROVIDER_DEFAULT_MODELS.get(provider, {}).get(purpose, "")


def get_enabled_llm_providers(config_path: str = CONFIG_PATH):
    """
    Load YAML and return a dict of enabled LLM providers and their configs.
    """
    # print(f"[LLM CONFIG DEBUG] loading config from: {os.path.abspath(config_path)}")  # Demote to debug
    logger = logging.getLogger(__name__)
    logger.debug(f"[LLM CONFIG DEBUG] loading config from: {os.path.abspath(config_path)}")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}
    # print(f"[LLM CONFIG DEBUG] FULL YAML loaded: {config}")
    logger.debug(f"[LLM CONFIG DEBUG] FULL YAML loaded: {config}")
    llm_section = config.get("llm", {})
    providers = llm_section.get("providers", {})
    # print(f"[LLM CONFIG DEBUG] providers section: {providers}")
    logger.debug(f"[LLM CONFIG DEBUG] providers section: {providers}")
    enabled = {}
    for name, cfg in providers.items():
        if isinstance(cfg, dict) and cfg.get("enabled", False):
            enabled[name] = cfg
    # print(f"[LLM CONFIG DEBUG] enabled_providers: {enabled}")
    logger.debug(f"[LLM CONFIG DEBUG] enabled_providers: {enabled}")
    return enabled


def get_llm_config(config_path: str = CONFIG_PATH):
    # print("[LLM CONFIG DEBUG] >>> ENTERED get_llm_config <<<")
    logger = logging.getLogger(__name__)
    logger.debug("[LLM CONFIG DEBUG] >>> ENTERED get_llm_config <<<")
    enabled_providers = get_enabled_llm_providers(config_path)
    if not enabled_providers:
        raise ValueError("At least one LLM provider (ollama or openai) must be enabled in config.")
    validated = {}
    for provider, cfg in enabled_providers.items():
        cfg_no_enabled = {k: v for k, v in cfg.items() if k != "enabled"}
        if provider == "ollama":
            validated["ollama"] = OllamaConfig(**cfg_no_enabled)
        elif provider == "openai":
            validated["openai"] = OpenAIConfig(**cfg_no_enabled)
    # print(f"[LLM CONFIG DEBUG] validated configs: {validated}")
    logger.debug(f"[LLM CONFIG DEBUG] validated configs: {validated}")
    return validated


def get_provider_config(
    provider: Optional[str] = None, config_path: str = CONFIG_PATH
) -> Union[OllamaConfig, OpenAIConfig, None]:
    """
    Get the config for a specific provider (dynamic switching).
    Args:
        provider (str): Provider name (ollama, openai, ...). If None, uses default_provider.
        config_path (str): Path to YAML config file.
    Returns:
        Provider config model or None if not found.
    """
    llm_config = get_llm_config(config_path)
    provider_name = provider or llm_config.default_provider
    return getattr(llm_config.providers, provider_name, None)

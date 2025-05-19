"""
LLM Manager Module

This module implements the manager layer for LLM operations. As a manager (not a service), it:

"""

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI
from supabase import Client

from src.config.llm_config import get_provider_config
from src.services.llm_service import LLMService
from src.services.logging_service import get_logger

logger = get_logger(__name__)


@dataclass
class LLMUsageStats:
    """Track LLM usage statistics."""

    total_requests: int = 0
    total_tokens: int = 0
    total_errors: int = 0
    last_request: Optional[datetime] = None
    average_latency: float = 0.0
    request_history: List[Dict[str, Any]] = field(default_factory=list)


class LLMManager:
    """Manager for LLM operations and state."""

    def __init__(self, api_url: str, model: str):
        """
        Initialize LLM manager.

        Args:
            api_url: API endpoint URL
            model: Model identifier
        """
        self.service = LLMService(api_url, model)
        self.stats = LLMUsageStats()
        self.cache: Dict[str, Tuple[str, datetime]] = {}
        self.lock = asyncio.Lock()


# Dependency dataclass for Pydantic AI
@dataclass
class PydanticAIDeps:
    supabase: Client
    openai_client: AsyncOpenAI

    def choose_provider(self, query_type: str, token_balances: dict, user_id: str = None):
        """
        Decide which LLM provider to use for a given query.
        """
        # Example logic, expand as needed
        if query_type == "code":
            return get_provider_config("ollama")
        elif token_balances.get("anthropic", 0) < 1000:
            return get_provider_config("openai")
        else:
            return get_provider_config("anthropic")

    def get_service_for_query(self, query_type: str, token_balances: dict, user_id: str = None):
        """
        Return an LLMService instance configured for the chosen provider.
        """
        provider_cfg = self.choose_provider(query_type, token_balances, user_id)
        # You may want to add logic here to instantiate the correct service class
        # For now, assume Ollama/OpenAI both use LLMService with different configs
        return LLMService(api_url=provider_cfg.api_url, model=provider_cfg.default_model)

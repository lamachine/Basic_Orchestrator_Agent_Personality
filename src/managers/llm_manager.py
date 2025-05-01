"""
LLM Manager Module

This module implements the manager layer for LLM operations. As a manager (not a service), it:

"""

import os
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from supabase import Client
from openai import AsyncOpenAI

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
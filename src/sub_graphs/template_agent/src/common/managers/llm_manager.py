"""
LLM Manager Module

This module implements the manager layer for LLM operations.
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from supabase import Client

from ..config.base_config import LLMConfig, LLMSettings, ModelConfig, load_config
from ..services.llm_service import LLMService
from ..state.state_models import Message, MessageStatus, MessageType
from .base_manager import BaseManager, ManagerState


class LLMUsageStats(BaseModel):
    """Track LLM usage statistics."""

    total_requests: int = 0
    total_tokens: int = 0
    total_errors: int = 0
    last_request: Optional[datetime] = None
    average_latency: float = 0.0
    request_history: List[Dict[str, Any]] = Field(default_factory=list)


class LLMState(ManagerState):
    """State model for LLM management."""

    active_providers: Dict[str, bool] = Field(default_factory=dict)
    token_balances: Dict[str, int] = Field(default_factory=dict)
    stats: LLMUsageStats = Field(default_factory=LLMUsageStats)


class LLMManager(BaseManager[LLMConfig, LLMState]):
    """Manager for LLM operations and state."""

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize the LLM manager.

        Args:
            config: Optional LLM configuration. If not provided, loads from base_config.yaml
        """
        if config is None:
            config = load_config("base_config.yaml").llm
        super().__init__(config)
        self.service = LLMService(config)

    async def initialize(self) -> None:
        """Initialize the LLM manager."""
        await super().initialize()
        # Initialize providers
        for provider in self.config.providers:
            self._state.active_providers[provider] = True
            self._state.token_balances[provider] = 0

    async def choose_provider(
        self,
        query_type: str,
        token_balances: Dict[str, int],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Decide which LLM provider to use for a given query.

        Args:
            query_type: Type of query (e.g., "code", "chat")
            token_balances: Dictionary of token balances per provider
            user_id: Optional user ID

        Returns:
            Provider configuration
        """
        try:
            if query_type == "code":
                return self.config.get_provider_config("ollama")
            elif token_balances.get("anthropic", 0) < 1000:
                return self.config.get_provider_config("openai")
            else:
                return self.config.get_provider_config("anthropic")

        except Exception as e:
            self.logger.error(f"Error choosing provider: {e}")
            raise RuntimeError(f"Failed to choose provider: {e}")

    async def get_service_for_query(
        self,
        query_type: str,
        token_balances: Dict[str, int],
        user_id: Optional[str] = None,
    ) -> LLMService:
        """
        Return an LLMService instance configured for the chosen provider.

        Args:
            query_type: Type of query
            token_balances: Dictionary of token balances per provider
            user_id: Optional user ID

        Returns:
            Configured LLMService instance
        """
        try:
            provider_cfg = await self.choose_provider(query_type, token_balances, user_id)
            return LLMService(api_url=provider_cfg.api_url, model=provider_cfg.default_model)

        except Exception as e:
            self.logger.error(f"Error getting service for query: {e}")
            raise RuntimeError(f"Failed to get service for query: {e}")

    async def update_stats(self, tokens: int, latency: float) -> None:
        """Update usage statistics.

        Args:
            tokens: Number of tokens used
            latency: Request latency in seconds
        """
        self._state.stats.total_requests += 1
        self._state.stats.total_tokens += tokens
        self._state.stats.last_request = datetime.now()

        # Update average latency
        if self._state.stats.average_latency == 0:
            self._state.stats.average_latency = latency
        else:
            self._state.stats.average_latency = (
                self._state.stats.average_latency * (self._state.stats.total_requests - 1) + latency
            ) / self._state.stats.total_requests

        # Add to history
        self._state.stats.request_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "tokens": tokens,
                "latency": latency,
            }
        )

        # Keep history at reasonable size
        if len(self._state.stats.request_history) > 1000:
            self._state.stats.request_history = self._state.stats.request_history[-1000:]

    async def generate_response(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Generate a response from the LLM.

        Args:
            prompt: Input prompt
            context: Optional context dictionary

        Returns:
            Message containing the response
        """
        try:
            # Create initial message
            message = self.create_message(
                content=prompt, message_type=MessageType.REQUEST, data=context or {}
            )
            self.update_state(message)

            # Get service for query
            service = await self.get_service_for_query(
                query_type="chat",
                token_balances=self._state.token_balances,
                user_id=context.get("user_id") if context else None,
            )

            # Generate response
            start_time = datetime.now()
            response_text = await service.generate(
                prompt=prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stop=self.config.stop_sequences,
            )
            end_time = datetime.now()
            latency = (end_time - start_time).total_seconds()

            # Update stats
            await self.update_stats(
                tokens=len(response_text.split()), latency=latency  # Rough estimate
            )

            # Create response message
            response = self.create_message(
                content=response_text,
                message_type=MessageType.RESPONSE,
                status=MessageStatus.SUCCESS,
                data={
                    "model": self.config.default_model,
                    "latency": latency,
                    "tokens": len(response_text.split()),
                },
            )
            self.update_state(response)
            return response

        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            error_msg = self.create_error_message(
                content=f"Error generating response: {str(e)}",
                error_data={"error": str(e)},
            )
            self.update_state(error_msg)
            return error_msg

    async def stream_response(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Message, None]:
        """Stream a response from the LLM.

        Args:
            prompt: Input prompt
            context: Optional context dictionary

        Yields:
            Messages containing response chunks
        """
        try:
            # Create initial message
            message = self.create_message(
                content=prompt, message_type=MessageType.REQUEST, data=context or {}
            )
            self.update_state(message)
            yield message

            # Get service for query
            service = await self.get_service_for_query(
                query_type="chat",
                token_balances=self._state.token_balances,
                user_id=context.get("user_id") if context else None,
            )

            # Stream response
            start_time = datetime.now()
            full_response = ""
            async for chunk in service.stream(
                prompt=prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stop=self.config.stop_sequences,
            ):
                full_response += chunk
                yield self.create_message(
                    content=chunk,
                    message_type=MessageType.RESPONSE,
                    status=MessageStatus.PARTIAL,
                    data={"model": self.config.default_model, "streaming": True},
                )

            end_time = datetime.now()
            latency = (end_time - start_time).total_seconds()

            # Update stats
            await self.update_stats(
                tokens=len(full_response.split()), latency=latency  # Rough estimate
            )

            # Create final message
            yield self.create_message(
                content=full_response,
                message_type=MessageType.RESPONSE,
                status=MessageStatus.SUCCESS,
                data={
                    "model": self.config.default_model,
                    "latency": latency,
                    "tokens": len(full_response.split()),
                },
            )

        except Exception as e:
            self.logger.error(f"Error streaming response: {e}")
            error_msg = self.create_error_message(
                content=f"Error streaming response: {str(e)}",
                error_data={"error": str(e)},
            )
            self.update_state(error_msg)
            yield error_msg

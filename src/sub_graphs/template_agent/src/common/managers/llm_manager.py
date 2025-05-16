"""
LLM Manager Module

This module implements the manager layer for LLM operations.
"""

import os
import asyncio
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator
from datetime import datetime
from pydantic import BaseModel, Field
from pathlib import Path
from supabase import Client
from openai import AsyncOpenAI

from .base_manager import BaseManager, ManagerState
from ..services.llm_service import LLMService
from ..config.llm_config import get_provider_config
from .state_models import Message, MessageType, MessageStatus
from .service_models import LLMServiceConfig

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
    stats: LLMUsageStats = Field(default_factory=LLMUsageStats)
    cache: Dict[str, Tuple[str, datetime]] = Field(default_factory=dict)
    current_provider: Optional[str] = None
    current_model: Optional[str] = None

class LLMManager(BaseManager):
    """Manager for LLM operations and state."""
    
    def __init__(self, config: LLMServiceConfig):
        """Initialize the LLM manager.
        
        Args:
            config: LLM service configuration
        """
        super().__init__(config)
        self.model_name = config.model_name
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        self.stop_sequences = config.stop_sequences
        self.service = LLMService(config.api_url, self.model_name)
        self.lock = asyncio.Lock()
        
        # Update state
        self.state.current_provider = config.api_url
        self.state.current_model = self.model_name

    async def choose_provider(self, 
                            query_type: str,
                            token_balances: Dict[str, int],
                            user_id: Optional[str] = None) -> Dict[str, Any]:
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
                return get_provider_config("ollama")
            elif token_balances.get("anthropic", 0) < 1000:
                return get_provider_config("openai")
            else:
                return get_provider_config("anthropic")
                
        except Exception as e:
            self.logger.error(f"Error choosing provider: {e}")
            raise RuntimeError(f"Failed to choose provider: {e}")

    async def get_service_for_query(self,
                                  query_type: str,
                                  token_balances: Dict[str, int],
                                  user_id: Optional[str] = None) -> LLMService:
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
            return LLMService(
                api_url=provider_cfg.api_url,
                model=provider_cfg.default_model
            )
            
        except Exception as e:
            self.logger.error(f"Error getting service for query: {e}")
            raise RuntimeError(f"Failed to get service for query: {e}")

    async def update_stats(self, 
                         tokens: int,
                         latency: float,
                         error: bool = False) -> None:
        """
        Update LLM usage statistics.
        
        Args:
            tokens: Number of tokens used
            latency: Request latency in seconds
            error: Whether the request resulted in an error
        """
        async with self.lock:
            self.state.stats.total_requests += 1
            self.state.stats.total_tokens += tokens
            if error:
                self.state.stats.total_errors += 1
                
            # Update average latency
            if self.state.stats.average_latency == 0:
                self.state.stats.average_latency = latency
            else:
                self.state.stats.average_latency = (
                    (self.state.stats.average_latency * (self.state.stats.total_requests - 1) + latency)
                    / self.state.stats.total_requests
                )
                
            self.state.stats.last_request = datetime.now()
            
            # Add to history
            self.state.stats.request_history.append({
                "timestamp": datetime.now().isoformat(),
                "tokens": tokens,
                "latency": latency,
                "error": error
            })
            
            # Keep only last 100 requests in history
            if len(self.state.stats.request_history) > 100:
                self.state.stats.request_history = self.state.stats.request_history[-100:]
                
            await self.persist_state()

    async def persist_state(self) -> None:
        """Persist the current LLM state."""
        # LLM state is ephemeral, no need to persist
        pass

    async def load_state(self) -> None:
        """Load the LLM state."""
        # LLM state is ephemeral, no need to load
        pass

    async def generate_response(self, 
                              prompt: str,
                              context: Optional[Dict[str, Any]] = None) -> Message:
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
                content=prompt,
                message_type=MessageType.REQUEST,
                data=context or {}
            )
            self.update_state(message)

            # Get service for query
            service = await self.get_service_for_query(
                query_type="chat",
                token_balances={},  # TODO: Get actual token balances
                user_id=context.get("user_id") if context else None
            )

            # Generate response
            start_time = datetime.now()
            response_text = await service.generate(
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stop=self.stop_sequences
            )
            end_time = datetime.now()
            latency = (end_time - start_time).total_seconds()

            # Update stats
            await self.update_stats(
                tokens=len(response_text.split()),  # Rough estimate
                latency=latency
            )

            # Create response message
            response = self.create_message(
                content=response_text,
                message_type=MessageType.RESPONSE,
                status=MessageStatus.SUCCESS,
                data={
                    "model": self.model_name,
                    "latency": latency,
                    "tokens": len(response_text.split())
                }
            )
            self.update_state(response)
            return response

        except Exception as e:
            error_msg = self.create_error_message(
                content=f"Error generating LLM response: {str(e)}",
                error_data={"error": str(e)}
            )
            self.update_state(error_msg)
            await self.update_stats(tokens=0, latency=0, error=True)
            return error_msg

    async def stream_response(self,
                            prompt: str,
                            context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[Message, None]:
        """Stream a response from the LLM.
        
        Args:
            prompt: Input prompt
            context: Optional context dictionary
            
        Yields:
            Messages containing the streamed response
        """
        try:
            # Create initial message
            message = self.create_message(
                content=prompt,
                message_type=MessageType.REQUEST,
                data=context or {}
            )
            self.update_state(message)
            yield message

            # Get service for query
            service = await self.get_service_for_query(
                query_type="chat",
                token_balances={},  # TODO: Get actual token balances
                user_id=context.get("user_id") if context else None
            )

            # Stream response
            start_time = datetime.now()
            full_response = ""
            async for chunk in service.stream(
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stop=self.stop_sequences
            ):
                full_response += chunk
                yield self.create_message(
                    content=chunk,
                    message_type=MessageType.RESPONSE,
                    status=MessageStatus.PARTIAL,
                    data={
                        "model": self.model_name,
                        "streaming": True
                    }
                )

            end_time = datetime.now()
            latency = (end_time - start_time).total_seconds()

            # Update stats
            await self.update_stats(
                tokens=len(full_response.split()),  # Rough estimate
                latency=latency
            )

            # Create final message
            final_message = self.create_message(
                content=full_response,
                message_type=MessageType.RESPONSE,
                status=MessageStatus.SUCCESS,
                data={
                    "model": self.model_name,
                    "latency": latency,
                    "tokens": len(full_response.split()),
                    "streaming": True
                }
            )
            self.update_state(final_message)
            yield final_message

        except Exception as e:
            error_msg = self.create_error_message(
                content=f"Error streaming LLM response: {str(e)}",
                error_data={"error": str(e)}
            )
            self.update_state(error_msg)
            await self.update_stats(tokens=0, latency=0, error=True)
            yield error_msg 
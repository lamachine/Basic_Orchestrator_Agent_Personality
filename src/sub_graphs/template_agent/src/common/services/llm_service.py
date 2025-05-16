"""
LLM Service Module

This module implements LLM operations as a service layer. As a service (not a manager), it:

1. Provides stateless utility functions for LLM operations
2. Focuses on a single responsibility (LLM access)
3. Does not make decisions about application flow
4. Offers tools and functions for LLM access

The key distinction of this being a service (vs a manager) is that it:
- Is stateless
- Provides utility functions
- Has a single responsibility
- Does not make decisions about system state
"""

import json
import os
import httpx
from typing import Dict, Any, List, Optional
import uuid
import traceback

from .logging_service import get_logger
from ..models.state_models import Message, MessageType, MessageStatus
from ..models.service_models import LLMServiceConfig

logger = get_logger(__name__)

class LLMService:
    """Service for LLM operations."""
    
    def __init__(self, config: LLMServiceConfig):
        """Initialize LLM service.
        
        Args:
            config: LLM service configuration
        """
        logger.debug(f"Initializing LLM Service")
        logger.debug(f"Config: {config}")
        
        self.config = config
        self.model = config.model_name
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        self.stop_sequences = config.stop_sequences
        
        # Get API URL from config
        api_url = config.get_merged_config().get("api_url", "http://localhost:11434/api")
        
        # Check if API URL ends with /api/generate and fix it
        if api_url.endswith('/generate'):
            logger.warning(f"API URL ends with /generate, removing suffix")
            api_url = api_url.rsplit('/generate', 1)[0]
        if api_url.endswith('/api/generate'):
            logger.warning(f"API URL ends with /api/generate, removing suffix")
            api_url = api_url.rsplit('/api/generate', 1)[0]
            
        self.api_url = api_url
        self.client = httpx.AsyncClient()
        
        logger.debug(f"LLM Service initialized with API URL: {self.api_url}")
        logger.debug("Created async HTTP client")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def _format_json(self, data: Dict[Any, Any]) -> str:
        """Format JSON data for logging with consistent indentation."""
        return json.dumps(data, indent=2)

    def _log_request(self, payload: Dict[Any, Any], prompt_length: int) -> None:
        """Log request details in a clean format."""
        logger.debug("LLM Request:")
        logger.debug(f"Model: {self.model}")
        logger.debug(f"Prompt length: {prompt_length} characters")
        logger.debug(f"Payload:\n{self._format_json(payload)}")

    def _log_response(self, response_json: Dict[Any, Any], duration: float, text_length: int) -> None:
        """Log response details in a clean format."""
        logger.debug("\nLLM Response:")
        logger.debug(f"Duration: {duration:.2f}s")
        logger.debug(f"Response length: {text_length} characters")
        
        if 'usage' in response_json:
            usage = response_json['usage']
            logger.debug("Token usage:")
            logger.debug(f"  Prompt: {usage.get('prompt_tokens', 'N/A')}")
            logger.debug(f"  Completion: {usage.get('completion_tokens', 'N/A')}")
            logger.debug(f"  Total: {usage.get('total_tokens', 'N/A')}")
        
        cleaned_response = {
            "model": response_json.get("model"),
            "created_at": response_json.get("created_at"),
            "response": response_json.get("response"),
            "done": response_json.get("done"),
            "done_reason": response_json.get("done_reason")
        }
        logger.debug(f"\nResponse details:\n{self._format_json(cleaned_response)}")
        logger.debug("-" * 80)

    async def generate(self, prompt: str, model: Optional[str] = None) -> str:
        """
        Generate text using local LLM via Ollama.
        
        Args:
            prompt: The input prompt
            model: Optional model override (defaults to instance model)
            
        Returns:
            Generated text response
        """
        try:
            # Log request details
            target_model = model or self.model
            
            if not self.api_url.rstrip('/').endswith('/api'):
                endpoint = f"{self.api_url.rstrip('/')}/api/generate"
            else:
                endpoint = f"{self.api_url.rstrip('/')}/generate"
                
            payload = {
                "model": target_model,
                "prompt": prompt,
                "stream": False,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stop": self.stop_sequences
            }
            
            # Enhanced request logging
            logger.debug("=== LLM Request Details ===")
            logger.debug(f"Full URL: {endpoint}")
            logger.debug(f"API Base URL: {self.api_url}")
            logger.debug(f"Model: {target_model}")
            logger.debug("=== Input Prompt ===")
            logger.debug(prompt)
            logger.debug("=== Request Payload ===")
            logger.debug(json.dumps(payload, indent=2))
            
            # Make the request
            try:
                logger.debug("Sending request to Ollama...")
                response = await self.client.post(
                    endpoint,
                    json=payload,
                    timeout=30.0  # Add explicit timeout
                )
                
                # Log response details immediately
                logger.debug(f"Response status: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                
                # Try to get response content regardless of status
                try:
                    response_content = response.text
                    logger.debug("=== Raw Response Content ===")
                    logger.debug(response_content)
                except Exception as content_error:
                    logger.error(f"Could not read response content: {content_error}")
                
                # Now raise for status if needed
                response.raise_for_status()
                
                # Parse response
                response_json = response.json()
                # Create a clean copy without the context array for logging
                log_response = response_json.copy()
                if 'context' in log_response:
                    log_response['context'] = f"[{len(log_response['context'])} vector values]"
                logger.debug("=== Parsed Response ===")
                logger.debug(json.dumps(log_response, indent=2))
                
                return response_json["response"]
                
            except httpx.TimeoutException:
                error_msg = "Request to Ollama timed out after 30 seconds"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            except httpx.RequestError as e:
                error_msg = f"Request error occurred: {str(e)}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
        except Exception as e:
            error_msg = f"Error generating text: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            raise RuntimeError(error_msg)

    async def get_response(self, 
                         system_prompt: str = "", 
                         conversation_history: List[Message] = None) -> str:
        """
        Get a response from the LLM with conversation history.
        
        Args:
            system_prompt: System prompt to guide the conversation
            conversation_history: List of previous messages
            
        Returns:
            Generated response text
        """
        try:
            # Format messages
            formatted_prompt = await self.format_messages(
                conversation_history or [],
                system_prompt
            )
            
            # Generate response
            response = await self.generate(formatted_prompt)
            return response
            
        except Exception as e:
            error_msg = f"Error getting response: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    async def query_llm(self, prompt: str, stream: bool = False) -> str:
        """
        Query the LLM with a prompt.
        
        Args:
            prompt: Input prompt
            stream: Whether to stream the response
            
        Returns:
            Generated response text
        """
        try:
            if stream:
                # TODO: Implement streaming
                raise NotImplementedError("Streaming not implemented yet")
            else:
                return await self.generate(prompt)
                
        except Exception as e:
            error_msg = f"Error querying LLM: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    async def get_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        Get embeddings for text using the LLM.
        
        Args:
            text: Input text
            model: Optional model override
            
        Returns:
            List of embedding values
        """
        try:
            target_model = model or self.model
            
            if not self.api_url.rstrip('/').endswith('/api'):
                endpoint = f"{self.api_url.rstrip('/')}/api/embeddings"
            else:
                endpoint = f"{self.api_url.rstrip('/')}/embeddings"
                
            payload = {
                "model": target_model,
                "prompt": text
            }
            
            response = await self.client.post(
                endpoint,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            
            response_json = response.json()
            return response_json["embedding"]
            
        except Exception as e:
            error_msg = f"Error getting embedding: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    async def format_messages(self, 
                            messages: List[Message], 
                            system_prompt: Optional[str] = None) -> str:
        """
        Format a list of messages into a prompt string.
        
        Args:
            messages: List of messages to format
            system_prompt: Optional system prompt
            
        Returns:
            Formatted prompt string
        """
        try:
            formatted = []
            
            # Add system prompt if provided
            if system_prompt:
                formatted.append(f"System: {system_prompt}\n")
            
            # Format each message
            for msg in messages:
                if msg.type == MessageType.REQUEST:
                    formatted.append(f"User: {msg.content}\n")
                elif msg.type == MessageType.RESPONSE:
                    formatted.append(f"Assistant: {msg.content}\n")
                    
            return "".join(formatted)
            
        except Exception as e:
            error_msg = f"Error formatting messages: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stop_sequences": self.stop_sequences,
            "api_url": self.api_url
        }

    async def clear_cache(self) -> None:
        """Clear any cached data."""
        # No cache to clear in this implementation
        pass 
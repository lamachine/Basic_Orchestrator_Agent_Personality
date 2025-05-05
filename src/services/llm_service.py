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
from src.config.llm_config import EMBEDDING_MODEL, LLM_MODEL, LLM_PROVIDER, OLLAMA_HOST
import ollama
import uuid
import traceback

# Import OllamaClient for embeddings
from ollama import Client as OllamaClient
from src.services.logging_service import get_logger
from src.tools.orchestrator_tools import format_completed_tools_prompt
from src.state.state_models import MessageRole, TaskStatus, MessageState

logger = get_logger(__name__)

class LLMService:
    """Service for LLM operations."""
    
    _instance: Optional['LLMService'] = None
    _initialized = False
    
    def __new__(cls, api_url: str = "http://localhost:11434/api", model: str = "mistral") -> 'LLMService':
        """Ensure only one instance is created (singleton pattern)."""
        if cls._instance is None:
            logger.debug("Creating new LLMService instance")
            cls._instance = super(LLMService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, api_url: str = "http://localhost:11434/api", model: str = "mistral"):
        """Initialize LLM service (only runs once due to singleton pattern)."""
        if self._initialized:
            logger.debug("LLMService already initialized, skipping initialization")
            return
            
        logger.debug(f"Initializing LLM Service")
        logger.debug(f"API URL: {api_url}")
        logger.debug(f"Model: {model}")
        
        # Check if API URL ends with /api/generate and fix it
        if api_url.endswith('/generate'):
            logger.warning(f"API URL ends with /generate, removing suffix")
            api_url = api_url.rsplit('/generate', 1)[0]
        if api_url.endswith('/api/generate'):
            logger.warning(f"API URL ends with /api/generate, removing suffix")
            api_url = api_url.rsplit('/api/generate', 1)[0]
            
        self.api_url = api_url
        self.model = model
        self.client = httpx.AsyncClient()
        
        logger.debug(f"LLM Service initialized with API URL: {self.api_url}")
        logger.debug("Created async HTTP client")
        self._initialized = True

    @classmethod
    def get_instance(cls, api_url: str = "http://localhost:11434/api", model: str = "mistral") -> 'LLMService':
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls(api_url, model)
        return cls._instance

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
            # Get temperature and context_window from config if available
            from src.config.llm_config import get_llm_config
            llm_config = get_llm_config()
            temperature = getattr(llm_config, 'temperature', 0.1)
            context_window = getattr(llm_config, 'context_window', 16384)
            # Try to get per-model settings if available
            if hasattr(llm_config, 'models') and 'conversation' in llm_config.models:
                conversation_cfg = llm_config.models['conversation']
                temperature = conversation_cfg.get('temperature', temperature)
                context_window = conversation_cfg.get('context_window', context_window)
            if not self.api_url.rstrip('/').endswith('/api'):
                endpoint = f"{self.api_url.rstrip('/')}/api/generate"
            else:
                endpoint = f"{self.api_url.rstrip('/')}/generate"
            payload = {
                "model": target_model,
                "prompt": prompt,
                "stream": False,
                "temperature": temperature,
                "context_window": context_window
            }
            
            # Detailed request logging
            logger.debug("=== LLM Request Details ===")
            logger.debug(f"Full URL: {endpoint}")
            logger.debug(f"API Base URL: {self.api_url}")
            logger.debug(f"Model: {target_model}")
            logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")
            
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
                    logger.debug(f"Raw response content: {response_content}")
                except Exception as content_error:
                    logger.error(f"Could not read response content: {content_error}")
                
                # Now raise for status if needed
                response.raise_for_status()
                
                # Parse response
                response_json = response.json()
                logger.debug(f"Parsed response: {json.dumps(response_json, indent=2)}")
                
                return response_json["response"]
                
            except httpx.TimeoutException:
                error_msg = "Request to Ollama timed out after 30 seconds"
                logger.error(error_msg)
                raise
            except httpx.HTTPError as http_error:
                logger.error(f"HTTP Error occurred: {http_error}")
                logger.error(f"Request URL was: {endpoint}")
                # logger.error("This might indicate Ollama is not running or the endpoint is incorrect")
                # logger.debug("For Ollama, ensure:")
                # logger.debug("1. Ollama is running (try 'ollama list' in terminal)")
                # logger.debug("2. The model is pulled (try 'ollama pull llama3.1')")
                # logger.debug("3. The correct API endpoint is used (should be http://localhost:11434/api)")
                raise
                
        except Exception as e:
            error_msg = f"Error in LLM generation: {str(e)}"
            logger.error(error_msg)
            if isinstance(e, httpx.HTTPError):
                logger.error(f"HTTP Error details: {str(e)}")
            return ""

    async def get_response(self, system_prompt: str = "", conversation_history: List[Dict[str, str]] = None) -> str:
        """
        Get a response from the LLM using a system prompt and conversation history.
        
        Args:
            system_prompt: The system prompt for the LLM
            conversation_history: List of messages in the format [{"role": "user", "content": "..."}]
            
        Returns:
            The LLM's response text
        """
        try:
            prompt = system_prompt
            
            if conversation_history:
                for message in conversation_history:
                    role = message.get("role", "user")
                    content = message.get("content", "")
                    if role == "user":
                        prompt += f"\n\nUser: {content}"
                    elif role == "assistant":
                        prompt += f"\n\nAssistant: {content}"
                    else:
                        prompt += f"\n\n{role.capitalize()}: {content}"
                
                prompt += "\n\nAssistant:"
            
            return await self.generate(prompt)
            
        except Exception as e:
            error_msg = f"Error in get_response: {str(e)}"
            logger.error(error_msg)
            return error_msg

    async def query_llm(self, prompt: str, stream: bool = False) -> str:
        """
        Send a query to the LLM.
        
        Args:
            prompt: The prompt to send
            stream: Whether to stream the response
            
        Returns:
            str: The LLM's response
        """
        logger.debug(f"LLMService.generate: Prompt received:\n{prompt}")
        return await self.generate(prompt)

    async def get_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        Calculate text embedding.
        
        Args:
            text: Text to embed
            model: Optional model override
            
        Returns:
            List[float]: Embedding vector
        """
        request_id = str(uuid.uuid4())
        logger.debug(f"[EMBED] [{request_id}] Embedding request for text: '{text[:50]}'... (len={len(text)}) model={model}")
        try:
            embedding_model = model or os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
            logger.debug(f"[EMBED] [{request_id}] Generating embedding using model: {embedding_model}")
            try:
                if not self.api_url.rstrip('/').endswith('/api'):
                    endpoint = f"{self.api_url.rstrip('/')}/api/embeddings"
                else:
                    endpoint = f"{self.api_url.rstrip('/')}/embeddings"
                logger.debug(f"[EMBED] [{request_id}] Using embeddings endpoint: {endpoint}")
                response = await self.client.post(
                    endpoint,
                    json={
                        "model": embedding_model,
                        "prompt": text
                    }
                )
                logger.debug(f"[EMBED] [{request_id}] Embedding response status: {response.status_code}")
                response.raise_for_status()
                data = response.json()
                if 'embedding' in data:
                    embedding = data['embedding']
                    logger.debug(f"[EMBED] [{request_id}] Successfully generated embedding of length: {len(embedding)}. First 5 values: {embedding[:5]}")
                    return embedding
                else:
                    raise ValueError("No embedding in response")
            except Exception as embed_error:
                logger.error(f"[EMBED] [{request_id}] Error during embedding generation: {embed_error}")
                logger.error(f"[EMBED] [{request_id}] This might indicate the embedding model is not properly loaded")
                logger.error(f"[EMBED] [{request_id}] Stack trace:\n{traceback.format_exc()}")
                logger.debug(f"[EMBED] [{request_id}] Attempting to pull model {embedding_model}...")
                try:
                    if not self.api_url.rstrip('/').endswith('/api'):
                        pull_endpoint = f"{self.api_url.rstrip('/')}/api/pull"
                    else:
                        pull_endpoint = f"{self.api_url.rstrip('/')}/pull"
                    pull_response = await self.client.post(
                        pull_endpoint,
                        json={"name": embedding_model}
                    )
                    logger.debug(f"[EMBED] [{request_id}] Pull response status: {pull_response.status_code}")
                    logger.debug(f"[EMBED] [{request_id}] Pull response content: {pull_response.text}")
                    pull_response.raise_for_status()
                    logger.debug(f"[EMBED] [{request_id}] Successfully pulled {embedding_model}, retrying embedding...")
                    response = await self.client.post(
                        endpoint,
                        json={
                            "model": embedding_model,
                            "prompt": text
                        }
                    )
                    logger.debug(f"[EMBED] [{request_id}] Retry embedding response status: {response.status_code}")
                    response.raise_for_status()
                    data = response.json()
                    if 'embedding' in data:
                        logger.debug(f"[EMBED] [{request_id}] Successfully generated embedding on retry.")
                        return data['embedding']
                    else:
                        logger.error(f"[EMBED] [{request_id}] Invalid embedding response after pull: {data}")
                        raise ValueError("No embedding in response after pull")
                except Exception as pull_error:
                    logger.error(f"[EMBED] [{request_id}] Error pulling model: {pull_error}")
                    logger.error(f"[EMBED] [{request_id}] Pull response content: {getattr(pull_error, 'response', None)}")
                    logger.error(f"[EMBED] [{request_id}] Stack trace (pull):\n{traceback.format_exc()}")
                    raise RuntimeError(f"Failed to pull embedding model {embedding_model}: {pull_error}")
        except Exception as e:
            logger.error(f"[EMBED] [{request_id}] Error calculating embedding: {e}")
            logger.error(f"[EMBED] [{request_id}] Stack trace (outer):\n{traceback.format_exc()}")
            logger.error("Falling back to zero vector and raising exception")
            raise RuntimeError(f"Embedding generation failed: {e}")

    async def format_messages(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> str:
        """
        Format messages for LLM input.
        
        Args:
            messages: List of message dicts with role and content
            system_prompt: Optional system prompt to prepend
            
        Returns:
            str: Formatted prompt string
        """
        try:
            prompt = f"{system_prompt}\n\n" if system_prompt else ""
            
            for message in messages:
                role = message.get("role", "user")
                content = message.get("content", "")
                prompt += f"{role.capitalize()}: {content}\n\n"
                
            prompt += "Assistant:"
            return prompt
            
        except Exception as e:
            logger.error(f"Error formatting messages: {e}")
            raise

if LLM_PROVIDER == 'ollama':
    ollama.host = OLLAMA_HOST
    async def get_ollama_response(messages: list, tools: list = None) -> dict:
        """Get response from Ollama."""
        try:
            return ollama.chat(
                model=LLM_MODEL,
                messages=messages,
                tools=tools,
                options={
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            )
        except Exception as e:
            logger.debug(f"Error from Ollama: {e}")
            return {"message": {"content": f"Error: {str(e)}"}}

async def process_completed_tool(llm_agent, session: MessageState, tool_completion_id: str, request_info: Dict[str, Any]) -> MessageState:
    """Process a completed tool request and generate a response for a session."""
    # Extract the tool name and user input
    tool_name = request_info.get("name", "unknown")
    # Get the original user input that triggered this tool
    user_message = None
    for message in reversed(session.messages):
        if message.role == MessageRole.USER:
            user_message = message.content
            break
    if not user_message:
        user_message = "unknown query"  # Fallback
    # Format a prompt for the completed tool
    prompt = format_completed_tools_prompt(tool_completion_id, user_message)
    # Generate a response using LLM
    logger.debug(f"Generating response for completed tool {tool_name}")
    llm_response = await llm_agent.generate_response(prompt, tool_completion_id=tool_completion_id)
    # Add to session state
    completed_message = f"{llm_response}"
    # Create the assistant message
    await session.add_message(MessageRole.ASSISTANT, completed_message)
    # Update task status
    session.current_task_status = TaskStatus.COMPLETED
    return session 

def get_stats(self) -> Dict[str, Any]:
        """
        Get current LLM usage statistics.
        
        Returns:
            Dict[str, Any]: Current stats
        """
        return {
            "total_requests": self.stats.total_requests,
            "total_tokens": self.stats.total_tokens,
            "total_errors": self.stats.total_errors,
            "last_request": self.stats.last_request,
            "average_latency": self.stats.average_latency,
            "cache_size": len(self.cache)
        }
        
async def clear_cache(self) -> None:
        """Clear the response and embedding cache."""
        async with self.lock:
            self.cache.clear()
            logger.debug("Cleared LLM cache") 
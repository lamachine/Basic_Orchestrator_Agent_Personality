"""
LLM service provider module using local models via Ollama.
"""
from typing import Optional
import os
import httpx

class LLMService:
    """Service for interacting with local Language Models via Ollama."""
    
    def __init__(self):
        """Initialize the LLM service."""
        self.base_url = "http://localhost:11434/api"
        self.client = httpx.AsyncClient()
        
    async def generate(self, prompt: str, model: str = "mistral") -> str:
        """
        Generate text using local LLM via Ollama.
        
        Args:
            prompt: The input prompt
            model: The model to use (default: mistral)
            
        Returns:
            Generated text response
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            print(f"Error in LLM generation: {e}")
            return ""
            
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

_llm_service: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    """
    Get or create the LLM service instance.
    
    Returns:
        LLMService instance
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service 
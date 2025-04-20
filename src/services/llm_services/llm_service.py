import json
import requests
import logging
import time
import os
from typing import Dict, Any, List

# Import OllamaClient for embeddings
from ollama import Client as OllamaClient

class LLMService:
    def __init__(self, api_url: str, model: str):
        self.api_url = api_url
        self.model = model
        self.logger = logging.getLogger(__name__)

    def _format_json(self, data: Dict[Any, Any]) -> str:
        """Format JSON data for logging with consistent indentation."""
        return json.dumps(data, indent=2)

    def _log_request(self, payload: Dict[Any, Any], prompt_length: int) -> None:
        """Log request details in a clean format."""
        self.logger.debug("LLM Request:")
        self.logger.debug(f"Model: {self.model}")
        self.logger.debug(f"Prompt length: {prompt_length} characters")
        self.logger.debug(f"Payload:\n{self._format_json(payload)}")

    def _log_response(self, response_json: Dict[Any, Any], duration: float, text_length: int) -> None:
        """Log response details in a clean format."""
        self.logger.debug("\nLLM Response:")
        self.logger.debug(f"Duration: {duration:.2f}s")
        self.logger.debug(f"Response length: {text_length} characters")
        
        if 'usage' in response_json:
            usage = response_json['usage']
            self.logger.debug("Token usage:")
            self.logger.debug(f"  Prompt: {usage.get('prompt_tokens', 'N/A')}")
            self.logger.debug(f"  Completion: {usage.get('completion_tokens', 'N/A')}")
            self.logger.debug(f"  Total: {usage.get('total_tokens', 'N/A')}")
        
        self.logger.debug(f"\nFull response:\n{self._format_json(response_json)}")
        self.logger.debug("-" * 80)

    def get_response(self, system_prompt: str = "", conversation_history: List[Dict[str, str]] = None) -> str:
        """
        Get a response from the LLM using a system prompt and conversation history.
        
        This is a compatibility method for BaseAgent which expects this format.
        
        Args:
            system_prompt: The system prompt for the LLM
            conversation_history: List of messages in the format [{"role": "user", "content": "..."}]
            
        Returns:
            The LLM's response text
        """
        try:
            # Build a prompt from the system prompt and conversation history
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
                
                # Add a prompt for the assistant to respond
                prompt += "\n\nAssistant:"
            
            # Send the built prompt to the LLM
            return self.query_llm(prompt)
            
        except Exception as e:
            error_msg = f"Error in get_response: {str(e)}"
            self.logger.error(error_msg)
            return error_msg

    def query_llm(self, prompt: str) -> str:
        """Send a query to the LLM via API and return the response."""
        start_time = time.time()
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            self._log_request(payload, len(prompt))
            
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            response_json = response.json()
            response_text = response_json.get('response', 'No response from LLM')
            
            duration = time.time() - start_time
            self._log_response(response_json, duration, len(response_text))
            
            return response_text
        except Exception as e:
            error_msg = f"Error querying LLM: {str(e)}"
            self.logger.error(error_msg)
            return error_msg

    def get_embedding(self, text: str) -> List[float]:
        """
        Calculate the embedding for a given text using Ollama API.
        
        Args:
            text: The text to embed
            
        Returns:
            List[float]: A vector representation of the text
        """
        try:
            # Initialize the Ollama client
            ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
            client = OllamaClient(host=ollama_url)
            
            # Get the model to use for embeddings - use a default if not specified
            model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
            
            # Generate the embedding using the embeddings method
            response = client.embeddings(model=model, prompt=text)
            
            # Extract the embedding vector from the response
            embedding = response.embedding
            
            return embedding
        except Exception as e:
            self.logger.error(f"Error calculating embedding: {e}")
            return [0.0] * 768  # Return zero vector on error with 768 dimensions 
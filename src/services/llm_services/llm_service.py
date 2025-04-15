import json
import requests
import logging
import time
from typing import Dict, Any

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
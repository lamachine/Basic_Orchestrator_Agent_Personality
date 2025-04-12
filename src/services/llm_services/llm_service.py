import json
import requests
import logging
from typing import Dict, Any

class LLMService:
    def __init__(self, api_url: str, model: str):
        self.api_url = api_url
        self.model = model
        self.logger = logging.getLogger(__name__)

    def query_llm(self, prompt: str) -> str:
        """Send a query to the LLM via API and return the response."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            # LLM call via API
            self.logger.info(f"Full payload sent to LLM: {json.dumps(payload)}")
            self.logger.debug(f"Querying LLM model: {self.model}")
            
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            response_json = response.json()
            response_text = response_json.get('response', 'No response from LLM')
            
            self.logger.info(f"Full response received from LLM: {json.dumps(response_json)}")
            self.logger.debug(f"Received response from LLM (length: {len(response_text)})")
            
            return response_text
        except Exception as e:
            error_msg = f"Error querying LLM: {str(e)}"
            self.logger.error(error_msg)
            return error_msg 
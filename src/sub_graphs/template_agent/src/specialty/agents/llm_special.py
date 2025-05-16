"""
LLM Specialization Example - Shows how to customize LLM behavior.

This module demonstrates how to extend the LLM agent with custom behavior.
This is example code showing override points, not meant for production use.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from ...common.agents.llm_agent import LLMAgent
from ...common.state.state_models import MessageRole

class LLMSpecialExample(LLMAgent):
    """Example of LLM agent specialization through overrides."""
    
    async def query_llm_override(self, prompt: str) -> Optional[str]:
        """
        Example: Override LLM query for specific prompts.
        Return None to use default LLM query.
        """
        # Example: Special handling for test prompts
        if prompt.startswith("test:"):
            return "This is a test response from the override"
        return None
        
    async def preprocess_prompt(self, prompt: str) -> str:
        """
        Example: Modify prompt before sending to LLM.
        """
        # Example: Add context prefix
        return f"Context: template agent. Query: {prompt}"
        
    async def postprocess_response(self, response: str) -> str:
        """
        Example: Modify LLM response before returning.
        """
        # Example: Add metadata footer
        return f"{response}\n[Processed by template agent]" 
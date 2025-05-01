"""Configuration module for the application."""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from src.config.llm_config import get_llm_config, LLMConfig
from src.config.user_config import get_user_config, UserConfig

# Load environment variables
load_dotenv(override=True)

# Set up basic logging directly, avoiding circular imports
logger = logging.getLogger(__name__)

# Import will be available after creating user_config.py
try:
    from src.config.user_config import get_user_config
    HAS_USER_CONFIG = True
except ImportError:
    HAS_USER_CONFIG = False
    logger.debug("No user_config.py found. Using default configuration.")

class Configuration:
    """Unified configuration for the orchestrator system."""
    def __init__(self):
        self.llm = get_llm_config()
        self.user_config = get_user_config()
        # Expose personality settings
        personality_cfg = self.user_config.get_personality_config()
        self.personality_enabled = personality_cfg.get('enabled', True)
        self.personality_file_path = personality_cfg.get('file_path', None)
        # Add any other global settings as needed

    @property
    def ollama_api_url(self):
        return self.llm.api_url

    @property
    def ollama_model(self):
        return self.llm.default_model

    @property
    def llm_temperature(self):
        return self.llm.temperature

    @property
    def llm_max_tokens(self):
        return self.llm.max_tokens

    @property
    def llm_context_window(self):
        return self.llm.context_window

    @property
    def llm_models(self):
        return self.llm.models

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration for a specific agent."""
        if self.user_config:
            return self.user_config.get_agent_config(agent_name)
        if agent_name in self.agent_config:
            return self.agent_config[agent_name]
        return {}
        
    def get_model_for_purpose(self, purpose: str) -> Dict[str, Any]:
        """
        Get the appropriate LLM model configuration for a specific purpose.
        
        Args:
            purpose: The purpose of the model (conversation, coding, reasoning, embedding)
            
        Returns:
            Dictionary with model configuration or default settings
        """
        if purpose in self.llm_models:
            # Get the settings for this purpose
            model_config = self.llm_models.get(purpose, {})
            
            # If it's a simple string (backward compatibility), convert to dict
            if isinstance(model_config, str):
                return {
                    'model': model_config,
                    'temperature': self.llm_temperature,
                    'max_tokens': self.llm_max_tokens
                }
            
            return model_config
        
        # Return default configuration
        return {
            'model': self.ollama_model,
            'temperature': self.llm_temperature,
            'max_tokens': self.llm_max_tokens
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_') and k != 'user_config'}
        
    def __repr__(self) -> str:
        """String representation of configuration."""
        # Hide sensitive values
        safe_dict = self.to_dict()
        for key in ['supabase_anon_key', 'supabase_key', 'supabase_service_role_key']:
            if key in safe_dict and safe_dict[key]:
                safe_dict[key] = '***REDACTED***'
        return f"Configuration({safe_dict})"

# Create default configuration
default_config = Configuration() 
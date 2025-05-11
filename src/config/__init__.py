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
        
        # Expose personality settings - with better handling of structure
        try:
            # Get personality config 
            personality_cfg = self.user_config.get_personality_config()
            
            # Check if we have a personalities dict (new format)
            if isinstance(personality_cfg, dict) and 'personalities' in personality_cfg:
                # New format with multiple personalities
                self.personality_enabled = True
                
                # Get the default personality name
                default_name = personality_cfg.get('default_personality')
                
                # Get all personalities
                personalities = personality_cfg.get('personalities', {})
                
                # Find default personality - either by default_name or first enabled one
                if default_name and default_name in personalities:
                    persona = personalities[default_name]
                    self.personality_file_path = persona.get('file_path')
                else:
                    # Find first enabled personality
                    for name, persona in personalities.items():
                        if persona.get('enabled', True):
                            self.personality_file_path = persona.get('file_path')
                            break
            else:
                # Old format - simpler
                self.personality_enabled = personality_cfg.get('enabled', True)
                self.personality_file_path = personality_cfg.get('file_path')
                
            # Debug
            logger.debug(f"Configuration: personality_enabled={self.personality_enabled}")
            logger.debug(f"Configuration: personality_file_path={self.personality_file_path}")
            
        except Exception as e:
            logger.error(f"Error loading personality config: {e}", exc_info=True)
            # Set defaults
            self.personality_enabled = True
            self.personality_file_path = 'src/agents/Character_Ronan_valet_orchestrator.json'
            
        # Add any other global settings as needed

    @property
    def ollama_api_url(self):
        return self.llm['ollama'].api_url if self.llm and 'ollama' in self.llm else None

    @property
    def ollama_model(self):
        return self.llm['ollama'].default_model if self.llm and 'ollama' in self.llm else None

    @property
    def llm_temperature(self):
        return self.llm['ollama'].temperature if self.llm and 'ollama' in self.llm else None

    @property
    def llm_max_tokens(self):
        return self.llm['ollama'].max_tokens if self.llm and 'ollama' in self.llm else None

    @property
    def llm_context_window(self):
        return self.llm['ollama'].context_window if self.llm and 'ollama' in self.llm else None

    @property
    def llm_models(self):
        return self.llm['ollama'].models if self.llm and 'ollama' in self.llm else None

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
        if purpose in self.llm['ollama'].models:
            model_config = self.llm['ollama'].models.get(purpose, {})
            if isinstance(model_config, str):
                return {
                    'model': model_config,
                    'temperature': self.llm['ollama'].temperature,
                    'max_tokens': self.llm['ollama'].max_tokens
                }
            return model_config
        
        # Return default configuration
        return {
            'model': self.llm['ollama'].default_model,
            'temperature': self.llm['ollama'].temperature,
            'max_tokens': self.llm['ollama'].max_tokens
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_') and k != 'user_config'}
        
    def __repr__(self) -> str:
        """String representation of configuration."""
        # Hide sensitive values
        safe_dict = self.to_dict()
        for key in ['anon_key', 'service_role_key']:
            if key in safe_dict and safe_dict[key]:
                safe_dict[key] = '***REDACTED***'
        return f"Configuration({safe_dict})"

# Create default configuration
default_config = Configuration() 
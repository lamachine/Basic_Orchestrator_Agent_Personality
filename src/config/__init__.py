"""Configuration module for the application."""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Import will be available after creating user_config.py
try:
    from src.config.user_config import get_user_config
    HAS_USER_CONFIG = True
except ImportError:
    HAS_USER_CONFIG = False

class Configuration:
    """Base configuration class for the application."""
    def __init__(self, **kwargs):
        # Try to load user config if available
        self.user_config = None
        if HAS_USER_CONFIG:
            try:
                self.user_config = get_user_config()
                print(f"Loaded user configuration from {self.user_config.config_path}")
            except Exception as e:
                print(f"Error loading user configuration: {e}")
                
        # Logging configuration with defaults from user config or env vars
        if self.user_config:
            log_config = self.user_config.get_logging_config()
            self.file_level = kwargs.get('file_level', log_config.get('file_level', os.getenv('FILE_LOG_LEVEL', 'DEBUG')))
            self.console_level = kwargs.get('console_level', log_config.get('console_level', os.getenv('CONSOLE_LOG_LEVEL', 'INFO')))
        else:
            self.file_level = kwargs.get('file_level', os.getenv('FILE_LOG_LEVEL', 'DEBUG'))
            self.console_level = kwargs.get('console_level', os.getenv('CONSOLE_LOG_LEVEL', 'INFO'))
        
        # Database configuration from user config or env vars
        if self.user_config:
            db_config = self.user_config.get_database_config()
            self.supabase_url = kwargs.get('supabase_url', db_config.get('url') or os.getenv('SUPABASE_URL'))
            self.supabase_anon_key = kwargs.get('supabase_anon_key', db_config.get('anon_key') or os.getenv('SUPABASE_ANON_KEY'))
            self.supabase_service_role_key = kwargs.get('supabase_service_role_key', 
                                                      db_config.get('service_role_key') or os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
        else:
            self.supabase_url = kwargs.get('supabase_url', os.getenv('SUPABASE_URL'))
            self.supabase_anon_key = kwargs.get('supabase_anon_key', os.getenv('SUPABASE_ANON_KEY'))
            self.supabase_service_role_key = kwargs.get('supabase_service_role_key', 
                                                      os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
        
        # LLM configuration from user config or env vars
        if self.user_config:
            llm_config = self.user_config.get_llm_config()
            self.ollama_api_url = kwargs.get('ollama_api_url', llm_config.get('api_url') or os.getenv('OLLAMA_API_URL', 'http://localhost:11434'))
            self.ollama_model = kwargs.get('ollama_model', llm_config.get('default_model') or os.getenv('OLLAMA_MODEL', 'llama3.1:latest'))
            
            # Additional LLM settings from user config
            self.llm_temperature = llm_config.get('temperature', 0.7)
            self.llm_max_tokens = llm_config.get('max_tokens', 2048)
            self.llm_context_window = llm_config.get('context_window', 8192)
            
            # Purpose-based model settings
            self.llm_models = llm_config.get('models', {})
        else:
            self.ollama_api_url = kwargs.get('ollama_api_url', os.getenv('OLLAMA_API_URL', 'http://localhost:11434'))
            self.ollama_model = kwargs.get('ollama_model', os.getenv('OLLAMA_MODEL', 'llama3.1:latest'))
            
            # Default values for additional LLM settings
            self.llm_temperature = 0.7
            self.llm_max_tokens = 2048
            self.llm_context_window = 8192
            self.llm_models = {}
        
        # Runtime configuration from user config or env vars
        if self.user_config:
            general_config = self.user_config.get('general') or {}
            self.debug_mode = kwargs.get('debug_mode', general_config.get('debug_mode', False) or os.getenv('DEBUG_MODE', 'False').lower() == 'true')
            self.user_id = general_config.get('user_id', 'developer')
            self.session_timeout_minutes = general_config.get('session_timeout_minutes', 30)
        else:
            self.debug_mode = kwargs.get('debug_mode', os.getenv('DEBUG_MODE', 'False').lower() == 'true')
            self.user_id = 'developer'
            self.session_timeout_minutes = 30
        
        # Agent configuration
        if self.user_config:
            self.agent_config = self.user_config.get('agents') or {}
        else:
            self.agent_config = {}

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
        for key in ['supabase_anon_key', 'supabase_service_role_key']:
            if key in safe_dict and safe_dict[key]:
                safe_dict[key] = '***REDACTED***'
        return f"Configuration({safe_dict})"

# Create default configuration
default_config = Configuration() 
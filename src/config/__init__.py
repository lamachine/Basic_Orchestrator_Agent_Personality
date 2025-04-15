"""Configuration module for the application."""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

class Configuration:
    """Base configuration class for the application."""
    def __init__(self, **kwargs):
        # Logging configuration with defaults
        self.file_level = kwargs.get('file_level', os.getenv('FILE_LOG_LEVEL', 'DEBUG'))
        self.console_level = kwargs.get('console_level', os.getenv('CONSOLE_LOG_LEVEL', 'INFO'))
        
        # Database configuration
        self.supabase_url = kwargs.get('supabase_url', os.getenv('SUPABASE_URL'))
        self.supabase_anon_key = kwargs.get('supabase_anon_key', os.getenv('SUPABASE_ANON_KEY'))
        self.supabase_service_role_key = kwargs.get('supabase_service_role_key', 
                                                   os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
        
        # LLM configuration
        self.ollama_api_url = kwargs.get('ollama_api_url', os.getenv('OLLAMA_API_URL', 'http://localhost:11434'))
        self.ollama_model = kwargs.get('ollama_model', os.getenv('OLLAMA_MODEL', 'llama3.1:latest'))
        
        # Runtime configuration
        self.debug_mode = kwargs.get('debug_mode', os.getenv('DEBUG_MODE', 'False').lower() == 'true')

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        
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
"""
Configuration for the Personal Assistant sub-graph.

This module manages configuration for the personal assistant, including:
- API credentials and endpoints
- Service configurations
- Default settings
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class GoogleConfig:
    """Configuration for Google services."""
    credentials_file: str = os.getenv('GOOGLE_CREDENTIALS_FILE', '')
    token_file: str = os.getenv('GOOGLE_TOKEN_FILE', '')
    scopes: list = None

    def __post_init__(self):
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/tasks',
            'https://www.googleapis.com/auth/calendar'
        ]

@dataclass
class GmailConfig:
    """Configuration for Gmail integration."""
    credentials_path: str = os.getenv('GMAIL_CREDENTIALS_PATH', '')
    token_path: str = os.getenv('GMAIL_TOKEN_PATH', 'token.pickle')
    user_id: str = os.getenv('GMAIL_USER_ID', 'me')
    scopes: list = None
    
    def __post_init__(self):
        """Set default scopes if none provided."""
        if not self.credentials_path:
            # Try to get from Google config if not set directly
            self.credentials_path = os.getenv('GOOGLE_CREDENTIALS_FILE', '')
            if not self.credentials_path:
                self.credentials_path = os.getenv('GOOGLE_CLIENT_SECRET_FILE', '')
                
        if self.scopes is None:
            self.scopes = [
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/gmail.labels',
                'https://www.googleapis.com/auth/gmail.compose'
            ]
            
    def validate(self) -> bool:
        """Validate Gmail configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        if not self.credentials_path:
            return False
            
        if not os.path.exists(self.credentials_path):
            return False
            
        return True

@dataclass
class PersonalAssistantConfig:
    """Main configuration for the Personal Assistant."""
    # Service configurations
    google: GoogleConfig = GoogleConfig()
    
    # Database configuration (inherited from main orchestrator)
    database_url: str = os.getenv('DATABASE_URL', '')
    
    # LLM configuration (inherited from main orchestrator)
    llm_api_url: str = os.getenv('LLM_API_URL', 'http://localhost:11434')
    llm_model: str = os.getenv('LLM_MODEL', 'llama3.1')
    
    # Logging configuration
    log_level: str = os.getenv('PA_LOG_LEVEL', 'DEBUG')
    log_file: str = os.getenv('PA_LOG_FILE', 'personal_assistant.log')
    console_log_level: str = os.getenv('PA_CONSOLE_LOG_LEVEL', 'DEBUG')

    # Gmail configuration
    gmail_enabled: bool = False  # Will be set in __post_init__
    gmail_config: Optional[GmailConfig] = None
    
    def __post_init__(self):
        """Initialize and validate configuration."""
        # Set up logging first
        self._setup_logging()
        
        # Initialize Gmail config
        self.gmail_enabled = os.getenv('GMAIL_ENABLED', 'false').lower() == 'true'
        if self.gmail_enabled:
            self.gmail_config = GmailConfig()
            if not self.gmail_config.validate():
                raise ValueError(
                    "Gmail is enabled but credentials file not found. "
                    "Please set GMAIL_CREDENTIALS_PATH environment variable "
                    "to point to your credentials.json file."
                )

    def _setup_logging(self):
        """Configure logging for personal assistant."""
        from src.config.logging_config import setup_logging
        setup_logging({
            'file_level': self.log_level,
            'console_level': self.console_log_level,
            'log_dir': 'logs',
            'max_log_size_mb': 10,
            'backup_count': 5
        })

    def validate(self) -> bool:
        """
        Validate the configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        # Validate Gmail configuration if enabled
        if self.gmail_enabled:
            if not self.gmail_config or not self.gmail_config.validate():
                return False
            
        # Validate core services
        if not (self.database_url and self.llm_api_url and self.llm_model):
            return False
            
        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dict[str, Any]: Configuration as dictionary
        """
        return {
            'google': {
                'credentials_file': self.google.credentials_file,
                'token_file': self.google.token_file,
                'scopes': self.google.scopes
            },
            'gmail': {
                'credentials_path': self.gmail_config.credentials_path if self.gmail_config else None,
                'token_path': self.gmail_config.token_path if self.gmail_config else None,
                'user_id': self.gmail_config.user_id if self.gmail_config else None,
                'scopes': self.gmail_config.scopes if self.gmail_config else None
            },
            'database_url': self.database_url,
            'llm_api_url': self.llm_api_url,
            'llm_model': self.llm_model,
            'log_level': self.log_level,
            'log_file': self.log_file
        } 
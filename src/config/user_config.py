"""User-editable configuration for the application.

This module loads configuration from a YAML file that can be easily edited
by users (not developers) to configure various aspects of the application:
- Logging levels
- LLM providers and models
- Database connections
- Other runtime parameters
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

# Default configuration file paths to check
DEFAULT_CONFIG_PATHS = [
    './config.yaml',                          # Current directory
    './config/config.yaml',                   # Config subdirectory
    '~/.config/basic_orchestrator/config.yaml',  # User config directory
]

# Default configuration with documentation for each setting
DEFAULT_CONFIG = {
    # Logging configuration
    'logging': {
        'file_level': 'DEBUG',      # Level for file logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        'console_level': 'INFO',    # Level for console output
        'log_dir': './logs',        # Directory for log files
        'max_log_size_mb': 10,      # Maximum size of log files before rotation
        'backup_count': 5,          # Number of backup log files to keep
    },
    
    # LLM configuration
    'llm': {
        'provider': 'ollama',       # Primary LLM provider: ollama, openai, anthropic, etc.
        'api_url': 'http://localhost:11434',  # API endpoint for the provider
        
        # Default model settings (used as fallback)
        'default_model': 'llama3.1:latest',
        'temperature': 0.7,
        'max_tokens': 2048,
        'context_window': 8192,
        
        # Purpose-specific models and settings
        'models': {
            # Conversation model (for chat, general interactions)
            'conversation': {
                'model': 'llama3.1:latest',
                'temperature': 0.7,
                'max_tokens': 2048,
                'system_prompt': 'You are a helpful assistant named Ronan.'
            },
            
            # Coding model (for code generation, analysis)
            'coding': {
                'model': 'codellama:latest',
                'temperature': 0.2,  # Lower temperature for more precise code
                'max_tokens': 4096,  # Larger output for code generation
                'system_prompt': 'You are an expert programming assistant.'
            },
            
            # Reasoning model (for complex problem-solving)
            'reasoning': {
                'model': 'deepseek-r1',
                'temperature': 0.3,  # Lower for more logical outputs
                'max_tokens': 4096,
                'system_prompt': 'You are a logical reasoning assistant that thinks step by step.'
            },
            
            # Vector encoding model (for embeddings)
            'embedding': {
                'model': 'nomic-embed-text',  # For creating vector embeddings
                'dimensions': 768,            # Embedding dimensions
                'normalize': True             # Whether to normalize vectors
            }
        }
    },
    
    # Orchestrator graph configuration
    'orchestrator': {
        'graph_type': 'standard',          # Type of orchestrator graph to use
        'max_recursion_depth': 3,          # Max depth for recursive tool calls
        'max_pending_tasks': 10,           # Maximum number of pending tasks
        'task_timeout_seconds': 300,       # Default timeout for tasks
        'default_thinking_format': 'steps', # Format for thinking steps (steps, tree, none)
    },
    
    # Database configuration
    'database': {
        'provider': 'supabase',     # Database provider: supabase, postgres, etc.
        'url': '',                  # Database URL (leave empty to use env var)
        'anon_key': '',             # Supabase anon key (leave empty to use env var)
        'service_role_key': '',     # Supabase service role key (leave empty to use env var)
    },
    
    # Agent configuration
    'agents': {
        'enabled': ['librarian', 'valet', 'personal_assistant'],  # Enabled agents
        # Agent-specific configuration
        'librarian': {
            'use_web_search': True,
            'max_references': 5,
        },
        'valet': {
            'check_frequency_seconds': 300,  # How often to check for tasks
        },
        'personal_assistant': {
            'default_timezone': 'UTC',
        },
    },
    
    # General settings
    'general': {
        'debug_mode': False,        # Enable debug mode
        'user_id': 'developer',     # Default user ID
        'session_timeout_minutes': 30,  # Session timeout in minutes
    }
}

class UserConfig:
    """User configuration loaded from YAML file with defaults."""
    
    _instance = None  # Singleton instance
    
    @classmethod
    def get_instance(cls):
        """Get or create the singleton instance of UserConfig."""
        if cls._instance is None:
            cls._instance = UserConfig()
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the user configuration.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config_path = self._find_config_file(config_path)
        self.config = self._load_config()
        self.logger = logging.getLogger(__name__)
        
    def _find_config_file(self, config_path: Optional[str] = None) -> Optional[str]:
        """
        Find the configuration file to use.
        
        Args:
            config_path: Optional explicit path to configuration file
            
        Returns:
            Path to configuration file or None if not found
        """
        # Use explicit path if provided
        if config_path and os.path.isfile(config_path):
            return config_path
            
        # Check default paths
        for path in DEFAULT_CONFIG_PATHS:
            expanded_path = os.path.expanduser(path)
            if os.path.isfile(expanded_path):
                return expanded_path
                
        # No config file found
        return None
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file or use defaults.
        
        Returns:
            Configuration dictionary
        """
        config = DEFAULT_CONFIG.copy()
        
        # Attempt to load from file if available
        if self.config_path:
            try:
                with open(self.config_path, 'r') as f:
                    user_config = yaml.safe_load(f)
                    
                # Merge user config with defaults (depth=2)
                if user_config:
                    for section, values in user_config.items():
                        if section in config and isinstance(values, dict):
                            config[section].update(values)
                        else:
                            config[section] = values
                
                print(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                print(f"Error loading configuration from {self.config_path}: {e}")
                print("Using default configuration")
        else:
            print("No configuration file found, using defaults")
            # Create a default configuration file
            self._create_default_config()
            
        return config
    
    def _create_default_config(self):
        """Create a default configuration file with comments."""
        try:
            # Use the first path from DEFAULT_CONFIG_PATHS
            default_path = os.path.expanduser(DEFAULT_CONFIG_PATHS[0])
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(default_path), exist_ok=True)
            
            with open(default_path, 'w') as f:
                # Add a file header with instructions
                f.write("""# User Configuration for Basic Orchestrator Agent Personality
# 
# This file contains user-editable settings for the application.
# Edit the values below to customize the behavior of the system.
# 
# Note: Do not remove any sections, only modify values.
#       Use # to add comments or disable settings.
#
# For more information, see the project documentation.
#
""")
                
                # Dump the configuration with comments
                yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, sort_keys=False)
                
            print(f"Created default configuration file at {default_path}")
            self.config_path = default_path
        except Exception as e:
            print(f"Error creating default configuration file: {e}")
    
    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            section: Configuration section
            key: Optional specific key within section
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        if section not in self.config:
            return default
            
        if key is None:
            return self.config[section]
            
        return self.config[section].get(key, default)
        
    def set(self, section: str, key: str, value: Any) -> bool:
        """
        Set a configuration value and save to file.
        
        Args:
            section: Configuration section
            key: Key within section
            value: New value
            
        Returns:
            True if successful, False otherwise
        """
        # Ensure section exists
        if section not in self.config:
            self.config[section] = {}
            
        # Update value
        self.config[section][key] = value
        
        # Save to file if available
        if self.config_path:
            try:
                with open(self.config_path, 'w') as f:
                    yaml.dump(self.config, f, default_flow_style=False)
                return True
            except Exception as e:
                print(f"Error saving configuration: {e}")
                return False
        
        return False
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Get logging configuration.
        
        Returns:
            Dictionary with logging configuration
        """
        return self.config.get('logging', {})
        
    def get_llm_config(self) -> Dict[str, Any]:
        """
        Get LLM configuration.
        
        Returns:
            Dictionary with LLM configuration
        """
        return self.config.get('llm', {})
        
    def get_database_config(self) -> Dict[str, Any]:
        """
        Get database configuration.
        
        Returns:
            Dictionary with database configuration
        """
        return self.config.get('database', {})
        
    def get_agent_config(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get agent configuration.
        
        Args:
            agent_name: Optional specific agent name
            
        Returns:
            Dictionary with agent configuration
        """
        agents_config = self.config.get('agents', {})
        
        if agent_name:
            return agents_config.get(agent_name, {})
            
        return agents_config
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Complete configuration dictionary
        """
        return self.config.copy()
        
    def __repr__(self) -> str:
        """String representation of configuration with sensitive data redacted."""
        # Create a copy of the config for display
        safe_config = self.to_dict()
        
        # Redact sensitive values
        if 'database' in safe_config:
            db_config = safe_config['database']
            for key in ['anon_key', 'service_role_key', 'password']:
                if key in db_config and db_config[key]:
                    db_config[key] = '***REDACTED***'
                    
        return f"UserConfig(path={self.config_path}, config={safe_config})"

# Helper function to get configuration
def get_user_config() -> UserConfig:
    """
    Get the user configuration singleton.
    
    Returns:
        UserConfig instance
    """
    return UserConfig.get_instance() 
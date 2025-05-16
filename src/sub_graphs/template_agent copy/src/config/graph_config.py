"""
Template Graph Configuration - Manages service-specific and graph-level settings.

This module provides configuration management for template graphs:
1. Inherits base configuration from AllGraphsConfig
2. Manages local service configurations
3. Integrates with parent graph settings
4. Provides validation and type checking

The configuration system allows for:
- Inheritance of core functionality from parent graph
- Local service configuration
- Environment variable overrides
- Configuration validation
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
from src.config.graph_config import AllGraphsConfig, DBConfig, StateConfig, UserConfig
from src.config.llm_config import LLMConfig
from src.config.logging_config import LoggingConfig

@dataclass
class ServiceConfig:
    """Base configuration for services."""
    enabled: bool = False
    credentials_path: str = ""
    token_path: str = ""
    scopes: List[str] = None
    
    def validate(self) -> bool:
        """
        Validate service configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        if not self.enabled:
            return True
            
        if not self.credentials_path:
            return False
            
        if not os.path.exists(self.credentials_path):
            return False
            
        return True

@dataclass
class APIConfig:
    """Configuration for external APIs."""
    base_url: str = os.getenv('API_BASE_URL', '')
    api_key: str = os.getenv('API_KEY', '')
    timeout: int = int(os.getenv('API_TIMEOUT', '30'))
    retry_count: int = int(os.getenv('API_RETRY_COUNT', '3'))
    
    def validate(self) -> bool:
        """
        Validate API configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        if not self.base_url:
            return False
        return True

@dataclass
class TemplateGraphConfig(AllGraphsConfig):
    """
    Configuration for template graph.
    
    Inherits core functionality from AllGraphsConfig and adds
    template-specific configuration.
    """
    # Graph identification
    graph_name: str = "template_graph"
    system_prompt: str = (
        "You are a template agent that can be customized for specific tasks. "
        "You have access to various tools and can coordinate with other agents. "
        "All tool messages must be in JSON tool command format."
    )
    
    # Inherit core configurations
    llm: LLMConfig = field(default_factory=LLMConfig)
    db: DBConfig = field(default_factory=DBConfig)
    state: StateConfig = field(default_factory=StateConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    user: UserConfig = field(default_factory=UserConfig)
    
    # Local service configurations
    api_config: APIConfig = field(default_factory=APIConfig)
    services: Dict[str, ServiceConfig] = field(default_factory=dict)
    
    # Parent graph settings
    parent_graph_name: Optional[str] = os.getenv('PARENT_GRAPH_NAME')
    parent_graph_config: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize and validate configuration."""
        # Initialize services dict if not set
        if not self.services:
            self.services = {}
            
        # Set up logging
        self._setup_logging()
        
        # Load parent config if available
        self._load_parent_config()
        
    def _setup_logging(self):
        """Configure logging for the graph."""
        from src.config.logging_config import setup_logging
        setup_logging({
            'file_level': self.logging.file_level,
            'console_level': self.logging.console_level,
            'log_dir': self.logging.log_dir,
            'max_log_size_mb': 10,
            'backup_count': 5
        })
        
    def _load_parent_config(self):
        """Load configuration from parent graph if available."""
        parent_config_path = os.getenv('PARENT_GRAPH_CONFIG')
        if parent_config_path and os.path.exists(parent_config_path):
            import yaml
            with open(parent_config_path, 'r') as f:
                self.parent_graph_config = yaml.safe_load(f)
                
                # Inherit settings if not set locally
                if not self.llm.api_url and 'llm_api_url' in self.parent_graph_config:
                    self.llm.api_url = self.parent_graph_config['llm_api_url']
                if not self.llm.model and 'llm_model' in self.parent_graph_config:
                    self.llm.model = self.parent_graph_config['llm_model']

    def validate(self) -> bool:
        """
        Validate the configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        # Validate core configurations
        if not super().validate():
            return False
            
        # Validate local services
        if not self.api_config.validate():
            return False
            
        # Validate enabled services
        for service_name, service_config in self.services.items():
            if not service_config.validate():
                return False
                
        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dict[str, Any]: Configuration as dictionary
        """
        config_dict = super().to_dict()
        
        # Add local configurations
        config_dict.update({
            'api': {
                'base_url': self.api_config.base_url,
                'timeout': self.api_config.timeout,
                'retry_count': self.api_config.retry_count
            },
            'services': {
                name: {
                    'enabled': config.enabled,
                    'credentials_path': config.credentials_path,
                    'token_path': config.token_path,
                    'scopes': config.scopes
                }
                for name, config in self.services.items()
            },
            'parent_graph_name': self.parent_graph_name
        })
        
        return config_dict 

def get_template_config(config_path: Optional[str] = None) -> TemplateGraphConfig:
    """
    Get the template agent's configuration.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        TemplateGraphConfig: Loaded configuration
    """
    if config_path is None:
        # Use default config path
        base_dir = Path(__file__).parent.parent.parent
        config_path = str(base_dir / "config" / "config.yaml")
    
    # Create and return configuration
    config = TemplateGraphConfig()
    
    # Load from file if it exists
    if os.path.exists(config_path):
        import yaml
        with open(config_path, 'r') as f:
            file_config = yaml.safe_load(f)
            if file_config:
                # Update configuration with file settings
                for key, value in file_config.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
    
    return config 
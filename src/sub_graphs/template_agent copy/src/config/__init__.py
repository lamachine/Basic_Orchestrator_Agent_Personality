"""
Template Agent Configuration Module.

This module provides access to the template agent's configuration system.
"""

from .graph_config import (
    TemplateGraphConfig,
    ServiceConfig,
    APIConfig,
    get_template_config
)

__all__ = [
    'TemplateGraphConfig',
    'ServiceConfig',
    'APIConfig',
    'get_template_config'
] 
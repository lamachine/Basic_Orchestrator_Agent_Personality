# -*- coding: utf-8 -*-
"""
Template Agent UI Adapters package.

This package contains interface adapters for the template agent.
"""

from .api import APIInterface
from .cli import CLIInterface
from .io_adapter import IOAdapter
from .mcp import MCPAdapter
from .parent_graph import ParentGraphAdapter
from .template_agent import TemplateAgentAdapter

__all__ = [
    'IOAdapter',
    'APIInterface',
    'CLIInterface',
    'TemplateAgentAdapter',
    'ParentGraphAdapter',
    'MCPAdapter',
]

"""
Template Agent Tools Package

This package provides the core tool infrastructure for the template agent.
It includes the base tool class and tool registry implementation.
"""

from .base_tool import BaseTool
from .tool_registry import ToolRegistry, ToolDescription

__all__ = ['BaseTool', 'ToolRegistry', 'ToolDescription'] 
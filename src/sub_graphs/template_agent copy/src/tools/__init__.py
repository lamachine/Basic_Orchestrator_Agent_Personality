"""
Template Agent Tools Module.

This module provides tool functionality for the template agent, including:
- Base tool class for all template tools
- Tool registry for managing tools
- Tool processor for executing tools
- Tool utilities for common operations
"""

from .base_tool import BaseTool
from .tool_registry import ToolRegistry
from .tool_processor import ToolProcessor
from .tool_utils import (
    template_validate_parameters,
    template_format_tool_response,
    template_handle_tool_error,
    template_tool_wrapper
)

__all__ = [
    'BaseTool',
    'ToolRegistry',
    'ToolProcessor',
    'template_validate_parameters',
    'template_format_tool_response',
    'template_handle_tool_error',
    'template_tool_wrapper'
] 
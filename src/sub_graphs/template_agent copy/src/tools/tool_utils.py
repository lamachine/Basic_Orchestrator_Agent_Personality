"""
Template Agent Tool Utilities.

This module provides utility functions for the template agent's tools,
inheriting core functionality from the orchestrator's tool utilities
but adding template-specific helper functions.
"""

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import json
import asyncio
from functools import wraps

from src.tools.tool_utils import (
    execute_tool_with_state,
    format_session_history,
    create_tool_node_func,
    should_use_tool
)
from .template_tool_mods import validate_template_parameters

from ..services.logging_service import get_logger

logger = get_logger(__name__)

def template_validate_parameters(
    parameters: Dict[str, Any],
    required: List[str],
    optional: Optional[List[str]] = None
) -> bool:
    """
    Validate tool parameters with template-specific rules.
    
    Args:
        parameters: Tool parameters to validate
        required: List of required parameter names
        optional: Optional list of optional parameter names
        
    Returns:
        bool: True if parameters are valid
    """
    # Add template-specific validation
    if not validate_template_parameters(parameters, required, optional):
        logger.warning("Base parameter validation failed")
        return False
    
    # Add template-specific parameter validation
    for param in parameters:
        if isinstance(parameters[param], str) and len(parameters[param]) > 1000:
            logger.warning(f"Parameter {param} exceeds maximum length")
            return False
    
    logger.debug("Template parameter validation passed")
    return True

def template_format_tool_response(
    result: Any,
    status: str = "success",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format tool response with template-specific handling.
    
    Args:
        result: Tool execution result
        status: Response status
        metadata: Optional metadata
        
    Returns:
        Dict containing the formatted response
    """
    # Add template-specific metadata
    if metadata is None:
        metadata = {}
    
    metadata["template_timestamp"] = datetime.now().isoformat()
    
    # Format using base utility
    response = base_format_tool_response(
        result,
        status,
        metadata
    )
    
    logger.debug(f"Formatted tool response with status: {status}")
    return response

def template_handle_tool_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Handle tool error with template-specific handling.
    
    Args:
        error: The error to handle
        context: Optional context information
        
    Returns:
        Dict containing the error response
    """
    # Add template-specific context
    if context is None:
        context = {}
    
    context["template_error"] = True
    
    # Handle using base utility
    response = base_handle_tool_error(
        error,
        context
    )
    
    logger.error(f"Handled tool error: {str(error)}")
    return response

def template_tool_wrapper(
    func: Callable
) -> Callable:
    """
    Decorator for template-specific tool handling.
    
    Args:
        func: The function to wrap
        
    Returns:
        Wrapped function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # Add template-specific context
            if "context" in kwargs:
                kwargs["context"] = {
                    **(kwargs.get("context", {})),
                    "template_wrapper": True
                }
            
            # Execute function
            result = await func(*args, **kwargs)
            
            logger.debug(f"Executed tool function: {func.__name__}")
            return result
            
        except Exception as e:
            logger.error(f"Tool function failed: {func.__name__}")
            return template_handle_tool_error(e)
    
    return wrapper 
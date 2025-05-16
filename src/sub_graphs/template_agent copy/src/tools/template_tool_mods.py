"""
Template Tool Modifications.

This module provides template-specific modifications and helpers for tools.
These are meant to be used with the base tool classes from the orchestrator.
"""

from typing import Dict, Any, Optional, List, Callable
import logging
from functools import wraps

from ..services.logging_service import get_logger

logger = get_logger(__name__)

def template_tool_decorator(func: Callable) -> Callable:
    """
    Decorator for template-specific tool functions.
    
    This decorator adds template-specific logging and context handling
    to tool functions.
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Add template context
        context = kwargs.get('context', {})
        context['source'] = 'template'
        
        # Log execution
        logger.debug(f"Executing template tool: {func.__name__}")
        
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"Template tool {func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Template tool {func.__name__} failed: {str(e)}")
            raise
    
    return wrapper

def validate_template_parameters(parameters: Dict[str, Any]) -> List[str]:
    """
    Validate parameters for template tools.
    
    Args:
        parameters: Parameters to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Add template-specific validation rules here
    if 'name' in parameters and not isinstance(parameters['name'], str):
        errors.append("Parameter 'name' must be a string")
    
    if 'description' in parameters and not isinstance(parameters['description'], str):
        errors.append("Parameter 'description' must be a string")
    
    return errors

def format_template_response(response: Any) -> Dict[str, Any]:
    """
    Format tool response for template context.
    
    Args:
        response: Raw tool response
        
    Returns:
        Formatted response
    """
    return {
        'status': 'success',
        'data': response,
        'source': 'template'
    }

def handle_template_error(error: Exception) -> Dict[str, Any]:
    """
    Handle errors in template tools.
    
    Args:
        error: The error that occurred
        
    Returns:
        Error response
    """
    return {
        'status': 'error',
        'error': str(error),
        'source': 'template'
    } 
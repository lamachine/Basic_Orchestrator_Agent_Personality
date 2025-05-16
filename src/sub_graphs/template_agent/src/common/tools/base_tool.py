"""
Base tool class for template agent tools.

This module provides the base class that all template agent tools should inherit from.
Tools in this package should be focused on core functionality that can be shared across
different template agent implementations.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseTool(ABC):
    """Base class for all template agent tools."""
    
    def __init__(self, name: str, description: str):
        """
        Initialize the base tool.
        
        Args:
            name: The name of the tool
            description: A description of what the tool does
        """
        self.name = name
        self.description = description
        
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool's main functionality.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            Dict containing the tool's execution results
        """
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        Validate the parameters passed to the tool.
        
        Args:
            params: Dictionary of parameters to validate
            
        Returns:
            True if parameters are valid, False otherwise
        """
        return True
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get tool metadata.
        
        Returns:
            Dictionary containing tool metadata
        """
        return {
            "name": self.name,
            "description": self.description,
            "type": self.__class__.__name__
        } 
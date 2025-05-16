"""
Template Agent Base Tool.

This module provides the base tool class for the template agent,
inheriting core functionality from the orchestrator's base tool
but adding template-specific tool handling.
"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from src.tools.base_tool import BaseTool as OrchestratorBaseTool

from ..services.logging_service import get_logger

logger = get_logger(__name__)

class BaseTool(OrchestratorBaseTool):
    """
    Template agent base tool.
    
    This class extends the orchestrator's base tool with template-specific
    functionality and validation.
    """
    
    def __init__(self, name: str, description: str):
        """
        Initialize the template tool.
        
        Args:
            name: Tool name
            description: Tool description
        """
        super().__init__(name, description)
        self.source_prefix = "template"
        logger.debug(f"Initialized template tool: {name}")
    
    @abstractmethod
    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute the tool with template-specific handling.
        
        Args:
            parameters: Tool parameters
            context: Optional context information
            
        Returns:
            Dict containing the execution result
        """
        # Add template-specific context
        if context is None:
            context = {}
        
        # Add template-specific metadata
        context["source"] = f"{self.source_prefix}.{self.name}"
        
        # Execute using base tool
        result = await super().execute(parameters, context)
        
        logger.debug(f"Executed template tool {self.name}")
        return result
    
    def validate_parameters(
        self,
        parameters: Dict[str, Any]
    ) -> bool:
        """
        Validate tool parameters with template-specific rules.
        
        Args:
            parameters: Tool parameters to validate
            
        Returns:
            bool: True if parameters are valid
        """
        # Add template-specific validation
        if not super().validate_parameters(parameters):
            logger.warning(f"Parameter validation failed for tool {self.name}")
            return False
        
        logger.debug(f"Validated parameters for tool {self.name}")
        return True 
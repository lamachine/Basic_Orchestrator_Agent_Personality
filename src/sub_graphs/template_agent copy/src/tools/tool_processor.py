"""
Template Agent Tool Processor.

This module provides tool processing for the template agent,
inheriting core functionality from the orchestrator's tool processor
but adding template-specific tool handling and execution.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from src.tools.tool_processor import ToolProcessor as BaseToolProcessor
from .base_tool import BaseTool
from .tool_registry import ToolRegistry
from ..services.logging_service import get_logger

logger = get_logger(__name__)

class ToolProcessor(BaseToolProcessor):
    """
    Template agent tool processor.
    
    This processor extends the base tool processor with template-specific
    tool handling and execution.
    """
    
    def __init__(self, registry: ToolRegistry):
        """
        Initialize the template tool processor.
        
        Args:
            registry: The tool registry to use
        """
        super().__init__(registry)
        self.source_prefix = "template"
        self._tool_executions: List[Dict[str, Any]] = []
        logger.debug("Initialized template tool processor")
    
    async def process_tool_request(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a tool request with template-specific handling.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            context: Optional context information
            
        Returns:
            Dict containing the processing result
        """
        # Add template-specific context
        if context is None:
            context = {}
        
        # Track execution
        execution = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "parameters": parameters,
            "context": context
        }
        
        try:
            # Process using base processor
            result = await super().process_tool_request(
                tool_name,
                parameters,
                {
                    **context,
                    "source": f"{self.source_prefix}.tool_processor"
                }
            )
            
            # Update execution record
            execution["result"] = result
            execution["status"] = "success"
            
            logger.debug(f"Processed tool request for {tool_name}")
            return result
            
        except Exception as e:
            # Update execution record
            execution["result"] = {"error": str(e)}
            execution["status"] = "error"
            
            logger.error(f"Failed to process tool request for {tool_name}: {str(e)}")
            raise
        
        finally:
            # Record execution
            self._tool_executions.append(execution)
    
    def get_tool_executions(
        self,
        tool_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get template-specific tool execution history.
        
        Args:
            tool_name: Optional tool name to filter by
            limit: Optional limit on number of executions to return
            
        Returns:
            List of tool executions
        """
        executions = self._tool_executions
        
        # Filter by tool name if specified
        if tool_name:
            executions = [
                e for e in executions
                if e["tool"] == tool_name
            ]
        
        # Apply limit if specified
        if limit:
            executions = executions[-limit:]
        
        return executions
    
    def clear_tool_executions(
        self,
        tool_name: Optional[str] = None
    ) -> None:
        """
        Clear template-specific tool execution history.
        
        Args:
            tool_name: Optional tool name to clear executions for
        """
        if tool_name:
            self._tool_executions = [
                e for e in self._tool_executions
                if e["tool"] != tool_name
            ]
        else:
            self._tool_executions = []
        
        logger.debug(
            f"Cleared tool executions for "
            f"{tool_name if tool_name else 'all tools'}"
        ) 
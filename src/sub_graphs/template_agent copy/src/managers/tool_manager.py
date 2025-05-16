"""
Template Agent Tool Manager.

This manager handles tool execution for the template agent,
inheriting core functionality from the orchestrator's tool manager
but adding template-specific tool handling and validation.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from src.managers.tool_manager import ToolManager as BaseToolManager
from src.state.state_models import MessageRole
from ..services.logging_service import get_logger

logger = get_logger(__name__)

class ToolManager(BaseToolManager):
    """
    Template agent tool manager.
    
    This manager extends the base tool manager with template-specific
    tool handling and validation.
    """
    
    def __init__(self):
        """Initialize the template tool manager."""
        super().__init__()
        self.source_prefix = "template"
        self._tool_executions: List[Dict[str, Any]] = []
        logger.debug("Initialized template tool manager")
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool with template-specific handling.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            context: Optional context information
            
        Returns:
            Dict containing the tool execution result
        """
        # Add template-specific context
        if context is None:
            context = {}
        
        # Validate tool access
        if not self._validate_tool_access(tool_name):
            logger.warning(f"Tool {tool_name} not accessible to template agent")
            return {
                "status": "error",
                "message": f"Tool {tool_name} not accessible to template agent"
            }
        
        # Execute tool using base manager
        result = await super().execute_tool(
            tool_name,
            parameters,
            {
                **context,
                "source": f"{self.source_prefix}.tool_manager"
            }
        )
        
        # Track execution
        self._tool_executions.append({
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "parameters": parameters,
            "result": result,
            "context": context
        })
        
        logger.debug(f"Executed tool {tool_name}: {result.get('status')}")
        return result
    
    def _validate_tool_access(self, tool_name: str) -> bool:
        """
        Validate if the template agent has access to a tool.
        
        Args:
            tool_name: Name of the tool to validate
            
        Returns:
            bool: True if tool is accessible
        """
        # Get template-specific tool configuration
        tool_config = self.config.get("tools", {}).get(tool_name, {})
        
        # Check if tool is enabled for template agent
        return tool_config.get("enabled", False)
    
    def get_tool_executions(
        self,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get template-specific tool execution history.
        
        Args:
            limit: Optional limit on number of executions to return
            
        Returns:
            List of tool executions
        """
        if limit is None:
            return self._tool_executions
        return self._tool_executions[-limit:]
    
    def clear_tool_executions(self) -> None:
        """Clear the template-specific tool execution history."""
        self._tool_executions = []
        logger.debug("Cleared template tool execution history") 
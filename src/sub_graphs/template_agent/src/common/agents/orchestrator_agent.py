"""
Orchestrator Agent - Extends LLM agent with orchestration capabilities.

This module provides the OrchestratorAgent class which adds orchestration features:
1. Tool management and routing
2. Request preprocessing
3. Task coordination
4. State tracking

Override points are provided for specialization:
- route_request_override: Custom routing logic
- preprocess_request: Request modification before routing
- postprocess_response: Response modification after routing
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..state.state_models import MessageRole
from .llm_agent import LLMAgent


class OrchestratorAgent(LLMAgent):
    """Agent with orchestration capabilities."""

    async def route_request(
        self, request: Dict[str, Any], tool_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Core request routing implementation.

        Args:
            request: The request to route
            tool_name: Optional specific tool to use

        Returns:
            Dict[str, Any]: Tool response
        """
        try:
            # Check for override
            override_response = await self.route_request_override(request, tool_name)
            if override_response is not None:
                return override_response

            # Log routing attempt if logging enabled
            if self.config.get("enable_logging", True):
                await self._log_routing_attempt(request, tool_name)

            # Preprocess request
            request = await self.preprocess_request(request)

            # Get available tools
            tools = await self.tool_registry.get_tools()

            if not tools:
                return {"status": "error", "message": "No tools available"}

            if tool_name and tool_name not in tools:
                return {"status": "error", "message": f"Tool {tool_name} not found"}

            # Execute tool
            tool = tools[tool_name] if tool_name else tools[list(tools.keys())[0]]
            response = await tool.execute(**request)

            # Postprocess response
            return await self.postprocess_response(response)

        except Exception as e:
            self.logger.error(f"Error routing request: {e}")
            return {"status": "error", "message": str(e)}

    async def route_request_override(
        self, request: Dict[str, Any], tool_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Override point for custom routing logic.
        Return None to use default routing.

        Args:
            request: The request to route
            tool_name: Optional specific tool to use

        Returns:
            Optional[Dict[str, Any]]: Custom response or None
        """
        return None

    async def preprocess_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Override point for request preprocessing.

        Args:
            request: The request to preprocess

        Returns:
            Dict[str, Any]: Modified request
        """
        return request

    async def postprocess_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Override point for response postprocessing.

        Args:
            response: The response to postprocess

        Returns:
            Dict[str, Any]: Modified response
        """
        return response

    async def _log_routing_attempt(self, request: Dict[str, Any], tool_name: Optional[str]) -> None:
        """Log a routing attempt."""
        if hasattr(self, "graph_state") and "conversation_state" in self.graph_state:
            await self.graph_state["conversation_state"].add_message(
                role=MessageRole.SYSTEM,
                content=f"Routing request to {'specified tool: ' + tool_name if tool_name else 'default tool'}",
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "message_type": "routing",
                    "request": request,
                    "tool_name": tool_name,
                },
                sender=f"{self.config.get('graph_name', 'unknown')}.{self.name}",
                target=f"{self.config.get('graph_name', 'unknown')}.tools",
            )

    async def get_available_tools(self) -> List[str]:
        """Get list of available tools."""
        try:
            tools = await self.tool_registry.get_tools()
            return list(tools.keys())
        except Exception as e:
            self.logger.error(f"Error getting tools: {e}")
            return []

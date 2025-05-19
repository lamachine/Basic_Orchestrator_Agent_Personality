"""
Template Agent - Base implementation for graph agents.

This module provides a base template agent that can be used as a starting point
for implementing new graph agents. It extends the orchestrator agent with
common functionality and provides override points for customization.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from ..messages.message_models import Message, MessageStatus, MessageType
from .orchestrator_agent import OrchestratorAgent


class TemplateAgent(OrchestratorAgent):
    """Base template agent implementation."""

    async def route_request_override(
        self, request: Dict[str, Any], tool_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Override routing for specific request types.
        Return None to use default routing.

        Args:
            request: The request to route
            tool_name: Optional specific tool to route to

        Returns:
            Optional[Dict[str, Any]]: Response if handled, None to use default routing
        """
        # Example: Special handling for "test" requests
        if request.get("type") == "test":
            return {
                "status": "success",
                "message": "Test request handled by override",
                "data": request,
            }
        return None

    async def preprocess_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add metadata to requests before routing.

        Args:
            request: The request to preprocess

        Returns:
            Dict[str, Any]: The preprocessed request
        """
        # Add processing timestamp
        request["metadata"] = request.get("metadata", {})
        request["metadata"]["processed_at"] = datetime.now().isoformat()
        return request

    async def postprocess_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Modify response before returning to caller.

        Args:
            response: The response to postprocess

        Returns:
            Dict[str, Any]: The postprocessed response
        """
        # Add processing metadata
        response["metadata"] = response.get("metadata", {})
        response["metadata"]["template_processed"] = True
        return response

    async def create_message(self, content: str, type: MessageType, **kwargs) -> Message:
        """
        Override message creation to add template-specific metadata.

        Args:
            content: The message content
            type: The message type
            **kwargs: Additional message parameters

        Returns:
            Message: The created message
        """
        message = await super().create_message(content, type, **kwargs)
        message.metadata.update({"template_specific": True, "template_version": "1.0"})
        return message

    async def update_message_status(
        self, message: Message, new_status: MessageStatus, **kwargs
    ) -> Message:
        """
        Override status updates to add template-specific handling.

        Args:
            message: The message to update
            new_status: The new status
            **kwargs: Additional update parameters

        Returns:
            Message: The updated message
        """
        # Add template-specific status handling
        if new_status == MessageStatus.RUNNING:
            message.metadata["template_started_at"] = datetime.now().isoformat()
        elif new_status == MessageStatus.COMPLETED:
            message.metadata["template_completed_at"] = datetime.now().isoformat()

        return await super().update_message_status(message, new_status, **kwargs)

    async def route_request(
        self, request: Dict[str, Any], tool_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Override route_request to add template-specific routing logic.

        Args:
            request: The request to route
            tool_name: Optional specific tool to route to

        Returns:
            Dict[str, Any]: The routed response
        """
        # Add template-specific request processing
        request["metadata"] = request.get("metadata", {})
        request["metadata"]["template_processed"] = True

        # Call parent implementation with modified request
        return await super().route_request(request, tool_name)

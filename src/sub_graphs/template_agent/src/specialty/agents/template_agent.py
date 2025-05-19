"""
Template Agent Example - Example of agent specialization through overrides.

This module demonstrates how to extend the base agent classes by overriding
specific methods. This is just example code showing the override points,
not meant for production use.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from ...common.agents.orchestrator_agent import OrchestratorAgent
from ...common.messages.message_models import Message, MessageStatus, MessageType


class TemplateAgentExample(OrchestratorAgent):
    """Example of agent specialization through overrides."""

    async def route_request_override(
        self, request: Dict[str, Any], tool_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Example: Override routing for specific request types.
        Return None to use default routing.

        This shows how to intercept and handle specific request types before
        they reach the default routing logic.
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
        Example: Add metadata to requests before routing.

        This shows how to modify requests before they are processed
        by the main routing logic.
        """
        # Example: Add processing timestamp
        request["metadata"] = request.get("metadata", {})
        request["metadata"]["processed_at"] = datetime.now().isoformat()
        return request

    async def postprocess_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Example: Modify response before returning to caller.

        This shows how to modify responses after they are generated
        but before they are returned to the caller.
        """
        # Example: Add processing metadata
        response["metadata"] = response.get("metadata", {})
        response["metadata"]["template_processed"] = True
        return response

    async def create_message(self, content: str, type: MessageType, **kwargs) -> Message:
        """
        Example: Override message creation to add template-specific metadata.

        This shows how to customize message creation while still using
        the base message model.
        """
        message = await super().create_message(content, type, **kwargs)
        message.metadata.update({"template_specific": True, "template_version": "1.0"})
        return message

    async def update_message_status(
        self, message: Message, new_status: MessageStatus, **kwargs
    ) -> Message:
        """
        Example: Override status updates to add template-specific handling.

        This shows how to customize status update behavior while still
        using the base status update logic.
        """
        # Example: Add template-specific status handling
        if new_status == MessageStatus.RUNNING:
            message.metadata["template_started_at"] = datetime.now().isoformat()
        elif new_status == MessageStatus.COMPLETED:
            message.metadata["template_completed_at"] = datetime.now().isoformat()

        return await super().update_message_status(message, new_status, **kwargs)

    async def route_request(
        self, request: Dict[str, Any], tool_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Example: Override route_request to add template-specific routing logic.

        This shows how to customize the routing behavior while still
        using the base routing logic.
        """
        # Example: Add template-specific request processing
        request["metadata"] = request.get("metadata", {})
        request["metadata"]["template_processed"] = True

        # Call parent implementation with modified request
        return await super().route_request(request, tool_name)

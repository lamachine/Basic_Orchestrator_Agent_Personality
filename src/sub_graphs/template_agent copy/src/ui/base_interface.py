"""
Template Agent Base Interface.

This module provides the base interface implementation for the template agent,
inheriting core functionality from the orchestrator's base interface
but adding template-specific message handling.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from src.ui.base_interface import BaseUserInterface as OrchestratorBaseInterface
from src.ui.base_interface import MessageFormat as BaseMessageFormat
from ..services.logging_service import get_logger

logger = get_logger(__name__)

class MessageFormat(BaseMessageFormat):
    """Template agent message format implementation."""
    
    @staticmethod
    def create_request(method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a template agent request message."""
        request = BaseMessageFormat.create_request(method, params)
        request["source"] = "template"
        logger.debug(f"Created template request message: {request}")
        return request
    
    @staticmethod
    def create_response(request_id: str, result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a template agent response message."""
        response = BaseMessageFormat.create_response(request_id, result)
        response["source"] = "template"
        logger.debug(f"Created template response message: {response}")
        return response
    
    @staticmethod
    def create_error(request_id: str, code: int, message: str, data: Optional[Any] = None) -> Dict[str, Any]:
        """Create a template agent error message."""
        error = BaseMessageFormat.create_error(request_id, code, message, data)
        error["source"] = "template"
        logger.debug(f"Created template error message: {error}")
        return error

class BaseUserInterface(OrchestratorBaseInterface):
    """
    Template agent base interface.
    
    This class extends the orchestrator's base interface with template-specific
    message handling and UI functionality.
    """
    
    def __init__(self, agent):
        """Initialize the template interface."""
        super().__init__(agent)
        self.source_prefix = "template"
        logger.debug("Initialized template interface")
    
    def _process_user_input(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process user input through the template agent."""
        try:
            logger.debug(f"Processing template user input: {user_input}")
            request_id = user_input.get("id")
            
            # Extract the actual input from the message
            input_text = user_input.get("params", {}).get("message", "")
            logger.debug(f"Extracted template input text: {input_text}")
            
            # Add template-specific context
            context = {
                "source": f"{self.source_prefix}.interface",
                "session_id": self.session_id,
                "session_name": self.session_name
            }
            
            # Process through template agent
            logger.debug("Sending input to template agent for processing")
            agent_response = self.agent.chat(input_text, context=context)
            logger.debug(f"Received template agent response: {agent_response}")
            
            # Format response
            response = MessageFormat.create_response(
                request_id=request_id,
                result={
                    "response": agent_response.get("response", str(agent_response)),
                    "status": agent_response.get("status", "success"),
                    "source": self.source_prefix
                }
            )
            logger.debug(f"Formatted template response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing template input: {e}")
            error = MessageFormat.create_error(
                request_id=user_input.get("id", "unknown"),
                code=-32000,
                message=f"Error processing template input: {str(e)}"
            )
            logger.debug(f"Created template error response: {error}")
            return error 
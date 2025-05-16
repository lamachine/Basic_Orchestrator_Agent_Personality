"""
Template Agent IO Adapter.

This module provides the IO adapter implementation for the template agent,
inheriting core functionality from the orchestrator's IO adapter
but adding template-specific input/output handling.
"""

import json
import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

from src.ui.adapters.io_adapter import IOAdapter as BaseIOAdapter
from ..base_interface import MessageFormat
from ...services.logging_service import get_logger

logger = get_logger(__name__)

class IOAdapter(BaseIOAdapter):
    """
    Template agent IO adapter.
    
    This adapter extends the base IO adapter with template-specific
    input/output handling and message routing.
    """
    
    def __init__(self):
        """Initialize the template IO adapter."""
        super().__init__()
        self.source_prefix = "template"
        self._message_handlers: Dict[str, List[Callable]] = {
            "template": [],
            "orchestrator": []
        }
        logger.debug("Initialized template IO adapter")
    
    async def send_message(
        self,
        message: Dict[str, Any],
        target: Optional[str] = None
    ) -> None:
        """
        Send a message with template-specific handling.
        
        Args:
            message: Message to send
            target: Optional target identifier
        """
        # Add template-specific metadata
        if "source" not in message:
            message["source"] = self.source_prefix
        
        # Add timestamp
        message["timestamp"] = datetime.now().isoformat()
        
        # Determine target
        if target is None:
            target = "orchestrator" if message.get("source") == self.source_prefix else self.source_prefix
        
        logger.debug(f"Sending template message to {target}: {message}")
        
        # Route message
        if target == "orchestrator":
            # Send to orchestrator
            await super().send_message(message, target)
        else:
            # Handle locally
            await self._handle_message(message)
    
    async def _handle_message(
        self,
        message: Dict[str, Any]
    ) -> None:
        """
        Handle a message with template-specific processing.
        
        Args:
            message: Message to handle
        """
        source = message.get("source", self.source_prefix)
        logger.debug(f"Handling template message from {source}: {message}")
        
        # Get handlers for source
        handlers = self._message_handlers.get(source, [])
        
        # Call handlers
        for handler in handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Error in template message handler: {e}")
    
    def register_handler(
        self,
        source: str,
        handler: Callable
    ) -> None:
        """
        Register a message handler with template-specific validation.
        
        Args:
            source: Source identifier
            handler: Handler function
        """
        if source not in self._message_handlers:
            self._message_handlers[source] = []
        
        self._message_handlers[source].append(handler)
        logger.debug(f"Registered template handler for {source}")
    
    def unregister_handler(
        self,
        source: str,
        handler: Callable
    ) -> None:
        """
        Unregister a message handler.
        
        Args:
            source: Source identifier
            handler: Handler function to remove
        """
        if source in self._message_handlers:
            self._message_handlers[source].remove(handler)
            logger.debug(f"Unregistered template handler for {source}")
    
    async def process_input(
        self,
        input_data: str
    ) -> Dict[str, Any]:
        """
        Process input with template-specific handling.
        
        Args:
            input_data: Input data to process
            
        Returns:
            Dict containing the processed input
        """
        try:
            # Parse input
            if isinstance(input_data, str):
                try:
                    input_data = json.loads(input_data)
                except json.JSONDecodeError:
                    input_data = {"message": input_data}
            
            # Create request
            request = MessageFormat.create_request(
                method="chat",
                params=input_data
            )
            
            logger.debug(f"Processed template input: {request}")
            return request
            
        except Exception as e:
            logger.error(f"Error processing template input: {e}")
            return MessageFormat.create_error(
                request_id="unknown",
                code=-32000,
                message=f"Error processing template input: {str(e)}"
            )
    
    async def format_output(
        self,
        output_data: Dict[str, Any]
    ) -> str:
        """
        Format output with template-specific handling.
        
        Args:
            output_data: Output data to format
            
        Returns:
            Formatted output string
        """
        try:
            # Add template-specific metadata
            if "source" not in output_data:
                output_data["source"] = self.source_prefix
            
            # Format as JSON
            output = json.dumps(output_data, indent=2)
            
            logger.debug(f"Formatted template output: {output}")
            return output
            
        except Exception as e:
            logger.error(f"Error formatting template output: {e}")
            return json.dumps({
                "error": {
                    "code": -32000,
                    "message": f"Error formatting template output: {str(e)}"
                }
            }) 
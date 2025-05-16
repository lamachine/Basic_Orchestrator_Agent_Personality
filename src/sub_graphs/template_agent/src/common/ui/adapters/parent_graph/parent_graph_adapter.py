"""
Parent graph adapter implementation for template agent.

This module provides the parent graph adapter implementation for the template agent.
It handles communication between the template agent and its parent graph.
"""

from typing import Dict, Any, Optional, List, Set
import logging
import asyncio
import json
import uuid
import time
from datetime import datetime
import os

from ..base_interface import BaseInterface
from ..state.state_models import Message, MessageRole, MessageType, MessageStatus
from src.sub_graphs.template_agent.src.common.services.logging_service import get_logger

logger = get_logger(__name__)

# Dictionary to store pending sub-graph requests
PENDING_SUBGRAPH_REQUESTS = {}

class ParentGraphAdapter(BaseInterface):
    """Parent graph adapter for template agent communication."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the parent graph adapter.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.running = False
        self.tool_check_interval = 0.5  # Check every 500ms
        self.displayed_tools: Set[str] = set()  # Track displayed tool results
        self._tool_checker_task = None
        self._setup_parent_graph()
    
    def _setup_parent_graph(self):
        """Set up parent graph connection and configuration."""
        try:
            # Initialize parent graph configuration
            self.config = {
                "parent_graph_id": os.getenv("PARENT_GRAPH_ID", "orchestrator"),
                "sub_graph_id": os.getenv("SUB_GRAPH_ID", "template_agent"),
                "message_queue": asyncio.Queue(),  # Queue for message passing
                "timeout": 30  # Default timeout in seconds
            }
            logger.debug("Setting up parent graph connection")
            self.running = True
        except Exception as e:
            logger.error(f"Error setting up parent graph: {e}")
            raise
    
    async def start(self) -> None:
        """Start the parent graph adapter and tool checker."""
        try:
            # Start the tool checker as a background task
            self._tool_checker_task = asyncio.create_task(self._check_tool_completions())
            await self._main_loop()
        finally:
            if self._tool_checker_task:
                self._tool_checker_task.cancel()
                try:
                    await self._tool_checker_task
                except asyncio.CancelledError:
                    pass
    
    def stop(self) -> None:
        """Stop the parent graph adapter."""
        self.running = False
        if self._tool_checker_task:
            self._tool_checker_task.cancel()
    
    async def _check_tool_completions(self) -> None:
        """
        Background task that checks for completed tools and processes their results.
        Uses cooperative multitasking to avoid blocking the main message loop.
        """
        while self.running:
            try:
                # Check for completed sub-graph requests
                for task_id, request in list(PENDING_SUBGRAPH_REQUESTS.items()):
                    if request["status"] == "completed" and task_id not in self.displayed_tools:
                        # Process completed request
                        result = request.get("result", {})
                        error = request.get("error")
                        
                        if error:
                            logger.error(f"Sub-graph request {task_id} failed: {error}")
                        else:
                            logger.debug(f"Sub-graph request {task_id} completed: {result}")
                            
                        # Mark as displayed
                        self.displayed_tools.add(task_id)
                        
                        # If agent has a tool completion handler, call it
                        if hasattr(self.agent, "handle_tool_completion"):
                            await self.agent.handle_tool_completion(task_id, result)
                
                await asyncio.sleep(self.tool_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in tool checker: {e}", exc_info=True)
                await asyncio.sleep(1.0)  # Wait longer on error
    
    async def send_message(self, message: Message) -> bool:
        """
        Send a message to the parent graph.
        
        Args:
            message: Message to send
            
        Returns:
            bool: True if message was sent successfully
        """
        try:
            # Generate task ID for tracking
            task_id = str(uuid.uuid4())
            
            # Initialize pending request
            PENDING_SUBGRAPH_REQUESTS[task_id] = {
                "task_id": task_id,
                "status": "pending",
                "started_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Format message for parent graph
            subgraph_message = {
                "type": "subgraph_message",
                "id": task_id,
                "content": message.content,
                "role": message.role.value,
                "message_type": message.type.value,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "session_id": getattr(self.agent, 'session_id', None),
                    "interface": "parent_graph",
                    "sub_graph_id": self.config["sub_graph_id"],
                    "parent_graph_id": self.config["parent_graph_id"]
                }
            }
            
            # Add message to conversation state if available
            if hasattr(self.agent, 'graph_state') and "conversation_state" in self.agent.graph_state:
                await self.agent.graph_state["conversation_state"].add_message(
                    message.role,
                    message.content,
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "message_type": "parent_graph_message",
                        "session_id": getattr(self.agent, 'session_id', None),
                        "interface": "parent_graph",
                        "sub_graph_id": self.config["sub_graph_id"],
                        "parent_graph_id": self.config["parent_graph_id"]
                    },
                    sender='template_agent',
                    target='parent_graph'
                )
            
            # Send message through queue
            await self.config["message_queue"].put(subgraph_message)
            logger.debug(f"Sent message to parent graph: {subgraph_message}")
            
            return True
        except Exception as e:
            logger.error(f"Error sending message to parent graph: {e}")
            return False
    
    async def receive_message(self) -> Optional[Message]:
        """
        Receive a message from the parent graph.
        
        Returns:
            Optional[Message]: Received message or None if no message available
        """
        try:
            # Check message queue
            if not self.config["message_queue"].empty():
                message_data = await self.config["message_queue"].get()
                
                # Convert to Message object
                message = Message(
                    content=message_data["content"],
                    role=MessageRole(message_data["role"]),
                    type=MessageType(message_data["message_type"]),
                    metadata=message_data["metadata"]
                )
                
                logger.debug(f"Received message from parent graph: {message}")
                return message
                
            return None
        except Exception as e:
            logger.error(f"Error receiving message from parent graph: {e}")
            return None
    
    async def close(self):
        """Close the parent graph connection."""
        try:
            self.stop()
            # Clear message queue
            while not self.config["message_queue"].empty():
                await self.config["message_queue"].get()
            logger.debug("Closing parent graph connection")
        except Exception as e:
            logger.error(f"Error closing parent graph connection: {e}")
    
    def is_connected(self) -> bool:
        """
        Check if the parent graph connection is active.
        
        Returns:
            bool: True if connected
        """
        return self.running
    
    async def _main_loop(self) -> None:
        """Run the main message processing loop."""
        while self.running:
            try:
                message = await self.receive_message()
                if message:
                    await self.process_message(message)
                await asyncio.sleep(0.1)  # Prevent busy waiting
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(1.0)  # Wait longer on error
    
    async def process_message(self, message: Message) -> None:
        """
        Process a received message.
        
        Args:
            message: The message to process
        """
        try:
            # Handle different message types
            if message.type == MessageType.TOOL_REQUEST:
                # Handle tool request from parent
                if hasattr(self.agent, "handle_tool_request"):
                    result = await self.agent.handle_tool_request(message)
                    # Send result back to parent
                    await self.send_message(Message(
                        content=json.dumps(result),
                        role=MessageRole.ASSISTANT,
                        type=MessageType.TOOL_RESPONSE,
                        metadata=message.metadata
                    ))
            elif message.type == MessageType.COMMAND:
                # Handle command from parent
                if hasattr(self.agent, "handle_command"):
                    await self.agent.handle_command(message)
            else:
                # Handle regular message
                logger.debug(f"Processing parent graph message: {message}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}") 
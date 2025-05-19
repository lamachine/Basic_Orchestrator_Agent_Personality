"""
MCP adapter implementation for template agent.

This module provides the MCP adapter implementation for the template agent.
It handles communication between the template agent and MCP-based systems.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union

import aiohttp
import sseclient

from ....services.logging_service import get_logger
from ....state.state_models import Message, MessageRole, MessageStatus, MessageType
from ...base_interface import BaseInterface

logger = get_logger(__name__)

# Dictionary to store pending MCP requests
PENDING_MCP_REQUESTS = {}

# MCP Protocol Constants
MCP_PROTOCOL_VERSION = "2025-03-26"
MCP_ERROR_CODES = {
    -32600: "Invalid Request",
    -32601: "Method not found",
    -32602: "Invalid params",
    -32603: "Internal error",
    -32000: "Server error",
    -32001: "Invalid resource",
    -32002: "Resource not found",
    -32003: "Invalid tool",
    -32004: "Tool not found",
    -32005: "Invalid prompt",
    -32006: "Prompt not found",
}


class MCPAdapter(BaseInterface):
    """MCP adapter for template agent communication."""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the MCP adapter.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.running = False
        self.tool_check_interval = 0.5  # Check every 500ms
        self.displayed_tools: Set[str] = set()  # Track displayed tool results
        self._tool_checker_task = None
        self._sse_client = None
        self._http_session = None
        self._setup_mcp()

    def _setup_mcp(self):
        """Set up MCP connection and configuration."""
        try:
            # Initialize MCP configuration
            self.config = {
                "endpoints": {
                    "sse": os.getenv("MCP_SSE_ENDPOINT", "http://localhost:8080/events"),
                    "http": os.getenv("MCP_HTTP_ENDPOINT", "http://localhost:8080/api"),
                },
                "timeout": 30,  # Default timeout in seconds
                "transport": os.getenv("MCP_TRANSPORT", "sse"),  # Default to SSE transport
                "protocol_version": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "resources": {"listChanged": True},
                    "tools": {"listChanged": True},
                    "prompts": {"listChanged": True},
                    "logging": {"enabled": True},
                },
            }
            logger.debug("Setting up MCP connection")
            self.running = True
        except Exception as e:
            logger.error(f"Error setting up MCP: {e}")
            raise

    async def start(self) -> None:
        """Start the MCP adapter and tool checker."""
        try:
            # Initialize transport
            if self.config["transport"] == "sse":
                await self._setup_sse()
            else:
                await self._setup_stdio()

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

    async def _setup_sse(self):
        """Set up SSE transport."""
        try:
            self._http_session = aiohttp.ClientSession()
            async with self._http_session.get(
                self.config["endpoints"]["sse"],
                headers={
                    "Accept": "text/event-stream, application/json",
                    "Content-Type": "application/json",
                },
            ) as response:
                if response.status != 200:
                    raise Exception(f"SSE connection failed: {response.status}")
                self._sse_client = sseclient.SSEClient(response)
                logger.debug("SSE transport initialized")
        except Exception as e:
            logger.error(f"Error setting up SSE transport: {e}")
            raise

    async def _setup_stdio(self):
        """Set up stdio transport."""
        try:
            # Initialize stdio transport
            logger.debug("Stdio transport initialized")
        except Exception as e:
            logger.error(f"Error setting up stdio transport: {e}")
            raise

    def stop(self) -> None:
        """Stop the MCP adapter."""
        self.running = False
        if self._tool_checker_task:
            self._tool_checker_task.cancel()
        if self._sse_client:
            self._sse_client.close()
        if self._http_session:
            asyncio.create_task(self._http_session.close())

    async def _check_tool_completions(self) -> None:
        """
        Background task that checks for completed tools and processes their results.
        Uses cooperative multitasking to avoid blocking the main message loop.
        """
        while self.running:
            try:
                # Check for completed MCP requests
                for task_id, request in list(PENDING_MCP_REQUESTS.items()):
                    if request["status"] == "completed" and task_id not in self.displayed_tools:
                        # Process completed request
                        result = request.get("result", {})
                        error = request.get("error")

                        if error:
                            logger.error(f"MCP request {task_id} failed: {error}")
                        else:
                            logger.debug(f"MCP request {task_id} completed: {result}")

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
        Send a message through the MCP adapter.

        Args:
            message: Message to send

        Returns:
            bool: True if message was sent successfully
        """
        try:
            # Generate task ID for tracking
            task_id = str(uuid.uuid4())

            # Initialize pending request
            PENDING_MCP_REQUESTS[task_id] = {
                "task_id": task_id,
                "status": "pending",
                "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            # Format message as MCP request
            mcp_request = {
                "jsonrpc": "2.0",
                "id": task_id,
                "method": "message",
                "params": {
                    "content": message.content,
                    "role": message.role.value,
                    "type": message.type.value,
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "message_type": "mcp_message",
                        "session_id": getattr(self.agent, "session_id", None),
                        "interface": "mcp",
                        "protocol_version": self.config["protocol_version"],
                    },
                },
            }

            # Send based on transport type
            if self.config["transport"] == "sse":
                # Send via HTTP POST
                async with self._http_session.post(
                    self.config["endpoints"]["http"],
                    json=mcp_request,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                ) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP request failed: {response.status}")
                    result = await response.json()
                    PENDING_MCP_REQUESTS[task_id]["status"] = "completed"
                    PENDING_MCP_REQUESTS[task_id]["result"] = result
            else:
                # Send via stdio
                print(json.dumps(mcp_request))
                PENDING_MCP_REQUESTS[task_id]["status"] = "pending"

            # Add message to conversation state if available
            if (
                hasattr(self.agent, "graph_state")
                and "conversation_state" in self.agent.graph_state
            ):
                await self.agent.graph_state["conversation_state"].add_message(
                    message.role,
                    message.content,
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "message_type": "mcp_message",
                        "session_id": getattr(self.agent, "session_id", None),
                        "interface": "mcp",
                        "protocol_version": self.config["protocol_version"],
                    },
                    sender="mcp_adapter",
                    target="template_agent",
                )
            return True
        except Exception as e:
            logger.error(f"Error sending message through MCP: {e}")
            return False

    async def receive_message(self) -> Optional[Message]:
        """
        Receive a message through the MCP adapter.

        Returns:
            Optional[Message]: Received message or None if no message available
        """
        try:
            if self.config["transport"] == "sse":
                # Receive via SSE
                for event in self._sse_client.events():
                    try:
                        message_data = json.loads(event.data)
                        # Handle batch messages
                        if isinstance(message_data, list):
                            for msg in message_data:
                                if "method" in msg:  # This is a notification
                                    return self._parse_mcp_message(msg)
                        elif "method" in message_data:  # Single notification
                            return self._parse_mcp_message(message_data)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in SSE event: {event.data}")
                        continue
            else:
                # Receive via stdio
                line = input()
                try:
                    message_data = json.loads(line)
                    # Handle batch messages
                    if isinstance(message_data, list):
                        for msg in message_data:
                            if "method" in msg:  # This is a notification
                                return self._parse_mcp_message(msg)
                    elif "method" in message_data:  # Single notification
                        return self._parse_mcp_message(message_data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in stdio: {line}")

            return None
        except Exception as e:
            logger.error(f"Error receiving message through MCP: {e}")
            return None

    def _parse_mcp_message(self, message_data: Dict[str, Any]) -> Optional[Message]:
        """
        Parse an MCP message into a Message object.

        Args:
            message_data: The MCP message data

        Returns:
            Optional[Message]: Parsed message or None if invalid
        """
        try:
            if "method" in message_data and "params" in message_data:
                return Message(
                    content=message_data["params"]["content"],
                    role=MessageRole(message_data["params"]["role"]),
                    type=MessageType(message_data["params"]["type"]),
                    metadata=message_data["params"]["metadata"],
                )
            return None
        except Exception as e:
            logger.error(f"Error parsing MCP message: {e}")
            return None

    async def close(self):
        """Close the MCP connection."""
        try:
            self.stop()
            logger.debug("Closing MCP connection")
        except Exception as e:
            logger.error(f"Error closing MCP connection: {e}")

    def is_connected(self) -> bool:
        """
        Check if the MCP connection is active.

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
                # Handle tool request
                if hasattr(self.agent, "handle_tool_request"):
                    result = await self.agent.handle_tool_request(message)
                    # Send result back
                    await self.send_message(
                        Message(
                            content=json.dumps(result),
                            role=MessageRole.ASSISTANT,
                            type=MessageType.TOOL_RESPONSE,
                            metadata=message.metadata,
                        )
                    )
            elif message.type == MessageType.COMMAND:
                # Handle command
                if hasattr(self.agent, "handle_command"):
                    await self.agent.handle_command(message)
            else:
                # Handle regular message
                logger.debug(f"Processing MCP message: {message}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")

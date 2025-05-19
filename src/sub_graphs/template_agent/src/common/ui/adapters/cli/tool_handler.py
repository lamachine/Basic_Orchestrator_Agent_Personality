"""Tool handling functionality for CLI."""

import asyncio
import traceback
import uuid
from typing import Any, Dict, Optional, Set

from ....services.logging_service import get_logger
from ....tools.template_tools import check_completed_tool_requests, cleanup_processed_request

logger = get_logger(__name__)


class CLIToolHandler:
    """Handles tool completion checking and display for CLI."""

    def __init__(self, display_handler, agent):
        """Initialize the tool handler."""
        self.display_handler = display_handler
        self.agent = agent
        self.tool_check_interval = 0.5  # Check every 500ms
        self.displayed_tools: Set[str] = set()  # Track displayed tool results
        logger.debug("CLIToolHandler initialized with interval: %s", self.tool_check_interval)

    async def check_tool_completions(self) -> None:
        """Check for completed tool requests and display results."""
        try:
            # logger.debug("Checking for completed tool requests")
            # Check for completed tools
            completed_tools = check_completed_tool_requests()

            if completed_tools:
                logger.debug("Found %d completed tools", len(completed_tools))
                for request_id, completion in completed_tools.items():
                    if (
                        not completion.get("displayed", False)
                        and request_id not in self.displayed_tools
                    ):
                        logger.debug("Processing completion for request %s", request_id)
                        # Format and display the result
                        tool_name = completion.get("name", "Unknown Tool")
                        result = completion.get("response", {})

                        # Display with a clear separator
                        self.display_handler.display_message(
                            {"role": "system", "content": "\n--- Tool Completion ---"}
                        )

                        # Display tool name
                        self.display_handler.display_message(
                            {"role": "system", "content": f"Tool: {tool_name}"}
                        )

                        # Display result message if available
                        if isinstance(result, dict) and "message" in result:
                            self.display_handler.display_message(
                                {
                                    "role": "system",
                                    "content": f"Result: {result['message']}",
                                }
                            )
                        else:
                            self.display_handler.display_message(
                                {"role": "system", "content": f"Result: {result}"}
                            )

                        self.display_handler.display_message(
                            {"role": "system", "content": "--------------------\n"}
                        )

                        # Mark as displayed
                        self.displayed_tools.add(request_id)
                        completion["displayed"] = True
                        logger.debug("Marked request %s as displayed", request_id)

                        # If agent has a tool completion handler, call it
                        if hasattr(self.agent, "handle_tool_completion"):
                            logger.debug("Calling agent's tool completion handler")
                            original_query = completion.get("original_query", "")
                            response = await self.agent.handle_tool_completion(
                                request_id, original_query
                            )
                            if response and response.get("status") == "success":
                                logger.debug("Processing agent's response to tool completion")
                                await self.agent.process_message(response.get("message", ""))
                            else:
                                logger.warning(
                                    "Agent's tool completion handler returned unsuccessful response: %s",
                                    response,
                                )
                        else:
                            logger.debug("Agent has no tool completion handler")

                        # Clean up after agent has processed the request
                        cleanup_processed_request(request_id)
                        self.displayed_tools.discard(request_id)

        except Exception as e:
            logger.error("Error checking tool completions: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            raise

    def check_pending_completions(self) -> None:
        """Check for any pending tool completions that happened while offline."""
        try:
            logger.debug("Checking for pending tool completions from previous sessions")
            completions = check_completed_tool_requests()
            if completions:
                logger.debug(
                    "Found %d pending tool completions from previous sessions",
                    len(completions),
                )
                for request_id, completion in completions.items():
                    try:
                        if not completion.get("processed_by_agent", False):
                            logger.debug(
                                "Processing pending completion for request %s",
                                request_id,
                            )
                            self.display_handler.display_tool_result(
                                {
                                    "request_id": request_id,
                                    "name": completion.get("name", "unknown"),
                                    "response": completion.get("response", {}),
                                }
                            )
                            logger.debug(
                                "Displayed pending completion for request %s",
                                request_id,
                            )
                    except Exception as e:
                        logger.error(
                            "Error processing pending completion %s: %s",
                            request_id,
                            str(e),
                        )
                        logger.error("Traceback: %s", traceback.format_exc())
        except Exception as e:
            logger.error("Error checking pending tool completions: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())

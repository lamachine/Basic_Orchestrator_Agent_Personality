"""Orchestrator Agent - Central coordinator for the agent ecosystem (minimal, no tools, no personality)."""

import asyncio
import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent
from src.agents.personality_agent import PersonalityAgent  # For future use
from src.config import Configuration
from src.services.logging_service import get_logger
from src.services.message_service import log_and_persist_message
from src.state.state_models import MessageRole, MessageState, MessageType
from src.tools.initialize_tools import get_registry
from src.tools.orchestrator_tools import (
    PENDING_TOOL_REQUESTS,
    TOOL_DEFINITIONS,
    add_tools_to_prompt,
    execute_tool,
    format_completed_tools_prompt,
    format_tool_results,
    handle_tool_calls,
)
from src.utils.datetime_utils import get_local_datetime_str

# Initialize logger
logger = get_logger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    Minimal orchestrator agent: coordinates user requests, chats via LLM, and logs interactions.
    Now supports optional personality integration.
    """

    def __init__(self, config: Configuration = None, personality_file: Optional[str] = None):
        """Initialize the Orchestrator Agent."""
        if not config:
            config = Configuration()
        super().__init__(
            name="orchestrator",
            api_url=config.llm["ollama"].api_url,
            model=config.llm["ollama"].default_model,
            config=config,
        )
        self.conversation_history: List[Dict[str, Any]] = []

        # --- Personality integration (without circular reference) ---
        self.personality_agent = None
        self.personality_file = personality_file

        # Add debug logging for personality initialization
        logger.debug(f"OrchestratorAgent.__init__: personality_file={personality_file}")
        logger.debug(
            f"OrchestratorAgent.__init__: personality_enabled={config.personality_enabled}"
        )
        logger.debug(
            f"OrchestratorAgent.__init__: config.personality_file_path={config.personality_file_path}"
        )

        # Load personality directly rather than creating a circular reference
        if personality_file:
            try:
                from src.agents.personality_agent import PersonalityAgent

                # Create a standalone personality agent (not wrapping this agent)
                self.personality_agent = PersonalityAgent(
                    base_agent=None,  # Don't wrap this agent
                    personality_file=personality_file,
                )
                logger.debug(f"Loaded personality from {personality_file}")

                # Verify personality loaded correctly
                if hasattr(self.personality_agent, "personality"):
                    persona_name = self.personality_agent.personality.get("name", "Unknown")
                    logger.debug(f"Loaded personality: {persona_name}")
                else:
                    logger.error("Personality agent initialized but has no personality attribute")
            except Exception as e:
                logger.error(
                    f"Failed to load personality file {personality_file}: {e}",
                    exc_info=True,
                )
                self.personality_agent = None
        else:
            logger.warning("No personality file provided to OrchestratorAgent")

        # Set graph name from config or default
        self.graph_name = getattr(config, "graph_name", "orchestrator_graph")

        # Orchestrator's role description
        self.prompt_section = (
            "You are the orchestrator agent, responsible for:\n"
            "1. Understanding user requests\n"
            "2. Determining which tools to use\n"
            "3. Coordinating tool execution\n"
            "4. Providing clear responses\n\n"
            "You MUST use tools when appropriate and format tool calls correctly."
        )

    async def process_message(
        self, message: str, session_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process an incoming user message (chat only, now with tool support)."""
        logger.debug("--- ORCHESTRATOR: process_message START ---")
        logger.debug(f"[process_message] User message: '{message}'")

        if session_state:
            logger.debug(f"[process_message] Session state keys: {session_state.keys()}")
            if "conversation_state" in session_state:
                logger.debug(
                    f"[process_message] Conversation state type: {type(session_state['conversation_state'])}"
                )
                if not isinstance(session_state["conversation_state"], MessageState):
                    logger.error(
                        f"[process_message] Invalid conversation_state type: {type(session_state['conversation_state'])}"
                    )
                    raise TypeError(
                        f"conversation_state must be MessageState, got {type(session_state['conversation_state'])}"
                    )

        if session_state and "conversation_state" in session_state:
            logger.debug("[process_message] Logging user message")
            try:
                # Get user_id from session state or use default
                user_id = session_state.get("user_id", "developer")
                await log_and_persist_message(
                    session_state["conversation_state"],
                    MessageRole.USER,
                    message,
                    metadata={"user_id": user_id},  # Pass user_id in metadata
                    sender=f"{self.graph_name}.cli",
                    target=f"{self.graph_name}.orchestrator",
                )
                logger.debug("[process_message] Successfully logged user message")
            except Exception as e:
                logger.error(
                    f"[process_message] Failed to log user message: {str(e)}",
                    exc_info=True,
                )
                raise  # Re-raise to handle at a higher level

        # Build prompt in stages
        prompt = await self._create_prompt(message)
        logger.debug(f"[process_message] Base prompt:\n{prompt}")

        if session_state and "conversation_state" in session_state:
            logger.debug("[process_message] Logging system prompt")
            try:
                await log_and_persist_message(
                    session_state["conversation_state"],
                    MessageRole.SYSTEM,
                    prompt,
                    sender=f"{self.graph_name}.orchestrator",
                    target=f"{self.graph_name}.llm",
                )
                logger.debug("[process_message] Successfully logged system prompt")
            except Exception as e:
                logger.error(
                    f"[process_message] Failed to log system prompt: {str(e)}",
                    exc_info=True,
                )
                raise  # Re-raise to handle at a higher level

        logger.debug(f"[process_message] Final prompt to LLM:\n{prompt}")
        response = await self.query_llm(prompt)
        logger.debug(f"[process_message] LLM response: {response}")

        if session_state and "conversation_state" in session_state:
            logger.debug("[process_message] Logging LLM response")
            try:
                # Get character name from personality agent if available
                metadata = {}
                if self.personality_agent and hasattr(self.personality_agent, "personality"):
                    character_name = self.personality_agent.personality.get("name", "Assistant")
                    metadata["character_name"] = character_name
                    logger.debug(
                        f"[process_message] Using character name from personality: {character_name}"
                    )

                await log_and_persist_message(
                    session_state["conversation_state"],
                    MessageRole.ASSISTANT,
                    response,
                    metadata=metadata,
                    sender=f"{self.graph_name}.llm",
                    target=f"{self.graph_name}.orchestrator",
                )
                logger.debug("[process_message] Successfully logged LLM response")
            except Exception as e:
                logger.error(
                    f"[process_message] Failed to log LLM response: {str(e)}",
                    exc_info=True,
                )
                raise  # Re-raise to handle at a higher level

        # Check for tool calls in the LLM response
        tool_call_pattern = r"`\{[^`]+\}`"
        matches = list(re.finditer(tool_call_pattern, response))
        if matches:
            logger.debug("[process_message] Found tool call in response")
            # Only handle the first tool call for now (single tool per message)
            match = matches[0]
            tool_call_json = match.group(0).strip("`")
            try:
                tool_call = json.loads(tool_call_json)
                logger.debug(f"[process_message] Parsed tool call: {tool_call}")
            except json.JSONDecodeError as e:
                logger.error(
                    f"[process_message] Invalid tool call JSON: {tool_call_json} | Error: {e}"
                )
                return {
                    "response": f"Error: Tool call was not valid JSON. Please try again or rephrase your request."
                }

            tool_name = tool_call.get("name")
            args = tool_call.get("args", {})
            # Generate a request_id
            request_id = str(uuid.uuid4())
            args["request_id"] = request_id
            logger.debug(f"[process_message] Generated request_id: {request_id}")

            # Log the tool call
            if session_state and "conversation_state" in session_state:
                logger.debug("[process_message] Logging tool call")
                try:
                    await log_and_persist_message(
                        session_state["conversation_state"],
                        MessageRole.TOOL,
                        f"Tool call: {tool_name} with args: {args}",
                        metadata={
                            "tool": tool_name,
                            "args": args,
                            "request_id": request_id,
                        },
                        sender=f"{self.graph_name}.orchestrator",
                        target=f"{self.graph_name}.{tool_name}",
                    )
                    logger.debug("[process_message] Successfully logged tool call")
                except Exception as e:
                    logger.error(
                        f"[process_message] Failed to log tool call: {str(e)}",
                        exc_info=True,
                    )
                    raise  # Re-raise to handle at a higher level

            # Store the original user query with the request for later use in tool completions
            PENDING_TOOL_REQUESTS[request_id] = PENDING_TOOL_REQUESTS.get(request_id, {})
            PENDING_TOOL_REQUESTS[request_id]["original_query"] = message

            # Schedule the tool call (async, don't await result)
            logger.debug(f"[process_message] Scheduling tool execution: {tool_name}")
            asyncio.create_task(
                execute_tool(tool_name, args, request_id, session_state=session_state)
            )

            # Return pending message to CLI
            pending_msg = f"[Tool: {tool_name}] Your request is being processed asynchronously. Request ID: {request_id}"
            if session_state and "conversation_state" in session_state:
                logger.debug("[process_message] Logging pending message")
                try:
                    await log_and_persist_message(
                        session_state["conversation_state"],
                        MessageRole.ASSISTANT,
                        pending_msg,
                        sender=f"{self.graph_name}.orchestrator",
                        target=f"{self.graph_name}.cli",
                    )
                    logger.debug("[process_message] Successfully logged pending message")
                except Exception as e:
                    logger.error(
                        f"[process_message] Failed to log pending message: {str(e)}",
                        exc_info=True,
                    )
                    raise  # Re-raise to handle at a higher level

            self._update_history(message, pending_msg)
            logger.debug(f"[process_message] Sending async pending response to CLI: {pending_msg}")
            return {"response": pending_msg}

        # If no tool call, normal flow
        # Log: orchestrator -> CLI
        if session_state and "conversation_state" in session_state:
            logger.debug("[process_message] Logging final response")
            try:
                await log_and_persist_message(
                    session_state["conversation_state"],
                    MessageRole.ASSISTANT,
                    response,
                    sender=f"{self.graph_name}.orchestrator",
                    target=f"{self.graph_name}.cli",
                )
                logger.debug("[process_message] Successfully logged final response")
            except Exception as e:
                logger.error(
                    f"[process_message] Failed to log final response: {str(e)}",
                    exc_info=True,
                )
                raise  # Re-raise to handle at a higher level

        self._update_history(message, response)
        logger.debug(f"[process_message] Sending response to CLI: {response}")
        return {"response": response}

    async def _create_prompt(self, message: str) -> str:
        """Create the prompt for the LLM by combining optional features."""
        prompt_parts = []
        logger.debug("orchestrator_agent:_create_prompt: Creating prompt")

        # 1. Time/Location Context
        timezone = "UTC"
        location = "Unknown"
        if self.config is not None:
            user_config = getattr(self.config, "user_config", self.config)
            if hasattr(user_config, "get_timezone") and hasattr(user_config, "get_location"):
                timezone = user_config.get_timezone()
                location = user_config.get_location()
        local_time = get_local_datetime_str(timezone)
        time_info = f"Current local time in {location} ({timezone}): {local_time}"
        prompt_parts.append(time_info)
        logger.debug(f"orchestrator_agent:_create_prompt: Time/Location added: {time_info}")

        # 2. Orchestrator Role
        prompt_parts.append(self.prompt_section)
        logger.debug(
            f"orchestrator_agent:_create_prompt: Orchestrator role added: {self.prompt_section}"
        )

        # 3. Personality (if available)
        if self.personality_agent:
            # Core personality traits
            personality_header = self.personality_agent.create_personality_header()
            prompt_parts.append(personality_header)
            logger.debug(
                f"orchestrator_agent:_create_prompt: Personality core added: {personality_header}"
            )

            # Check if we're in a new conversation (first message)
            is_first_message = len(self.conversation_history) == 0

            # For first message, include more personality context
            if is_first_message:
                # Add some random knowledge and lore for initial context
                personality = self.personality_agent.personality
                knowledge_items = personality.get("knowledge", [])
                lore_items = personality.get("lore", [])

                # Add 2-3 random knowledge items if available
                if knowledge_items:
                    import random

                    num_items = min(3, len(knowledge_items))
                    selected_knowledge = random.sample(knowledge_items, num_items)
                    knowledge_text = "Knowledge: " + " ".join(selected_knowledge)
                    prompt_parts.append(knowledge_text)
                    logger.debug(
                        f"orchestrator_agent:_create_prompt: Added knowledge: {knowledge_text}"
                    )

                # Add 1-2 random lore items if available
                if lore_items:
                    import random

                    num_items = min(2, len(lore_items))
                    selected_lore = random.sample(lore_items, num_items)
                    lore_text = "Lore: " + " ".join(selected_lore)
                    prompt_parts.append(lore_text)
                    logger.debug(f"orchestrator_agent:_create_prompt: Added lore: {lore_text}")

        # 4. Combine base prompt
        base_prompt = "\n\n".join(part for part in prompt_parts if part)

        # 5. Add tool information using add_tools_to_prompt
        prompt_with_tools = await add_tools_to_prompt(base_prompt)
        logger.debug(f"orchestrator_agent:_create_prompt: Tool information added")

        # 6. Conversation History (if available)
        if self.conversation_history:
            history = []
            for msg in self.conversation_history[-3:]:
                user_msg = f"<{msg.get('user_id', 'user')}>: {msg['user']}"
                assistant_msg = f"{msg.get('character_name', 'Assistant')}: {msg['assistant']}"
                history.append(f"{user_msg}\n{assistant_msg}")
            history_text = f"Recent conversation:\n" + "\n".join(history)
            prompt_with_tools += f"\n\n{history_text}"
            logger.debug(
                f"orchestrator_agent:_create_prompt: Conversation history added: {history_text}"
            )

        # 7. User's Message
        user_id = getattr(self, "user_id", "user")
        user_message = f"<{user_id}>: {message}"
        prompt_with_tools += f"\n\n{user_message}"
        logger.debug(f"orchestrator_agent:_create_prompt: User message added: {user_message}")

        # Add separators
        final_prompt = "=== LLM PROMPT ===\n\n" + prompt_with_tools + "\n\n=== END PROMPT ==="
        logger.debug("orchestrator_agent:_create_prompt: Final prompt created with separators")
        return final_prompt

    def _update_history(self, user_message: str, assistant_response: str):
        """Update conversation history."""
        character_name = "Assistant"
        if hasattr(self, "personality_agent") and self.personality_agent:
            character_name = self.personality_agent.get_name()

        self.conversation_history.append(
            {
                "user": user_message,
                "assistant": assistant_response,
                "timestamp": datetime.now().isoformat(),
                "user_id": getattr(self, "user_id", "user"),
                "character_name": character_name,
            }
        )
        # Keep only last 10 messages
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

    async def handle_tool_completion(self, request_id: str, original_query: str) -> Dict[str, Any]:
        """
        Process a completed tool request by generating a response with the results.

        Args:
            request_id: The unique identifier for the tool request
            original_query: The original user query that triggered the tool

        Returns:
            Dict with the response and status
        """
        logger.debug(
            f"[handle_tool_completion] Processing tool completion for request {request_id}"
        )

        try:
            # Get the tool result from PENDING_TOOL_REQUESTS
            if request_id not in PENDING_TOOL_REQUESTS:
                logger.warning(
                    f"[handle_tool_completion] No pending request found for {request_id}"
                )
                return {
                    "response": f"I couldn't find the results for your previous request (ID: {request_id}).",
                    "status": "error",
                }

            # Get tool data and format prompt for LLM
            request_data = PENDING_TOOL_REQUESTS[request_id]
            tool_name = request_data.get("name", "unknown")

            logger.debug(
                f"[handle_tool_completion] Found data for request {request_id}, tool: {tool_name}"
            )

            # Format the tool results into a prompt for the LLM
            prompt = format_completed_tools_prompt(request_id, original_query or "your request")
            logger.debug(f"[handle_tool_completion] Created prompt with tool results")

            # Get LLM response
            logger.debug(f"[handle_tool_completion] Sending tool results to LLM")
            response = await self.query_llm(prompt)
            logger.debug(f"[handle_tool_completion] LLM response: {response}")

            # Log the response if we have a session state
            if self.graph_state and "conversation_state" in self.graph_state:
                logger.debug("[handle_tool_completion] Logging tool result and response")

                # Log the tool result
                await log_and_persist_message(
                    self.graph_state["conversation_state"],
                    MessageRole.TOOL,
                    f"Tool result: {tool_name} returned: {request_data.get('response', {})}",
                    metadata={
                        "tool": tool_name,
                        "result": request_data.get("response", {}),
                        "request_id": request_id,
                    },
                    sender=f"{self.graph_name}.{tool_name}",
                    target=f"{self.graph_name}.orchestrator",
                )

                # Log the LLM's response to tool result
                await log_and_persist_message(
                    self.graph_state["conversation_state"],
                    MessageRole.ASSISTANT,
                    response,
                    metadata={
                        "tool_completion": True,
                        "request_id": request_id,
                        "tool_name": tool_name,
                    },
                    sender=f"{self.graph_name}.orchestrator",
                    target=f"{self.graph_name}.cli",
                )

            # Update conversation history
            self._update_history(f"[Tool result for: {original_query}]", response)

            # Return success response
            logger.debug(f"[handle_tool_completion] Successfully processed tool completion")
            return {"response": response, "status": "success"}

        except Exception as e:
            logger.error(f"[handle_tool_completion] Error: {str(e)}", exc_info=True)
            return {
                "response": f"Error processing tool results: {str(e)}",
                "status": "error",
            }


def orchestrator_node(state) -> Dict[str, Any]:
    return {}


# For direct execution testing
if __name__ == "__main__":
    logger.debug("Testing OrchestratorAgent initialization...")
    orchestrator = OrchestratorAgent()
    logger.debug(f"Orchestrator initialized with model: {orchestrator.model}")
    logger.debug("Try running 'python -m src.run_cli' to start the CLI interface.")

"""Orchestrator Agent - Central coordinator for the agent ecosystem (minimal, no tools, no personality)."""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import re
import json
import uuid

from src.agents.base_agent import BaseAgent
from src.config import Configuration
from src.services.logging_service import get_logger
from src.agents.personality_agent import PersonalityAgent  # For future use
from src.utils.datetime_utils import get_local_datetime_str
from src.tools.orchestrator_tools import initialize_tool_definitions, add_tools_to_prompt, handle_tool_calls, execute_tool
from src.services.message_service import log_and_persist_message
from src.state.state_models import MessageRole
# from src.tools.tool_processor import ToolProcessor  # (stubbed for future use)

# Initialize logger
logger = get_logger(__name__)

class OrchestratorAgent(BaseAgent):
    """
    Minimal orchestrator agent: coordinates user requests, chats via LLM, and logs interactions.
    Now supports optional personality integration.
    """
    
    def __init__(self, config: Configuration, personality_file: Optional[str] = None):
        """Initialize the orchestrator agent.
        
        Args:
            config: System configuration
            personality_file: Optional path to a personality JSON file
        """
        super().__init__(
            name="orchestrator",
            api_url=config.llm.api_url,
            model=config.llm.default_model,
            config=config
        )
        self.conversation_history: List[Dict[str, Any]] = []
        # --- Personality agent wrapping enabled if file provided ---
        self.personality_agent = None
        if personality_file:
            self.personality_agent = PersonalityAgent(
                base_agent=self,
                personality_file=personality_file
            )
        # Set graph name from config or default
        self.graph_name = getattr(config, 'graph_name', 'orchestrator_graph')
    
    async def process_message(self, message: str, session_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process an incoming user message (chat only, now with tool support)."""
        await initialize_tool_definitions()
        if session_state and "conversation_state" in session_state:
            await log_and_persist_message(
                session_state["conversation_state"],
                MessageRole.USER,
                message,
                sender=f"{self.graph_name}.cli",
                target=f"{self.graph_name}.orchestrator"
            )
        prompt = self._create_prompt(message)
        prompt = add_tools_to_prompt(prompt)
        if session_state and "conversation_state" in session_state:
            await log_and_persist_message(
                session_state["conversation_state"],
                MessageRole.SYSTEM,
                prompt,
                sender=f"{self.graph_name}.orchestrator",
                target=f"{self.graph_name}.llm"
            )
        if self.personality_agent:
            prompt = self.personality_agent.inject_personality_into_prompt(prompt)
        logger.debug(f"Prompt to be sent to LLM (after personality/tools):\n{prompt}")
        response = await self.query_llm(prompt)
        if session_state and "conversation_state" in session_state:
            await log_and_persist_message(
                session_state["conversation_state"],
                MessageRole.ASSISTANT,
                response,
                sender=f"{self.graph_name}.llm",
                target=f"{self.graph_name}.orchestrator"
            )
        logger.debug(f"User message: {message}")
        logger.debug(f"LLM response: {response}")
        # Check for tool calls in the LLM response
        tool_call_pattern = r"`\{[^`]+\}`"
        matches = list(re.finditer(tool_call_pattern, response))
        if matches:
            # Only handle the first tool call for now (single tool per message)
            match = matches[0]
            tool_call_json = match.group(0).strip('`')
            tool_call = json.loads(tool_call_json)
            tool_name = tool_call.get("name")
            args = tool_call.get("args", {})
            # Generate a request_id
            request_id = str(uuid.uuid4())
            # Log the tool call
            if session_state and "conversation_state" in session_state:
                await log_and_persist_message(
                    session_state["conversation_state"],
                    MessageRole.TOOL,
                    f"Tool call: {tool_name} with args: {args}",
                    metadata={"tool": tool_name, "args": args, "request_id": request_id},
                    sender=f"{self.graph_name}.orchestrator",
                    target=f"{self.graph_name}.{tool_name}"
                )
            # Schedule the tool call (async, don't await result)
            asyncio.create_task(execute_tool(tool_name, args, request_id, session_state=session_state))
            # Return pending message to CLI
            pending_msg = f"[Tool: {tool_name}] Your request is being processed asynchronously. Request ID: {request_id}"
            if session_state and "conversation_state" in session_state:
                await log_and_persist_message(
                    session_state["conversation_state"],
                    MessageRole.ASSISTANT,
                    pending_msg,
                    sender=f"{self.graph_name}.orchestrator",
                    target=f"{self.graph_name}.cli"
                )
            self._update_history(message, pending_msg)
            logger.debug(f"Sending async pending response to CLI: {pending_msg}")
            return {"response": pending_msg}
        # If no tool call, normal flow
        # Log: orchestrator -> CLI
        if session_state and "conversation_state" in session_state:
            await log_and_persist_message(
                session_state["conversation_state"],
                MessageRole.ASSISTANT,
                response,
                sender=f"{self.graph_name}.orchestrator",
                target=f"{self.graph_name}.cli"
            )
        self._update_history(message, response)
        logger.debug(f"Sending response to CLI: {response}")
        return {"response": response}
    
    def _create_prompt(self, message: str) -> str:
        """Create the prompt for the LLM (with system/personality context)."""
        # Get local time and location from config
        timezone = 'UTC'
        location = 'Unknown'
        if self.config is not None:
            user_config = getattr(self.config, 'user_config', self.config)
            if hasattr(user_config, 'get_timezone') and hasattr(user_config, 'get_location'):
                timezone = user_config.get_timezone()
                location = user_config.get_location()
        local_time = get_local_datetime_str(timezone)
        time_info = f"Current local time in {location} ({timezone}): {local_time}"
        context = ""
        if self.conversation_history:
            history = "\n".join([
                f"User: {msg['user']}\nAssistant: {msg['assistant']}"
                for msg in self.conversation_history[-3:]
            ])
            context += f"\n\nRecent conversation:\n{history}"
        # Add a system prompt for personality injection
        system_prompt = "You are a helpful AI assistant."
        prompt = f"{time_info}\n{system_prompt}\n{context}\n\nUser: {message}\nAssistant:"
        return prompt
    
    def _update_history(self, user_message: str, assistant_response: str):
        """Update conversation history."""
        self.conversation_history.append({
            "user": user_message,
            "assistant": assistant_response,
            "timestamp": datetime.now().isoformat()
        })
        # Keep only last 10 messages
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

    # --- Tool logic stubs for future re-addition ---
    # def _handle_tool_calls(self, ...):
    #     """Stub for tool call handling (to be re-added)."""
    #     pass
    # def _extract_tool_calls(self, ...):
    #     """Stub for tool call extraction (to be re-added)."""
    #     pass
    # def _format_response(self, ...):
    #     """Stub for tool result formatting (to be re-added)."""
    #     pass
    # --- Personality agent logic stub for future re-addition ---
    # def _inject_personality(self, prompt: str) -> str:
    #     """Stub for personality injection (to be re-added)."""
    #     if hasattr(self, 'personality_agent'):
    #         return self.personality_agent.inject_personality_into_prompt(prompt)
    #     return prompt

def orchestrator_node(state) -> Dict[str, Any]:
    return {}

# For direct execution testing
if __name__ == "__main__":
    logger.debug("Testing OrchestratorAgent initialization...")
    orchestrator = OrchestratorAgent()
    logger.debug(f"Orchestrator initialized with model: {orchestrator.model}")
    logger.debug("Try running 'python -m src.run_cli' to start the CLI interface.")
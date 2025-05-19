"""
LLM Agent - Extends base agent with LLM interaction capabilities.

This module provides the LLMAgent class which adds LLM-specific functionality:
1. Chat interface
2. Message logging
3. Conversation history management
4. LLM error handling

Override points are provided for specialization:
- query_llm_override: Custom LLM query handling
- preprocess_prompt: Prompt modification before LLM
- postprocess_response: Response modification after LLM
"""

from datetime import datetime
from typing import Any, Dict, Optional

from ...common.messages.message_models import Message, MessageStatus, MessageType
from ..state.state_models import MessageRole
from .base_agent import BaseAgent


class LLMAgent(BaseAgent):
    """Agent with LLM interaction capabilities."""

    async def query_llm(self, message: Message) -> Message:
        """
        Core LLM query implementation using message format.

        Args:
            message: The input message containing the prompt

        Returns:
            Message: LLM response message
        """
        try:
            # Check for override
            override_response = await self.query_llm_override(message)
            if override_response is not None:
                return override_response

            # Preprocess message
            processed_message = await self.preprocess_prompt(message)
            await self.update_message_status(processed_message, MessageStatus.RUNNING)

            # Get LLM response
            if not self.llm:
                raise Exception("LLM service not initialized")

            response = await self.llm.generate(processed_message.content)

            # Create response message
            response_message = await self.create_message(
                content=response,
                type=MessageType.RESPONSE,
                parent_message=message,
                status=MessageStatus.SUCCESS,
            )

            # Postprocess response
            return await self.postprocess_response(response_message)

        except Exception as e:
            self.logger.error(f"Error in LLM query: {e}")
            return await self.create_message(
                content=str(e),
                type=MessageType.ERROR,
                parent_message=message,
                status=MessageStatus.ERROR,
                error_details={"error": str(e)},
            )

    async def query_llm_override(self, prompt: str) -> Optional[str]:
        """
        Override point for custom LLM query handling.
        Return None to use default LLM query.

        Args:
            prompt: The prompt to process

        Returns:
            Optional[str]: Custom response or None
        """
        return None

    async def preprocess_prompt(self, prompt: str) -> str:
        """
        Override point for prompt preprocessing.

        Args:
            prompt: The prompt to preprocess

        Returns:
            str: Modified prompt
        """
        return prompt

    async def postprocess_response(self, response: str) -> str:
        """
        Override point for response postprocessing.

        Args:
            response: The response to postprocess

        Returns:
            str: Modified response
        """
        return response

    async def chat(self, user_input: str) -> Dict[str, Any]:
        """
        Core chat implementation for LLM-based agents.

        Args:
            user_input: The user's message

        Returns:
            Dict[str, Any]: Response containing status and message
        """
        try:
            # Log that we're sending to LLM if logging enabled
            if (
                self.config.get("enable_logging", True)
                and hasattr(self, "graph_state")
                and "conversation_state" in self.graph_state
            ):
                await self.graph_state["conversation_state"].add_message(
                    role=MessageRole.SYSTEM,
                    content=f"Sending query to LLM",
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "message_type": "llm_query",
                        "model": self.model,
                        "session_id": self.session_id,
                    },
                    sender=f"{self.config.get('graph_name', 'unknown')}.{self.name}",
                    target=f"{self.config.get('graph_name', 'unknown')}.llm",
                )

            # Get response from LLM
            response = await self.query_llm(user_input)

            # Log LLM's response if logging enabled
            if (
                self.config.get("enable_logging", True)
                and hasattr(self, "graph_state")
                and "conversation_state" in self.graph_state
            ):
                await self.graph_state["conversation_state"].add_message(
                    role=MessageRole.ASSISTANT,
                    content=response,
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "message_type": "llm_response",
                        "model": self.model,
                        "session_id": self.session_id,
                    },
                    sender=f"{self.config.get('graph_name', 'unknown')}.llm",
                    target=f"{self.config.get('graph_name', 'unknown')}.{self.name}",
                )

            # Update conversation history if enabled
            if self.conversation_history is not None:
                self.conversation_history.append(
                    {
                        "user": user_input,
                        "assistant": response,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            return {"response": response, "status": "success"}
        except Exception as e:
            self.logger.error(f"Error in chat: {e}")
            return {"response": f"Error: {str(e)}", "status": "error"}

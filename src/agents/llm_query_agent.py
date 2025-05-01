"""
LLM Query Agent Module - Specialized agent for interacting with language models.

This module implements the LLMQueryAgent class, which provides specialized handling
for direct interactions with Large Language Models. As a specialized agent within
the architecture, it focuses exclusively on:

1. LLM Integration - Manages connections to language model providers (e.g., Ollama)
2. Prompt Engineering - Constructs effective prompts from user input, context, and system instructions
3. Response Processing - Parses and validates structured responses from the language model
4. Tool Call Handling - Extracts and validates tool calls from LLM responses
5. Context Management - Maintains conversation context for effective LLM interactions

The LLMQueryAgent extends BaseAgent to leverage common functionality while specializing
in the efficient and effective interaction with language models. It serves as a component
within the larger agent ecosystem, focusing exclusively on LLM interactions rather than
orchestration or specialized tasks.

From the perspective of the OrchestratorAgent, this agent handles all direct interaction
with language models, providing a consistent interface for sending queries and receiving
structured responses that can be further processed by other components in the system.

This separation of concerns allows the LLMQueryAgent to focus exclusively on optimizing
LLM interactions without being concerned with higher-level workflow orchestration or
specialized domain knowledge, which is handled by other components of the system.
"""

from typing import Dict, Any, List, Optional
from src.state.state_models import MessageRole
from src.config import Configuration
from src.agents.base_agent import BaseAgent
from src.tools.orchestrator_tools import (
    add_tools_to_prompt, 
    handle_tool_calls, 
    format_tool_results, 
    PENDING_TOOL_REQUESTS,
    format_completed_tools_prompt
)
from src.tools.initialize_tools import initialize_tool_dependencies
from src.services.logging_service import get_logger
from src.tools.tool_processor import ToolProcessor
from datetime import datetime
logger = get_logger(__name__)

class LLMQueryError(Exception):
    """Exception raised for errors in LLM query operations.
    
    Attributes:
        message -- explanation of the error
        status_code -- HTTP status code if applicable
        response -- raw response from the LLM if available
    """
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Any] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)

class LLMQueryAgent(BaseAgent):
    """Specialized agent for LLM interactions."""
    
    def __init__(self, config: Configuration = None, personality_file: Optional[str] = None):
        """Initialize the LLM Query Agent."""
        if not config:
            config = Configuration()
            
        super().__init__(
            name="llm_query",
            prompt_section="You are a helpful AI assistant that can use tools to assist the user.",
            api_url=config.ollama_api_url,
            model=config.ollama_model,
            config=config
        )
        
        self.tool_executor = ToolProcessor()
        logger.debug(f"Initialized LLM Query Agent with model: {self.model}")

    def generate_prompt(self, user_input: str) -> str:
        """Generate a prompt for the LLM."""
        return f"{self.prompt_section}\n\nUser: {user_input}\n\nAssistant:"

    async def chat(self, user_input: str) -> Dict[str, Any]:
        """Process a user input message and return a response."""
        try:
            # Generate prompt
            prompt = self.generate_prompt(user_input)
            
            # Log sending to LLM
            if hasattr(self, 'graph_state') and "conversation_state" in self.graph_state:
                await self.graph_state["conversation_state"].add_message(
                    role=MessageRole.SYSTEM,
                    content=f"Sending query to LLM",
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "message_type": "llm_query",
                        "model": self.model,
                        "session_id": self.session_id
                    },
                    sender="orchestrator_graph.llm_query",
                    target="orchestrator_graph.llm"
                )
            
            # Get response from LLM
            response = await self.query_llm(prompt)
            
            # Log LLM's response to LLM Query Agent
            if hasattr(self, 'graph_state') and "conversation_state" in self.graph_state:
                await self.graph_state["conversation_state"].add_message(
                    role=MessageRole.ASSISTANT,
                    content=response,
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "message_type": "llm_response",
                        "model": self.model,
                        "session_id": self.session_id
                    },
                    sender="orchestrator_graph.llm",
                    target="orchestrator_graph.llm_query"
                )

            # Process the response (check for tool calls, etc)
            processed_response = await self.process_response(response)
            
            # Log sending processed response back to orchestrator
            if hasattr(self, 'graph_state') and "conversation_state" in self.graph_state:
                await self.graph_state["conversation_state"].add_message(
                    role=MessageRole.ASSISTANT,
                    content=processed_response,
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "message_type": "processed_response",
                        "model": self.model,
                        "session_id": self.session_id,
                        "has_tool_calls": bool(self.tool_parser.extract_tool_calls(response))
                    },
                    sender="orchestrator_graph.llm_query",
                    target="orchestrator_graph.orchestrator"
                )
            
            return {
                "response": processed_response,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            return {
                "response": str(e),
                "status": "error"
            }

    async def query_llm(self, prompt: str) -> str:
        """
        Send a query to the LLM via Ollama API and return the response.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            The LLM's response text
            
        Raises:
            LLMQueryError: If there is an error querying the LLM
        """
        try:
            logger.debug(f"Sending request to LLM for model: {self.model}")
            
            # Use the LLM service that was initialized in the BaseAgent constructor
            if self.llm is None:
                error_msg = "LLM service not initialized"
                logger.error(error_msg)
                raise LLMQueryError(error_msg)
                
            # Call super().query_llm or directly use the llm service
            # logger.debug(f"llm_query_agent.query_llm: Calling super().query_llm with prompt: {prompt}")
            response_text = await super().query_llm(prompt)
            if not response_text:
                raise LLMQueryError("Empty response received from LLM")
                
            # logger.debig(f"llm_query_agent.query_llm: Received response from super().query_llm: {response_text}")
            logger.debug(f"Received LLM response of length {len(response_text)}")
            return response_text
                
        except Exception as e:
            error_msg = f"Error querying LLM: {e}"
            logger.error(error_msg)
            if isinstance(e, LLMQueryError):
                raise
            raise LLMQueryError(error_msg)

    async def get_llm_response(self, user_input: str) -> str:
        """
        Get a response from the LLM for the given user input.

        Args:
            user_input (str): The user's input message.

        Returns:
            str: The LLM's response.
        """
        try:
            if not self.graph_state or "conversation_state" not in self.graph_state:
                raise ValueError("Conversation state not initialized")
            
            conversation_state = self.graph_state["conversation_state"]
            messages = []
            
            # Convert conversation state messages to dict format for LLM
            for msg in conversation_state.messages:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Add system message if not present
            if not any(msg["role"] == MessageRole.SYSTEM for msg in messages):
                messages.insert(0, {
                    "role": MessageRole.SYSTEM,
                    "content": self.system_prompt
                })
            
            # Get response from LLM
            response = await self.llm.generate_text(messages=messages)
            
            return response

        except Exception as e:
            logger.error(f"Error getting LLM response: {str(e)}")
            raise

    def store_tool_requests(self, execution_results: List[Dict[str, Any]]) -> None:
        """
        Store tool requests in the pending_requests dictionary.
        
        Args:
            execution_results: List of tool execution results
        """
        try:
            for result in execution_results:
                request_id = result.get("request_id")
                if request_id:
                    # Store the original user input with the request
                    # This allows us to generate a proper follow-up when the tool completes
                    self.pending_requests[request_id] = result.get("args", {}).get("task", "Unknown request")
                    logger.debug(f"Stored request ID {request_id} in pending_requests")
                    
            # Log the current status of pending requests for debugging
            pending_count = len(self.pending_requests)
            request_ids = list(self.pending_requests.keys())
            logger.debug(f"Current pending requests count: {pending_count}")
            logger.debug(f"Current pending request IDs: {request_ids}")
            
        except Exception as e:
            logger.error(f"Error storing tool requests: {e}")
            
    async def process_response(self, response: str) -> str:
        """
        Process the LLM's response, execute any tool calls, and return the formatted result.

        Args:
            response (str): The raw response from the LLM.

        Returns:
            str: The processed response with tool execution results.

        Raises:
            ValueError: If response is empty or invalid.
            ToolExecutionError: If there's an error executing tools.
        """
        try:
            if not response or not response.strip():
                raise ValueError("Empty response received from LLM")

            # Store assistant's message in conversation state
            if self.graph_state and "conversation_state" in self.graph_state:
                logger.debug(f"Adding assistant message to conversation state. Response type: {type(response)}")
                conversation_state = self.graph_state["conversation_state"]
                logger.debug(f"Type of add_message method: {type(conversation_state.add_message)}")
                await conversation_state.add_message(
                    role=MessageRole.ASSISTANT,
                    content=response,
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "model": self.model,
                        "response_type": "llm_response",
                        "session_id": self.session_id
                    },
                    sender="orchestrator_graph.llm",
                    target="orchestrator_graph.orchestrator"
                )
                logger.debug("Successfully added assistant message")

            # Extract and execute tool calls
            tool_calls = self.tool_parser.extract_tool_calls(response)
            if not tool_calls:
                return response

            # Execute tools and format results
            logger.debug("Executing tool calls...")
            tool_results = await self.handle_tool_calls(tool_calls)
            logger.debug(f"Got tool results type: {type(tool_results)}")
            formatted_response = self._format_tool_results(response, tool_results)
            
            return formatted_response

        except Exception as e:
            error_msg = f"Error processing LLM response: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise

    def _format_tool_results(self, original_response: str, tool_results: List[Dict[str, Any]]) -> str:
        """
        Format tool execution results into a readable response.

        Args:
            original_response (str): The original LLM response.
            tool_results (List[Dict[str, Any]]): Results from tool executions.

        Returns:
            str: Formatted response including tool results.
        """
        formatted_results = []
        for result in tool_results:
            tool_name = result.get("tool", "Unknown Tool")
            if "error" in result:
                formatted_results.append(f"❌ {tool_name}: {result['error']}")
            else:
                formatted_results.append(f"✅ {tool_name}: {result['result']}")

        if formatted_results:
            return f"{original_response}\n\nTool Execution Results:\n" + "\n".join(formatted_results)

    def _apply_personality_to_tool_results(self, execution_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply personality formatting to tool results.
        
        Args:
            execution_results: List of tool execution results
            
        Returns:
            List of formatted tool execution results
        """
        if not self.personality_enabled or not hasattr(self, 'personality'):
            return execution_results
            
        try:
            formatted_results = []
            for result in execution_results:
                # Only format if we have a result to work with
                if 'result' in result:
                    # Apply personality formatting
                    formatted_result = self.personality.format_tool_result(result['result'])
                    # Update the result
                    result_copy = result.copy()
                    result_copy['result'] = formatted_result
                    formatted_results.append(result_copy)
                else:
                    # Pass through unchanged
                    formatted_results.append(result)
                    
            return formatted_results
        except Exception as e:
            logger.error(f"Error applying personality to tool results: {e}")
            # Return original results if formatting fails
            return execution_results

    async def handle_tool_completion(self, request_id: str, original_query: str) -> Dict[str, str]:
        """
        Handle the completion of a tool request.
        
        Args:
            request_id: The ID of the completed tool request
            original_query: The original user query that triggered the tool
            
        Returns:
            Dict with response and status
        """
        try:
            # Get the tool completion data
            if request_id not in PENDING_TOOL_REQUESTS:
                return {"response": "Tool request not found", "status": "error"}
            
            request_data = PENDING_TOOL_REQUESTS[request_id]
            tool_name = request_data.get("name", "unknown_tool")
            
            # Generate prompt for tool completion
            prompt = format_completed_tools_prompt(request_id, original_query)
            
            # Get response from LLM
            response = await self.query_llm(prompt)
            
            # Store the assistant's response in the conversation state - wrapped in try/except
            # to ensure we don't fail the entire request if storage fails
            try:
                if self.has_db and self.conversation_id:
                    # Use message_manager directly
                    if self.graph_state and "conversation_state" in self.graph_state:
                        # Log the tool completion
                        await self.graph_state["conversation_state"].add_message(
                            role=MessageRole.TOOL,
                            content=f"Tool completion from {tool_name}: {request_data.get('response', {})}",
                            metadata={
                                "timestamp": datetime.now().isoformat(),
                                "tool_name": tool_name,
                                "response_type": "tool_completion",
                                "session_id": self.session_id,
                                "request_id": request_id,
                                "original_query": original_query
                            },
                            sender=f"orchestrator_graph.{tool_name}",
                            target="orchestrator_graph.orchestrator"
                        )
                        # Log the assistant's response
                        await self.graph_state["conversation_state"].add_message(
                            role=MessageRole.ASSISTANT,
                            content=response,
                            metadata={
                                "timestamp": datetime.now().isoformat(),
                                "model": self.model,
                                "response_type": "tool_completion_response",
                                "session_id": self.session_id,
                                "request_id": request_id,
                                "tool_name": tool_name
                            },
                            sender="orchestrator_graph.orchestrator",
                            target="orchestrator_graph.cli"
                        )
            except Exception as e:
                logger.warning(f"Could not store assistant message after tool completion: {e}")
                # Continue with processing even if message storage fails
            
            # Return success
            logger.debug(f"Successfully processed tool completion for request {request_id}")
            return {"response": response, "status": "success"}
            
        except Exception as e:
            error_msg = f"Error handling tool completion: {e}"
            logger.error(error_msg)
            return {"response": f"Error: {error_msg}", "status": "error"}

    def _is_conversation_end(self, text: str) -> bool:
        """
        Check if the user's message indicates an intent to end the conversation.
        
        Args:
            text: The user's message text
            
        Returns:
            True if the user wants to end the conversation, False otherwise
        """
        # Simple implementation - check for common exit phrases
        exit_phrases = [
            "end conversation",
            "exit conversation",
            "close conversation",
            "quit conversation",
            "goodbye", 
            "bye",
            "exit",
            "quit"
        ]
        
        text_lower = text.lower()
        for phrase in exit_phrases:
            if phrase in text_lower:
                return True
                
        return False

    @property
    def conversation_id(self):
        """Get the current conversation ID."""
        return self._conversation_id if hasattr(self, '_conversation_id') else None
        
    @conversation_id.setter
    def conversation_id(self, value):
        """Set the conversation ID with logging."""
        old_value = self.conversation_id
        self._conversation_id = value
        logger.debug(f"LLMQueryAgent.conversation_id changed from {old_value} to {value}")
        
        # Also update session_id for consistency
        self._session_id = value
        
    @property
    def session_id(self):
        """Get the session ID (alias for conversation_id)."""
        return self.conversation_id
        
    @session_id.setter
    def session_id(self, value):
        """Set the session ID (alias for conversation_id)."""
        self.conversation_id = value

    async def handle_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute a list of tool calls and return their results.

        Args:
            tool_calls (List[Dict[str, Any]]): List of tool call specifications.

        Returns:
            List[Dict[str, Any]]: List of tool execution results.
        """
        try:
            if not tool_calls:
                return []

            # Execute tools with graph state for message logging
            execution_results = await self.tool_executor.execute_tools(
                tool_calls, 
                graph_state=self.graph_state if hasattr(self, 'graph_state') else None
            )
            
            # Store tool executions in conversation state
            if self.graph_state and "conversation_state" in self.graph_state:
                for result in execution_results:
                    tool_name = result.get('tool', 'unknown_tool')
                    args = result.get('args', {})
                    # Log the tool call
                    await self.graph_state["conversation_state"].add_message(
                        role=MessageRole.TOOL,
                        content=f"Tool call: {tool_name} with args: {args}",
                        metadata={
                            "timestamp": datetime.now().isoformat(),
                            "tool_name": tool_name,
                            "tool_args": args,
                            "request_type": "tool_call",
                            "session_id": self.session_id
                        },
                        sender="orchestrator_graph.orchestrator",
                        target=f"orchestrator_graph.{tool_name}"
                    )
                    # Log the tool response
                    await self.graph_state["conversation_state"].add_message(
                        role=MessageRole.TOOL,
                        content=f"Tool result: {result.get('result', {})}",
                        metadata={
                            "timestamp": datetime.now().isoformat(),
                            "tool_name": tool_name,
                            "response_type": "tool_response",
                            "session_id": self.session_id,
                            "request_id": result.get('request_id')
                        },
                        sender=f"orchestrator_graph.{tool_name}",
                        target="orchestrator_graph.orchestrator"
                    )

            return execution_results

        except Exception as e:
            error_msg = f"Error handling tool calls: {str(e)}"
            logger.error(error_msg)
            raise 
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

import json
import logging
import requests
import re
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime

# Local imports
from src.services.db_services.db_manager import (
    TaskStatus, 
    MessageRole, 
    StateError,
    StateTransitionError,
    Message
)
from src.config import Configuration
from src.agents.base_agent import BaseAgent
from src.tools.orchestrator_tools import (
    add_tools_to_prompt, 
    handle_tool_calls, 
    format_tool_results, 
    PENDING_TOOL_REQUESTS
)
from src.graphs.orchestrator_graph import format_completed_tools_prompt, create_initial_state
from src.tools.initialize_tools import initialize_tool_dependencies

# Setup logging
from src.services.logging_services.logging_service import get_logger
logger = get_logger(__name__)

class LLMQueryAgent(BaseAgent):
    """
    Specialized agent for LLM interactions and tool processing.
    
    This class provides methods for:
    - Managing conversation state for LLM context
    - Generating prompts for LLM interaction
    - Processing LLM responses for tool calls
    - Handling tool execution and results
    
    It is designed to be used by the OrchestratorAgent rather than directly.
    """
    
    def __init__(self, config: Configuration = None):
        """Initialize the LLM Query Agent with configuration."""
        if not config:
            config = Configuration()
            
        super().__init__(
            name="llm_query",
            prompt_section="You are a helpful AI assistant that can use tools to assist the user.",
            api_url=config.ollama_api_url + '/api/generate',
            model=config.ollama_model,
            config=config
        )
        
        # Tool tracking
        self.last_tool_results = ""
        
        # Initialize tool dependencies
        self.tool_initialization = initialize_tool_dependencies(self)
        logger.debug(f"Initialized LLM Query Agent with model: {self.model}")

    def generate_prompt(self, user_input: str) -> str:
        """
        Generate a prompt for the LLM.
        
        This combines:
        - Base system prompt
        - Available tools description
        - Conversation history (if available)
        - Current user input
        - Any recent tool results
        
        Args:
            user_input: The user's input message
            
        Returns:
            Formatted prompt for the LLM
        """
        # Start with base system prompt
        base_prompt = self.prompt_section
        
        # Add tools description
        base_prompt = add_tools_to_prompt(base_prompt)
        
        # Add conversation history if available
        context = self.get_conversation_context()
        
        # Add tool results if any
        tool_results = self.last_tool_results
        
        # Combine everything into a single prompt
        # The order is important for proper context
        prompt = f"{base_prompt}\n\n"
        
        if context:
            prompt += f"# Conversation History\n{context}\n\n"
            
        if tool_results:
            prompt += f"{tool_results}\n\n"
            
        prompt += f"User: {user_input}\n\nAssistant:"
        
        logger.debug(f"Generated prompt of length {len(prompt)}")
        return prompt

    def get_conversation_context(self) -> str:
        """
        Get the conversation history to include in the prompt.
        
        Returns:
            Formatted conversation history as a string
        """
        if not self.graph_state or "conversation_state" not in self.graph_state:
            return ""
            
        # Get messages from conversation state
        messages = self.graph_state["conversation_state"].messages
        if not messages:
            return ""
            
        context = ""
        # Convert messages to string format
        for msg in messages:
            sender = "User" if msg.role == MessageRole.USER else "Assistant"
            context += f"{sender}: {msg.content}\n\n"
            
        return context

    def query_llm(self, prompt: str) -> str:
        """
        Send a query to the LLM via Ollama API and return the response.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            The LLM's response text
        """
        try:
            logger.debug(f"Sending request to LLM for model: {self.model}")
            
            # Use the LLM service that was initialized in the BaseAgent constructor
            if self.llm is None:
                error_msg = "LLM service not initialized"
                logger.error(error_msg)
                return f"Error: {error_msg}"
                
            # Call super().query_llm or directly use the llm service
            response_text = super().query_llm(prompt)
            
            logger.debug(f"Received LLM response of length {len(response_text)}")
            return response_text
                
        except Exception as e:
            error_msg = f"Error querying LLM: {e}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    def get_llm_response(self, user_input: str) -> str:
        """
        Generate a prompt and query the LLM.
        
        Args:
            user_input: The user's input message
            
        Returns:
            The LLM's response text
        """
        prompt = self.generate_prompt(user_input)
        #logger.debug(f"llm_query_agent.get_llm_response: Generated prompt: {prompt}")
        response = self.query_llm(prompt)
        return response

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
            
    def process_llm_response(self, response_text: str, user_input: str) -> Dict[str, Any]:
        """
        Process the LLM's response to check for tool calls and handle them.
        
        Args:
            response_text: The LLM's response text
            user_input: The original user input
            
        Returns:
            Dictionary with the updated response and any tool calls
        """
        try:
            # Check for tool calls
            processing_result = handle_tool_calls(response_text, user_input)
            
            # Get the original response
            response = response_text
            
            # Check if there were any tool calls
            tool_calls = processing_result.get("tool_calls", [])
            execution_results = processing_result.get("execution_results", [])
            
            if not tool_calls:
                # No tool calls, just return the original response
                logger.debug("No tool calls detected in response")
                return {"response": response, "status": "success"}
                
            logger.debug(f"Detected {len(tool_calls)} tool calls in response")
            
            # Store the tool requests in the pending_requests dictionary
            self.store_tool_requests(execution_results)
            
            # Format tool results as text to include in the response
            tool_result_text = format_tool_results(processing_result)
            self.last_tool_results = tool_result_text
            
            # Inject the tool results into the response
            if "I'll use" in response and tool_result_text:
                # Only append if we need to
                if not response.strip().endswith(tool_result_text.strip()):
                    augmented_response = f"{response}\n\n{tool_result_text}"
                else:
                    augmented_response = response
            else:
                augmented_response = response
                
            return {
                "response": augmented_response,
                "status": "success",
                "tool_calls": tool_calls,
                "execution_results": execution_results
            }
            
        except Exception as e:
            error_msg = f"Error processing LLM response: {e}"
            logger.error(error_msg)
            return {"response": response_text, "status": "error", "error": error_msg}

    def chat(self, user_input: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a user message and generate a response.
        
        This method:
        1. Gets a response from the LLM
        2. Processes the response for tool calls
        3. Updates the conversation state
        
        Args:
            user_input: The user's input message
            request_id: Optional request ID for tracking
            
        Returns:
            Dictionary with the response and any other relevant data
        """
        try:
            # Store the user message in the conversation state - wrapped in try/except
            # to ensure we don't fail the entire request if storage fails
            try:
                logger.debug(f"llm_query_agent.chat: Starting llm_query_agent.chat: {user_input}")
                logger.debug(f"llm_query_agent.chat: self.has_db: {self.has_db}")
                logger.debug(f"llm_query_agent.chat: self.conversation_id: {self.conversation_id}")
                if self.has_db and self.conversation_id:
                    # Use message_manager directly
                    logger.debug(f"llm_query_agent.chat: Storing user message: {user_input}")
                    logger.debug(f"llm_query_agent.chat: message to save: session_id={self.conversation_id}, role={MessageRole.USER}, content={user_input}, sender=orchestrator_graph.cli, target=orchestrator_graph.{self.name}, user_id={self.user_id}")
                    self.db.message_manager.store_message(
                        session_id=self.conversation_id,
                        role=MessageRole.USER,
                        content=user_input,
                        sender="orchestrator_graph.cli",
                        target=f"orchestrator_graph.{self.name}",
                        user_id=self.user_id
                    )                    
                    # Update state manager if available
                    if self.state_manager:
                        self.state_manager.update_conversation(MessageRole.USER, user_input)
            except Exception as e:
                logger.warning(f"Could not store user message: {e}")
                # Continue with processing even if message storage fails
            
            # Get response from LLM
            response_text = self.get_llm_response(user_input)
            
            # Process response for tool calls
            result = self.process_llm_response(response_text, user_input)
            
            # Store the assistant's response in the conversation state - wrapped in try/except
            # to ensure we don't fail the entire request if storage fails
            try:
                if "response" in result and self.has_db and self.conversation_id:
                    # Use message_manager directly
                    logger.debug(f"llm_query_agent.chat: Storing assistant message: {result['response'][:50]}...")
                    logger.debug(f"llm_query_agent.chat: assistant message to save: session_id={self.conversation_id}, role={MessageRole.ASSISTANT}, sender=orchestrator_graph.{self.name}, target=orchestrator_graph.cli, user_id={self.user_id}")
                    self.db.message_manager.store_message(
                        session_id=self.conversation_id,
                        role=MessageRole.ASSISTANT,
                        content=result["response"],
                        sender=f"orchestrator_graph.{self.name}",
                        target="orchestrator_graph.cli",
                        user_id=self.user_id
                    )
                    logger.debug("llm_query_agent.chat: Successfully stored assistant message")
                    
                    # Update state manager if available
                    if self.state_manager:
                        self.state_manager.update_conversation(MessageRole.ASSISTANT, result["response"])
                else:
                    if not "response" in result:
                        logger.warning("llm_query_agent.chat: No 'response' key in result")
                    if not self.has_db:
                        logger.warning("llm_query_agent.chat: self.has_db is False")
                    if not self.conversation_id:
                        logger.warning("llm_query_agent.chat: self.conversation_id is None")
            except Exception as e:
                logger.warning(f"Could not store assistant message: {e}")
                logger.warning(f"Exception details: {str(e)}", exc_info=True)
                # Continue with processing even if message storage fails
                
            return result
            
        except Exception as e:
            error_msg = f"Error processing chat request: {e}"
            logger.error(error_msg)
            return {"response": f"Error: {error_msg}", "status": "error"}

    def handle_tool_completion(self, request_id: str, original_query: str) -> Dict[str, str]:
        """
        Handle a completed tool request.
        
        This method:
        1. Generates a special prompt with the tool results
        2. Gets a response from the LLM
        3. Updates the conversation state
        
        Args:
            request_id: The ID of the completed request
            original_query: The original user query that initiated the tool request
            
        Returns:
            Dictionary with the response and status
        """
        try:
            logger.debug(f"Handling completed tool request {request_id}")
            
            # Check if the request ID exists in pendingToolRequests
            if request_id not in PENDING_TOOL_REQUESTS:
                error_msg = f"Request ID {request_id} not found in pending tool requests"
                logger.error(error_msg)
                return {"response": f"Error: {error_msg}", "status": "error"}
                
            request = PENDING_TOOL_REQUESTS[request_id]
            
            # If request is already processed, skip
            if request.get("processed_by_agent", False):
                logger.debug(f"Request {request_id} already processed, skipping")
                return {"response": "This tool request has already been processed.", "status": "info"}
                
            # Mark that we're starting to process this request
            request["processing_started"] = True
            
            # Generate a special prompt with the tool results
            prompt = format_completed_tools_prompt(request_id, original_query)
            
            # Get a response from the LLM
            response = self.query_llm(prompt)
            
            # Store the assistant's response in the conversation state - wrapped in try/except
            # to ensure we don't fail the entire request if storage fails
            try:
                if self.has_db and self.conversation_id:
                    # Use message_manager directly
                    self.db.message_manager.store_message(
                        session_id=self.conversation_id,
                        role=MessageRole.ASSISTANT,
                        content=response,
                        sender=f"orchestrator_graph.{self.name}",
                        target="orchestrator_graph.cli",
                        user_id=self.user_id
                    )
                    
                    # Update state manager if available
                    if self.state_manager:
                        self.state_manager.update_conversation(MessageRole.ASSISTANT, response)
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
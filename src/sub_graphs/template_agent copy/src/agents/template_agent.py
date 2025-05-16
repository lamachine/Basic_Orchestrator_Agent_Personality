"""
Template Agent - Coordinates tool execution and message flow.

This module provides a template for creating specialized agents that:
1. Process user messages and determine required tools
2. Coordinate tool execution and handle results
3. Manage conversation flow and state
4. Provide clear responses to users

To use this template:
1. Copy this file to your agent's directory
2. Rename it to <your_agent>_agent.py
3. Update the imports to match your project structure
4. Modify the tool handling logic for your needs
5. Customize the prompt creation for your use case
"""

import re
import json
import uuid
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base_agent import BaseAgent, AgentConfig
from ..services.logging_service import get_logger
from ..state.state_models import MessageRole, MessageType, MessageState
from ..tools.tool_registry import ToolRegistry

logger = get_logger(__name__)

class TemplateAgent(BaseAgent):
    """
    Template agent that coordinates tool execution and message flow.
    
    This agent:
    1. Processes user messages to identify tool needs
    2. Manages tool execution and results
    3. Maintains conversation context
    4. Provides clear user responses
    """
    
    def __init__(self, name: str, prompt_section: str, api_url: Optional[str] = None, 
                 model: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the template agent.
        
        Args:
            name: Agent name
            prompt_section: Section of the prompt to use
            api_url: Optional LLM API URL
            model: Optional LLM model name
            config: Optional configuration dictionary
        """
        agent_config = AgentConfig(
            name=name,
            prompt_section=prompt_section,
            api_url=api_url,
            model=model,
            config=config
        )
        super().__init__(agent_config)
        
        # Set graph name from config or default
        self.graph_name = self.config.get('graph_name', 'template_graph')
        
        # Initialize tool registry
        self.tool_registry = ToolRegistry()
        
    async def process_message(self, message: str, session_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process an incoming user message.
        
        Args:
            message: The user's message
            session_state: Optional session state dictionary
            
        Returns:
            Dict[str, Any]: Response containing status and message
        """
        logger.debug("--- TEMPLATE AGENT: process_message START ---")
        logger.debug(f"[process_message] User message: '{message}'")
        
        try:
            # Log user message
            if session_state and "conversation_state" in session_state:
                await self._log_message(
                    session_state["conversation_state"],
                    MessageRole.USER,
                    message,
                    sender=f"{self.graph_name}.cli",
                    target=f"{self.graph_name}.agent"
                )

            # Create prompt and get LLM response
            prompt = await self._create_prompt(message)
            response = await self.query_llm(prompt)
            
            # Check for tool calls in response
            tool_call_pattern = r"`\{[^`]+\}`"
            matches = list(re.finditer(tool_call_pattern, response))
            
            if matches:
                # Handle tool call
                return await self._handle_tool_call(matches[0], message, session_state)
            else:
                # Handle normal response
                return await self._handle_normal_response(response, session_state)
                
        except Exception as e:
            logger.error(f"Error in process_message: {e}", exc_info=True)
            return {"response": f"Error: {str(e)}", "status": "error"}
    
    async def _create_prompt(self, message: str) -> str:
        """
        Create a prompt for the LLM.
        
        Args:
            message: The user's message
            
        Returns:
            str: The formatted prompt
        """
        return f"{self.prompt_section}\n\nUser: {message}\nAssistant:"
    
    async def _get_tool_info(self) -> str:
        """
        Get information about available tools.
        
        Returns:
            str: Formatted tool information
        """
        tools = self.tool_registry.get_all_tools()
        if not tools:
            return "No tools available."
            
        tool_info = ["Available tools:"]
        for tool in tools:
            tool_info.append(f"- {tool.name}: {tool.description}")
        return "\n".join(tool_info)
    
    async def _handle_tool_call(
        self,
        match: re.Match,
        original_message: str,
        session_state: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Handle a tool call from the LLM response.
        
        Args:
            match: The regex match containing the tool call
            original_message: The original user message
            session_state: Optional session state dictionary
            
        Returns:
            Dict[str, Any]: Response containing status and message
        """
        try:
            # Parse tool call
            tool_call_json = match.group(0).strip('`')
            tool_call = json.loads(tool_call_json)
            
            # Extract tool information
            tool_name = tool_call.get("name")
            args = tool_call.get("args", {})
            request_id = str(uuid.uuid4())
            args["request_id"] = request_id
            
            # Log tool call
            if session_state and "conversation_state" in session_state:
                await self._log_message(
                    session_state["conversation_state"],
                    MessageRole.TOOL,
                    f"Tool call: {tool_name} with args: {args}",
                    metadata={"tool": tool_name, "args": args, "request_id": request_id},
                    sender=f"{self.graph_name}.agent",
                    target=f"{self.graph_name}.{tool_name}"
                )
            
            # Execute tool
            tool = self.tool_registry.get_tool(tool_name)
            if not tool:
                raise Exception(f"Tool {tool_name} not found")
                
            # Schedule tool execution
            asyncio.create_task(self._execute_tool(tool, args, request_id, session_state))
            
            # Return pending message
            pending_msg = f"[Tool: {tool_name}] Your request is being processed. Request ID: {request_id}"
            return {"response": pending_msg, "status": "pending"}
            
        except Exception as e:
            logger.error(f"Error handling tool call: {e}", exc_info=True)
            return {"response": f"Error: {str(e)}", "status": "error"}
    
    async def _handle_normal_response(
        self,
        response: str,
        session_state: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Handle a normal (non-tool) response from the LLM.
        
        Args:
            response: The LLM's response
            session_state: Optional session state dictionary
            
        Returns:
            Dict[str, Any]: Response containing status and message
        """
        try:
            # Log response
            if session_state and "conversation_state" in session_state:
                await self._log_message(
                    session_state["conversation_state"],
                    MessageRole.ASSISTANT,
                    response,
                    sender=f"{self.graph_name}.agent",
                    target=f"{self.graph_name}.cli"
                )
            
            # Update history
            if self.conversation_history is not None:
                self.conversation_history.append({
                    'user': response,
                    'assistant': response,
                    'timestamp': datetime.now().isoformat()
                })
            
            return {"response": response, "status": "success"}
            
        except Exception as e:
            logger.error(f"Error handling normal response: {e}", exc_info=True)
            return {"response": f"Error: {str(e)}", "status": "error"}
    
    async def _execute_tool(
        self,
        tool: Any,
        args: Dict[str, Any],
        request_id: str,
        session_state: Optional[Dict[str, Any]]
    ) -> None:
        """
        Execute a tool and handle its result.
        
        Args:
            tool: The tool to execute
            args: The tool's arguments
            request_id: The request ID
            session_state: Optional session state dictionary
        """
        try:
            # Execute tool
            result = await tool.execute(**args)
            
            # Log result
            if session_state and "conversation_state" in session_state:
                await self._log_message(
                    session_state["conversation_state"],
                    MessageRole.TOOL,
                    f"Tool result: {result}",
                    metadata={"tool": tool.name, "result": result, "request_id": request_id},
                    sender=f"{self.graph_name}.{tool.name}",
                    target=f"{self.graph_name}.agent"
                )
            
            # Create completion message
            completion_msg = f"Tool {tool.name} completed successfully. Result: {result}"
            
            # Log completion
            if session_state and "conversation_state" in session_state:
                await self._log_message(
                    session_state["conversation_state"],
                    MessageRole.ASSISTANT,
                    completion_msg,
                    metadata={"tool_completion": True, "request_id": request_id},
                    sender=f"{self.graph_name}.agent",
                    target=f"{self.graph_name}.cli"
                )
            
        except Exception as e:
            logger.error(f"Error executing tool: {e}", exc_info=True)
            error_msg = f"Error executing tool {tool.name}: {str(e)}"
            
            # Log error
            if session_state and "conversation_state" in session_state:
                await self._log_message(
                    session_state["conversation_state"],
                    MessageRole.ASSISTANT,
                    error_msg,
                    metadata={"tool_error": True, "request_id": request_id},
                    sender=f"{self.graph_name}.agent",
                    target=f"{self.graph_name}.cli"
                ) 
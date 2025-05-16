"""
Template Tool Interface for Parent Graph

This file provides a standardized template for creating tool interfaces that parent graphs can use to interact with sub-graphs.
It implements:
1. Input validation using Pydantic models
2. Standardized request/response format
3. Request ID tracking
4. Error handling and logging
5. Tool metadata and documentation
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, ValidationError
import asyncio
import os

from src.sub_graphs.template_agent.src.services.logging_service import get_logger
from src.sub_graphs.template_agent.src.agents.template_agent import TemplateAgent

logger = get_logger(__name__)

class ToolInput(BaseModel):
    """Input model for tool requests."""
    task: str
    parameters: Dict[str, Any]
    request_id: str
    timestamp: str

class TemplateTool:
    """Template tool for running test tools in the sub-graph."""
    
    def __init__(self):
        """Initialize the template tool."""
        self.name = "template_tool"
        self.description = """Template tool for running test tools in the sub-graph.
This tool acts as a bridge between the orchestrator and test tools within the sub-graph.
The sub-graph contains various test tools (like test_tool_1) that can be executed.
The orchestrator should send requests to the template tool with the user's request, 
and it will route them to the appropriate test tool within the sub-graph."""
        self.version = "1.0.0"
        self.capabilities = ["run_test_tool"]
        
        # Initialize the template agent
        self.agent = TemplateAgent(
            name="template_agent",
            prompt_section="You are a template agent that coordinates tool execution.",
            config={"graph_name": "template_graph"}
        )
        
    async def execute(self, session_state=None, **kwargs) -> Dict[str, Any]:
        """
        Execute the template tool.
        
        Args:
            session_state: Optional session state dictionary to be passed to the agent.
            **kwargs: Tool input parameters
            
        Returns:
            Dict[str, Any]: Tool execution result
        """
        try:
            # Validate input
            input_data = ToolInput(**kwargs)
            
            # Process with template agent
            result = await self.agent.process_message(input_data.task, session_state=session_state)
            
            return result
            
        except ValidationError as e:
            logger.error(f"Input validation error: {e}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {"status": "error", "message": str(e)}

# Create singleton instance
template_tool = TemplateTool() 
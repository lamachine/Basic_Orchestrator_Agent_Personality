"""Personal assistant agent implementation."""

from typing import Dict, Any, Optional
import logging
from dataclasses import dataclass
import importlib
import os
import json

# from src.sub_graph_personal_assistant.config.config import PersonalAssistantConfig  # (disabled for minimal orchestrator)
# from src.sub_graph_personal_assistant.tools.personal_assistant_base_tool import PersonalAssistantTool  # (disabled for minimal orchestrator)
# from src.sub_graph_personal_assistant.tools.google.google_mail_tools import GmailTool  # (disabled for minimal orchestrator)
# from src.sub_graph_personal_assistant.tools.slack_tool import SlackTool  # (disabled for minimal orchestrator)

# Setup logging
from src.services.logging_service import get_logger
logger = get_logger(__name__)

@dataclass
class ToolRegistry:
    """Registry of available personal assistant tools."""
    gmail: Any = None  # Will be GmailTool when loaded
    # slack: Any = None  # Will be SlackTool when loaded

# class PersonalAssistantAgent:
#     """Agent responsible for managing personal assistant tools and processing tasks."""
#     ...

    def __init__(self, config: PersonalAssistantConfig):
        """Initialize the personal assistant agent.
        
        Args:
            config: Configuration for the personal assistant and its tools
        """
        self.config = config
        self.tools = ToolRegistry()
        self._initialized = False
        self.source = "personal_assistant_graph.system"
        self._base = None
        
    def _get_base_agent(self):
        """Lazy load the base agent."""
        if not self._base:
            base_module = importlib.import_module('src.agents.base_agent')
            self._base = base_module.BaseAgent(
                name="personal_assistant_base",
                api_url=os.getenv('LLM_API_URL', 'http://localhost:11434'),
                model=os.getenv('LLM_MODEL', 'llama3.1')
            )
        return self._base
        
    def _get_gmail_tool(self):
        """Lazy load the Gmail tool."""
        return importlib.import_module('src.sub_graph_personal_assistant.tools.google.google_mail_tools').GmailTool
        
    async def initialize(self) -> bool:
        """Initialize all configured tools.
        
        Returns:
            bool: True if all tools initialized successfully
        """
        try:
            if self._initialized:
                return True
                
            # Initialize Gmail if configured
            logger.debug(f"Gmail enabled: {self.config.gmail_enabled}")
            if self.config.gmail_enabled:
                logger.debug(f"Gmail config: {self.config.gmail_config}")
                if not self.config.gmail_config:
                    logger.error("Gmail enabled but no configuration provided")
                    return False
                    
                GmailTool = self._get_gmail_tool()
                logger.debug("Creating Gmail tool instance")
                self.tools.gmail = GmailTool(self.config.gmail_config)
                logger.debug("Initializing Gmail tool")
                if not await self.tools.gmail.initialize():
                    logger.error("Failed to initialize Gmail tool")
                    return False
                logger.debug("Gmail tool initialized successfully")
                    
            # Initialize Slack if configured
            # if self.config.slack_enabled:
            #     self.tools.slack = SlackTool(self.config.slack_config)
            #     if not await self.tools.slack.initialize():
            #         logger.error("Failed to initialize Slack tool")
            #         return False
                    
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize personal assistant agent: {e}")
            return False
            
    async def cleanup(self) -> None:
        """Clean up all tools."""
        if self.tools.gmail:
            await self.tools.gmail.cleanup()
        # if self.tools.slack:
        #     await self.tools.slack.cleanup()
        self._initialized = False
        
    async def process_task(self, task: str) -> Dict[str, Any]:
        """Process a natural language task using appropriate tools.
        
        Args:
            task: Natural language task description
            
        Returns:
            Dict containing the execution results
        """
        if not self._initialized:
            return {
                "success": False,
                "error": "Personal assistant not initialized"
            }
            
        try:
            # Parse task to determine required tool and action
            task = task.lower().strip()
            
            # Handle Gmail tasks
            if any(x in task for x in ["email", "gmail"]):
                if not self.tools.gmail:
                    return {
                        "success": False,
                        "error": "Gmail tool not configured. Please enable Gmail in configuration."
                    }
                return await self._process_gmail_task(task)
                
            # Handle Slack tasks
            # elif any(x in task for x in ["slack", "message", "channel"]):
            #     if not self.tools.slack:
            #         return {
            #             "success": False,
            #             "error": "Slack tool not configured"
            #         }
            #     return await self._process_slack_task(task)
                
            else:
                return {
                    "success": False,
                    "error": "Unsupported task type. Available: email/Gmail"
                }
                
        except Exception as e:
            logger.error(f"Error processing task: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def _process_gmail_task(self, task: str) -> Dict[str, Any]:
        """Process Gmail-related tasks.
        
        Args:
            task: Gmail task description
            
        Returns:
            Dict containing the execution results
        """
        try:
            # Use LLM to parse task and generate appropriate Gmail action
            prompt = f"""
            Parse this email-related task and generate the appropriate Gmail API parameters.
            Task: {task}
            
            Return a JSON object with:
            - action: "search" or "send"
            - For search: include "query" (Gmail search syntax) and "max_results" (default 10)
            - For send: include "to", "subject", and "body"
            
            Examples of Gmail search syntax:
            - Unread messages: "is:unread in:inbox"
            - Recent emails: "newer_than:3d"
            - From someone: "from:example@email.com"
            - With attachment: "has:attachment"
            """
            
            # Get LLM response synchronously
            action_params_str = self._get_base_agent().query_llm(prompt)
            try:
                action_params = json.loads(action_params_str)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON: {action_params_str}")
                action_params = {
                    "action": "search",
                    "query": "is:unread in:inbox",
                    "max_results": 10
                }
            
            logger.debug(f"Using Gmail parameters: {action_params}")
            
            # Execute the Gmail action with the parameters
            return await self.tools.gmail.execute(action_params)
                
        except Exception as e:
            logger.error(f"Error processing Gmail task: {e}")
            return {
                "success": False,
                "error": f"Failed to process Gmail task: {str(e)}"
            }
            
    # async def _process_slack_task(self, task: str) -> Dict[str, Any]:
    #     """Process Slack-specific tasks.
    #     
    #     Args:
    #         task: Slack task description
    #         
    #     Returns:
    #         Dict containing the execution results
    #     """
    #     # TODO: Implement Slack task processing similar to Gmail
    #     return {
    #         "success": False,
    #         "error": "Slack integration not yet implemented"
    #     } 
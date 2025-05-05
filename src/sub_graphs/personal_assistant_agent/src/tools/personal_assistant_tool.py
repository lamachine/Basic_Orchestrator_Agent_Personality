"""Personal Assistant tool implementation."""

import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import threading
from src.tools.orchestrator_tools import PENDING_TOOL_REQUESTS

# Set up logger
logger = logging.getLogger(__name__)

class PersonalAssistantTool:
    """Personal Assistant tool for handling emails, calendar, and tasks."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Personal Assistant tool.
        
        Args:
            config: Optional configuration dictionary loaded from tool_config.yaml
        """
        self.config = config or {}
        self.name = "personal_assistant"
        self.description = "Handles emails, messages, to-do lists, and calendar integration"
        logger.info(f"Initialized {self.name} tool")
        
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate a true async tool call: immediately return 'pending', then complete in the background.
        """
        import uuid
        # Extract task from arguments
        task = args.get("task", "")
        request_id = args.get("request_id") or str(uuid.uuid4())
        now = datetime.now().isoformat()
        # Store the main event loop for use in the background thread
        try:
            self._main_event_loop = asyncio.get_running_loop()
        except RuntimeError:
            self._main_event_loop = None
        # Immediately mark as pending with full metadata
        PENDING_TOOL_REQUESTS[request_id] = {
            "type": "status",
            "status": "in_progress",
            "name": self.name,
            "args": args,
            "response": None,
            "timestamp": now
        }
        # Start background thread to complete after delay
        def complete_tool(loop):
            import time
            time.sleep(2)  # Simulate async delay
            # Simulate result
            result = {
                "type": "result",
                "status": "success",
                "name": self.name,
                "args": args,
                "message": f"[Async] I've processed your request: '{task}'",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "task_type": "general",
                    "details": f"Simulated async processing for: {task}"
                }
            }
            PENDING_TOOL_REQUESTS[request_id].update({
                "type": "result",
                "status": "completed",
                "response": result,
                "timestamp": datetime.now().isoformat()
            })
            # Schedule async logging on the main event loop
            try:
                from src.services.message_service import log_and_persist_message
                from src.state.state_models import MessageRole
                session_state = args.get("session_state")
                if session_state and loop:
                    coro = log_and_persist_message(
                        session_state,
                        MessageRole.TOOL,
                        f"Tool result: {self.name} returned: {result}",
                        metadata={"tool": self.name, "result": result, "request_id": request_id},
                        sender=self.name,
                        target="orchestrator"
                    )
                    asyncio.run_coroutine_threadsafe(coro, loop)
                elif not loop:
                    logger.error("No main event loop available for async logging in tool completion.")
            except Exception as e:
                logger.error(f"Error scheduling async logging for tool completion: {e}")
        threading.Thread(target=complete_tool, args=(self._main_event_loop,), daemon=True).start()
        # Return pending status immediately
        return {
            "type": "status",
            "status": "in_progress",
            "name": self.name,
            "args": args,
            "message": f"Your request is being processed asynchronously. Request ID: {request_id}",
            "request_id": request_id,
            "timestamp": now
        }
    
    async def _handle_email_task(self, task: str) -> Dict[str, Any]:
        """Handle email-related tasks."""
        await asyncio.sleep(1)  # Simulate API call
        
        return {
            "status": "success",
            "message": f"Email task processed: '{task}'",
            "data": {
                "task_type": "email",
                "email_account": self.config.get("default_email", "user@example.com"),
                "details": "This is a simulated email response. In a real implementation, this would connect to an email API."
            }
        }
    
    async def _handle_calendar_task(self, task: str) -> Dict[str, Any]:
        """Handle calendar-related tasks."""
        await asyncio.sleep(1.5)  # Simulate API call
        
        return {
            "status": "success",
            "message": f"Calendar task processed: '{task}'",
            "data": {
                "task_type": "calendar",
                "timezone": self.config.get("default_timezone", "UTC"),
                "details": "This is a simulated calendar response. In a real implementation, this would connect to a calendar API."
            }
        }
    
    async def _handle_task_management(self, task: str) -> Dict[str, Any]:
        """Handle task management."""
        await asyncio.sleep(0.5)  # Simulate API call
        
        return {
            "status": "success",
            "message": f"Task management request processed: '{task}'",
            "data": {
                "task_type": "task_management",
                "details": "This is a simulated task management response. In a real implementation, this would connect to a task management API."
            }
        }
    
    async def _handle_reminder(self, task: str) -> Dict[str, Any]:
        """Handle reminders."""
        await asyncio.sleep(0.5)  # Simulate API call
        
        return {
            "status": "success",
            "message": f"Reminder set: '{task}'",
            "data": {
                "task_type": "reminder",
                "details": "This is a simulated reminder response. In a real implementation, this would connect to a reminder/calendar API."
            }
        } 
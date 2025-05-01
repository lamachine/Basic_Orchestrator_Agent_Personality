"""Personal assistant graph implementation.

This module implements the graph for the personal assistant sub-graph,
handling tool requests and managing the personal assistant agent state.
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime

# from src.sub_graph_personal_assistant.agents.personal_assistant_agent import PersonalAssistantAgent  # (disabled for minimal orchestrator)
# from src.sub_graph_personal_assistant.config.config import PersonalAssistantConfig  # (disabled for minimal orchestrator)

from src.state.state_models import MessageRole
# from src.sub_graph_personal_assistant.config.config import PersonalAssistantConfig  # (disabled for minimal orchestrator)

# Setup logging
from src.services.logging_service import get_logger
logger = get_logger(__name__)

async def personal_assistant_graph(state: Dict[str, Any], tool_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a tool request in the personal assistant sub-graph.
    
    Args:
        state: The current graph state dictionary
        tool_request: The tool request to process
        
    Returns:
        Dict containing the execution results
    """
    try:
        # Initialize the personal assistant agent if needed
        if 'personal_assistant' not in state.get('agent_states', {}):
            logger.debug("Initializing new personal assistant agent instance")
            config = PersonalAssistantConfig()
            agent = PersonalAssistantAgent(config)
            if not await agent.initialize():
                logger.error("Failed to initialize personal assistant agent")
                return {
                    "success": False,
                    "error": "Failed to initialize personal assistant agent"
                }
            if 'agent_states' not in state:
                state['agent_states'] = {}
            state['agent_states']['personal_assistant'] = {
                'agent': agent,
                'initialized_at': datetime.now().isoformat()
            }
        
        # Get the agent instance
        agent = state['agent_states']['personal_assistant']['agent']
        
        # Store the incoming tool request in message history
        logger.debug("Adding tool request to conversation history")
        message = {
            'role': MessageRole.TOOL,
            'content': str(tool_request),
            'metadata': {
                'sender': 'orchestrator_graph.tool_request',
                'target': 'personal_assistant_graph.agent',
                'timestamp': datetime.now().isoformat()
            }
        }
        if 'messages' not in state:
            state['messages'] = []
        state['messages'].append(message)
        
        # Process the task
        logger.debug(f"Processing task: {tool_request.get('task', '')[:50]}...")  # Log first 50 chars of task
        result = await agent.process_task(tool_request.get('task', ''))
        
        # Store the result in message history
        logger.debug("Adding tool result to conversation history")
        result_message = {
            'role': MessageRole.TOOL,
            'content': str(result),
            'metadata': {
                'sender': 'personal_assistant_graph.agent',
                'target': 'orchestrator_graph.tool_response',
                'timestamp': datetime.now().isoformat()
            }
        }
        state['messages'].append(result_message)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in personal assistant graph: {e}")
        return {
            "success": False,
            "error": f"Personal assistant graph error: {str(e)}"
        } 
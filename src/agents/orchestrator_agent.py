"""
Orchestrator Agent Module - Central coordinator for the agent ecosystem.

This module implements the OrchestratorAgent class, which serves as the high-level 
coordinator for the entire agent system. The OrchestratorAgent:

1. Maintains Global State - Manages the conversation graph and overall system state
2. Routes User Messages - Determines which specialized processor (agent/tool/sub-graph) 
   should handle each user message based on context and content
3. Manages Tool Ecosystem - Coordinates specialized tools that may internally be 
   implemented as complete agent sub-graphs
4. Provides UI Interface - Presents a unified interface for all UI components to interact
   with the agent system
5. Maintains Conversation History - Tracks the full conversation across multiple specialized
   processors

The architecture follows a hub-and-spoke model where the OrchestratorAgent acts as the 
central hub that dispatches tasks to specialized processors and aggregates their results.
This design enables:

- Clear Separation of Concerns - Each processor focuses on specific types of tasks
- Modularity - New processors can be added without changing the orchestrator's core logic
- Simplified Interface - UI components only need to interface with the orchestrator
- Flexible Routing - Tasks can be dynamically routed to the most appropriate processor

From the orchestrator's perspective, the specialized functions (librarian, valet, personal
assistant) are tools with defined interfaces, while internally they may be implemented as
full agent sub-graphs with their own state management and specialized behaviors.
"""

# Standard library imports
from typing import Dict, List, Any, Optional, Union, Type
from enum import Enum
import logging

# Local imports
from src.agents.base_agent import BaseAgent
from src.config import Configuration
from src.graphs.orchestrator_graph import MessageRole

# Setup logging
from src.services.logging_services.logging_service import get_logger
logger = get_logger(__name__)

class AgentType(Enum):
    """Enum of available agent types for task routing."""
    LLM_QUERY = "llm_query"
    # These specialized functions are tools from the orchestrator's perspective,
    # but internally implemented as agents in their own sub-graphs
    TOOL_LIBRARIAN = "librarian_tool"
    TOOL_VALET = "valet_tool"
    TOOL_PERSONAL_ASSISTANT = "personal_assistant_tool"
    # Add more specialized tool-agents as they're implemented

class OrchestratorAgent(BaseAgent):
    """
    Core orchestrator agent that coordinates the flow between specialized agents.
    
    This agent is responsible for:
    - Determining which agent or tool should handle a particular request
    - Managing conversation state across all agents, tools and sub-graphs
    - Coordinating parallel execution of multiple requests when appropriate
    - Aggregating responses from multiple agents, tools and sub-graphs
    - Maintaining the overall conversation context
    """
    
    def __init__(self, config: Configuration = None):
        """
        Initialize the Orchestrator Agent.
        
        Args:
            config: Optional configuration override
        """
        # Get configuration if not provided
        if not config:
            config = Configuration()
            
        # Initialize base agent
        super().__init__(
            name="orchestrator",
            prompt_section="You are the orchestrator agent, responsible for coordinating other specialized agents, tools, and sub-graphs.",
            api_url=config.ollama_api_url + '/api/generate',
            model=config.ollama_model,
            config=config
        )
        
        # Initialize agent registry
        self.agents = {}
        self._initialize_agents()
        
        logger.debug(f"OrchestratorAgent initialized with model: {self.model}")
        
    def _initialize_agents(self):
        """Initialize available specialized agents and tool dependencies."""
        # Import specialized agents
        from src.agents.llm_query_agent import LLMQueryAgent
        
        # We'll lazily initialize these as needed to save resources
        self.agent_classes = {
            AgentType.LLM_QUERY: LLMQueryAgent,
            # Add more agent mappings as we implement them
        }
        
        # For now, eagerly initialize the LLM query agent since it's commonly used
        self.agents[AgentType.LLM_QUERY] = self.agent_classes[AgentType.LLM_QUERY](self.config)
        logger.debug(f"Initialized LLM Query Agent")
        
    def get_processor(self, agent_type: AgentType):
        """
        Get or initialize an agent, tool, or sub-graph of the specified type.
        
        Args:
            agent_type: The type of processor to retrieve
            
        Returns:
            The requested agent, tool, or sub-graph instance
        """
        if agent_type not in self.agents:
            if agent_type in self.agent_classes:
                # Lazily initialize the agent
                self.agents[agent_type] = self.agent_classes[agent_type](self.config)
                logger.debug(f"Lazily initialized processor: {agent_type.value}")
                
                # Sync important fields when first initializing a processor
                processor = self.agents[agent_type]
                
                # Sync conversation/session ID
                if self.conversation_id:
                    if hasattr(processor, 'conversation_id'):
                        processor.conversation_id = self.conversation_id
                        logger.debug(f"Synced conversation_id to new processor: {self.conversation_id}")
                    if hasattr(processor, 'session_id'):
                        processor.session_id = self.conversation_id
                        logger.debug(f"Synced session_id to new processor: {self.conversation_id}")
                
                # Sync user ID
                if hasattr(self, 'user_id') and hasattr(processor, 'user_id'):
                    processor.user_id = self.user_id
                    logger.debug(f"Synced user_id to new processor: {self.user_id}")
                
            else:
                # Unknown agent type
                logger.error(f"Unknown processor type requested: {agent_type}")
                return None
                
        return self.agents[agent_type]
        
    def determine_processor_for_task(self, user_input: str) -> AgentType:
        """
        Determine which agent, tool, or sub-graph should handle a particular user input.
        
        Args:
            user_input: The user's input message
            
        Returns:
            The appropriate AgentType for the task (agent, tool, or sub-graph)
        """
        # This is a simple implementation - in the future, we could use a classifier model
        # to more intelligently route requests to the appropriate processor
        
        # For now, all tasks go to the LLM query agent
        return AgentType.LLM_QUERY
        
    def chat(self, user_input: str) -> Dict[str, Any]:
        """
        Process a user message through the appropriate agent, tool, or sub-graph.
        
        This is the main entry point for handling user messages. It:
        1. Determines which processor should handle the task
        2. Routes the task to that processor
        3. Returns the response
        
        In the future, this could be expanded to route to multiple processors in parallel
        and aggregate their responses.
        
        Args:
            user_input: The user's input message
            
        Returns:
            Dictionary with the response and any other relevant data
        """
        try:
            logger.debug(f"orchestratorAgent.chat: Starting orchestratorAgent.chat: {user_input}")
            # Update the global graph state with the user message - wrapped in try/except
            # to ensure we don't fail the entire request if state update fails
            try:
                if self.state_manager:
                    self.state_manager.update_conversation(MessageRole.USER, user_input)
            except Exception as e:
                logger.warning(f"Could not update conversation state with user message: {e}")
                # Continue with processing even if state update fails
            
            # Determine which processor should handle this request
            processor_type = self.determine_processor_for_task(user_input)
            logger.debug(f"Determined processor for task: {processor_type.value}")
            
            # Get the appropriate processor (agent/tool/sub-graph)
            processor = self.get_processor(processor_type)
            if not processor:
                error_msg = f"No processor available for type: {processor_type.value}"
                logger.error(error_msg)
                return {"response": f"Error: {error_msg}", "status": "error"}
                
            # Set conversation_id and session_id on the processor before calling chat
            if self.conversation_id and hasattr(processor, 'conversation_id'):
                logger.debug(f"Setting processor.conversation_id to {self.conversation_id}")
                processor.conversation_id = self.conversation_id
            if self.conversation_id and hasattr(processor, 'session_id'):
                logger.debug(f"Setting processor.session_id to {self.conversation_id}")
                processor.session_id = self.conversation_id
            
            # Route the request to the processor
            result = processor.chat(user_input)
            logger.debug(f"orchestratorAgent.chat: Received result from processor: {result}")
            
            # Update the global graph state with the assistant's response - wrapped in try/except
            # to ensure we don't fail the entire request if state update fails
            try:
                if "response" in result and self.state_manager:
                    self.state_manager.update_conversation(MessageRole.ASSISTANT, result["response"])
            except Exception as e:
                logger.warning(f"Could not update conversation state with assistant response: {e}")
                # Continue with processing even if state update fails
                
            return result
            
        except Exception as e:
            error_msg = f"Error processing chat request: {e}"
            logger.error(error_msg)
            return {"response": f"Error: {error_msg}", "status": "error"}
            
    def handle_tool_completion(self, request_id: str, original_query: str) -> Dict[str, str]:
        """
        Handle a completed tool request by generating a response through the appropriate processor.
        
        Args:
            request_id: The ID of the completed request
            original_query: The original user query that initiated the tool request
            
        Returns:
            Dictionary with the response and status
        """
        try:
            # For now, we just pass this to the LLM query agent
            # In the future, we could route to the appropriate processor based on the tool
            llm_agent = self.get_processor(AgentType.LLM_QUERY)
            if llm_agent:
                return llm_agent.handle_tool_completion(request_id, original_query)
                
            error_msg = "LLM agent not available to handle tool completion"
            logger.error(error_msg)
            return {"response": f"Error: {error_msg}", "status": "error"}
            
        except Exception as e:
            error_msg = f"Error handling tool completion: {e}"
            logger.error(error_msg)
            return {"response": f"Error: {error_msg}", "status": "error"}
            
    def check_pending_tools(self):
        """
        Check for pending tool requests across all processors.
        
        Returns:
            List of completed tool requests
        """
        try:
            # For now, we just pass this to the LLM query agent
            llm_agent = self.get_processor(AgentType.LLM_QUERY)
            if llm_agent:
                return llm_agent.check_pending_tools()
                
            return None
            
        except Exception as e:
            logger.error(f"Error checking pending tools: {e}")
            return None

    def set_conversation_id(self, conversation_id: str):
        """
        Set the conversation ID on this agent and all sub-processors.
        
        Args:
            conversation_id: The conversation ID to set
        """
        logger.debug(f"Setting conversation_id on orchestrator and all processors: {conversation_id}")
        
        # Set on this agent
        self.conversation_id = conversation_id
        self.session_id = conversation_id  # Alias for compatibility
        
        # Set on all processors
        for processor_type, processor in self.agents.items():
            if hasattr(processor, 'conversation_id'):
                processor.conversation_id = conversation_id
                logger.debug(f"Set conversation_id on {processor_type.value}: {conversation_id}")
            if hasattr(processor, 'session_id'):
                processor.session_id = conversation_id
                logger.debug(f"Set session_id on {processor_type.value}: {conversation_id}")
        
        return True

def orchestrator_node(state) -> Dict[str, Any]:
    """
    Node function for the orchestrator in the LangGraph.
    
    Args:
        state: The current state of the graph
        
    Returns:
        Updated state or next actions
    """
    # This is a stub for future integration with LangGraph's StateGraph
    # In the future, this would contain the logic to:
    # 1. Analyze the current state
    # 2. Determine next actions
    # 3. Route to appropriate agents
    # 4. Return updated state
    
    logger.debug("Orchestrator node called with state")
    return {}

# For direct execution testing
if __name__ == "__main__":
    print("Testing OrchestratorAgent initialization...")
    orchestrator = OrchestratorAgent()
    print(f"Orchestrator initialized with model: {orchestrator.model}")
    print("Try running 'python -m src.run_cli' to start the CLI interface.")
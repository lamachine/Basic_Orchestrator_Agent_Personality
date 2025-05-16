"""
Central Decision Making Module

This module provides a central decision-making system for the agent, leveraging:
1. LLM for reasoning and Chain of Thought (CoT) processing
2. Memory integration with Mem0 for context and history
3. Structured decision frameworks for making complex choices
4. RAG for enhanced context retrieval and prompt enrichment

The central decision maker evaluates multiple factors:
- User requests and intent
- Current state
- Historical context from memory
- Available tools and capabilities
- Previous interactions
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple, Union

from ..managers.memory_manager import Mem0Memory, SwarmMessage
from ..state.state_manager import StateManager
from ..tools.tool_utils import ToolResponse
from ..rag.rag_engine import RagEngine

logger = logging.getLogger(__name__)

# Decision outcome types
DECISION_EXECUTE_TOOL = "execute_tool"  # Execute a specific tool
DECISION_RESPOND = "respond"            # Respond directly to the user
DECISION_CLARIFY = "clarify"            # Ask for clarification
DECISION_DEFER = "defer"                # Defer to another system/agent


class DecisionContext:
    """
    Container for all context needed to make a decision.
    """
    def __init__(
        self,
        user_id: str,
        user_message: str,
        current_state: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        previous_interactions: List[Dict[str, Any]] = None,
        memory_context: List[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.user_id = user_id
        self.user_message = user_message
        self.current_state = current_state
        self.available_tools = available_tools
        self.previous_interactions = previous_interactions or []
        self.memory_context = memory_context or []
        self.request_id = request_id
        self.metadata = metadata or {}


class DecisionResult:
    """
    Container for the result of a decision.
    """
    def __init__(
        self,
        decision_type: str,
        confidence: float,
        reasoning: str,
        action: Dict[str, Any],
        alternative_actions: List[Dict[str, Any]] = None,
    ):
        self.decision_type = decision_type
        self.confidence = confidence
        self.reasoning = reasoning
        self.action = action
        self.alternative_actions = alternative_actions or []


class CentralDecisionMaker:
    """
    Central decision-making system that coordinates:
    - LLM reasoning
    - Memory access
    - State management
    - Tool selection and execution
    - RAG-enhanced context retrieval
    """
    
    def __init__(
        self,
        state_manager: StateManager,
        memory_manager: Optional[Mem0Memory] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the central decision maker.
        
        Args:
            state_manager: StateManager instance for accessing and updating state
            memory_manager: Optional Mem0Memory instance for memory operations
            config: Optional configuration parameters
        """
        self.state_manager = state_manager
        self.memory_manager = memory_manager
        self.config = config or {}
        
        # Default confidence thresholds
        self.min_confidence_for_action = self.config.get("min_confidence_for_action", 0.7)
        self.min_confidence_for_tools = self.config.get("min_confidence_for_tools", 0.8)
        
        # Initialize RAG engine if memory manager is available
        self.rag_engine = RagEngine(memory_manager) if memory_manager else None

    def _retrieve_relevant_memories(self, user_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for the current context.
        
        Args:
            user_id: ID of the user
            query: Query to search for relevant memories
            top_k: Number of top memories to retrieve
            
        Returns:
            List of relevant memories
        """
        # Use RAG engine if available, otherwise fall back to basic memory search
        if self.rag_engine:
            context_result = self.rag_engine.retrieve_context(
                query=query,
                user_id=user_id,
                limit=top_k
            )
            return context_result.get("context", [])
        
        elif self.memory_manager:
            try:
                search_results = self.memory_manager.search_memory(
                    query=query,
                    top_k=top_k,
                    user_id=user_id
                )
                
                return search_results.get("results", [])
            except Exception as e:
                logger.warning(f"Failed to retrieve memories: {e}")
                return []
        
        return []
    
    def _add_interaction_to_memory(
        self,
        user_id: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add an interaction to memory.
        
        Args:
            user_id: ID of the user
            message: Message content
            metadata: Optional metadata for the memory
            
        Returns:
            True if memory was successfully added, False otherwise
        """
        # Use RAG engine if available for enhanced context storage
        if self.rag_engine:
            context_type = metadata.get("type", "conversation") if metadata else "conversation"
            return self.rag_engine.store_context(
                content=message,
                user_id=user_id,
                context_type=context_type,
                metadata=metadata
            )
        
        elif self.memory_manager:
            try:
                message_obj = SwarmMessage(
                    content=message,
                    user_id=user_id,
                    metadata=metadata or {}
                )
                
                result = self.memory_manager.add_memory(message_obj)
                return True
            except Exception as e:
                logger.warning(f"Failed to add memory: {e}")
                return False
                
        return False
    
    def _format_cot_prompt(
        self,
        context: DecisionContext,
        memories: List[Dict[str, Any]]
    ) -> str:
        """
        Format a Chain of Thought prompt for decision making.
        
        Args:
            context: Decision context
            memories: Relevant memories
            
        Returns:
            Formatted prompt string
        """
        # Create base prompt
        base_prompt = f"""
You are an intelligent agent assistant that uses reasoning to make decisions. 
The user (ID: {context.user_id}) has sent the following message:

"{context.user_message}"

## Available Tools
The following tools are available to help the user:
"""
        
        for idx, tool in enumerate(context.available_tools):
            base_prompt += f"""
{idx+1}. {tool.get('name', 'Unknown Tool')}
   Description: {tool.get('description', 'No description')}
   Parameters: {json.dumps(tool.get('parameters', {}), indent=2)}
"""
            
        # Add current state information
        base_prompt += """
## Current State
"""
        
        # Format current state
        for key, value in context.current_state.items():
            base_prompt += f"{key}: {value}\n"
            
        # Add previous interactions
        base_prompt += """
## Previous Interactions
"""
        
        for idx, interaction in enumerate(context.previous_interactions[-3:]):  # Last 3 interactions
            base_prompt += f"Interaction {idx+1}: {interaction.get('role', 'unknown')}: {interaction.get('content', '')}\n"
        
        # Add decision-making instructions
        decision_instructions = """
## Decision-Making Process
Think step by step about the best way to assist the user:

1. Understand the user's request in detail
2. Consider relevant memories and previous context
3. Evaluate if clarification is needed
4. Determine if a tool should be executed, and if so, which one
5. Decide on the parameters for the tool
6. Assess if a direct response is more appropriate

Please organize your thoughts clearly through each step, then make a final decision about what action to take. Your decision should be one of:
- EXECUTE_TOOL: Run a specific tool with parameters
- RESPOND: Provide a direct response to the user
- CLARIFY: Ask the user for clarification
- DEFER: Defer to another agent or system

## Your Reasoning:
"""
        
        # Use RAG engine to enrich the prompt if available
        if self.rag_engine and context.user_message:
            # Try to get an enriched prompt with context
            return self.rag_engine.enrich_prompt(
                base_prompt=base_prompt + decision_instructions,
                query=context.user_message,
                user_id=context.user_id,
                limit=5
            )
        
        # Otherwise, add memories directly
        memory_section = """
## Relevant Memories
The following memories about the user may be relevant:
"""
        
        if memories:
            for idx, memory in enumerate(memories):
                memory_content = memory.get('content', memory.get('memory', 'No content'))
                memory_section += f"""
Memory {idx+1}: {memory_content}
  Relevance score: {memory.get('similarity', memory.get('relevance', 0))}
"""
        else:
            memory_section += "No relevant memories found.\n"
            
        return base_prompt + memory_section + decision_instructions
    
    def _parse_llm_response(self, response: str) -> Tuple[str, float, str, Dict[str, Any]]:
        """
        Parse the LLM's reasoning and decision.
        
        Args:
            response: LLM response with reasoning and decision
            
        Returns:
            Tuple of (decision_type, confidence, reasoning, action)
        """
        # In a real implementation, you'd use more robust parsing
        # This is a simplified version
        
        reasoning = response
        
        # Default values in case parsing fails
        decision_type = DECISION_RESPOND
        confidence = 0.5
        action = {"response": "I need to consider how best to help you."}
        
        # Look for decision pattern
        if "EXECUTE_TOOL" in response:
            decision_type = DECISION_EXECUTE_TOOL
            confidence = 0.85  # Example confidence
            
            # Simple parsing - in real implementation, use regex or better parsing
            if "tool:" in response.lower():
                tool_section = response.lower().split("tool:")[1].split("\n")[0].strip()
                action = {"tool": tool_section, "parameters": {}}
                
                # Try to extract parameters - simplified
                if "parameters:" in response.lower():
                    param_section = response.lower().split("parameters:")[1].strip()
                    try:
                        # This is simplified - real implementation would be more robust
                        param_lines = param_section.split("\n")
                        for line in param_lines:
                            if ":" in line:
                                k, v = line.split(":", 1)
                                action["parameters"][k.strip()] = v.strip()
                    except Exception as e:
                        logger.warning(f"Failed to parse parameters: {e}")
            
        elif "CLARIFY" in response:
            decision_type = DECISION_CLARIFY
            confidence = 0.7
            
            # Extract clarification question
            if "question:" in response.lower():
                question = response.lower().split("question:")[1].split("\n")[0].strip()
                action = {"clarification_question": question}
                
        elif "DEFER" in response:
            decision_type = DECISION_DEFER
            confidence = 0.6
            
            # Extract target
            if "target:" in response.lower():
                target = response.lower().split("target:")[1].split("\n")[0].strip()
                action = {"target": target, "reason": "Need specialized expertise"}
                
        else:  # Default to RESPOND
            decision_type = DECISION_RESPOND
            confidence = 0.75
            
            # Try to extract the response content - simplified
            last_section = response.split("\n\n")[-1]
            action = {"response": last_section}
            
        return decision_type, confidence, reasoning, action
        
    def _execute_llm_for_decision(self, prompt: str) -> str:
        """
        Execute the LLM to make a decision based on the prompt.
        
        In a real implementation, this would call out to an actual LLM.
        
        Args:
            prompt: The formatted prompt to send to the LLM
            
        Returns:
            The LLM's response
        """
        # In a real implementation, connect to your LLM here
        # This is a mock response
        
        # Simplified example response - real LLM would provide detailed reasoning
        response = """
I'll analyze this step by step:

1. Understanding the request: The user wants information about X.
2. Reviewing memories: The user has previously expressed interest in Y.
3. Evaluating available tools: The search_knowledge_base tool seems most appropriate.
4. Parameter selection: I need to search for X in relation to Y.

Based on this reasoning, I'll use the search_knowledge_base tool to find relevant information.

Decision: EXECUTE_TOOL
Tool: search_knowledge_base
Parameters:
query: X in relation to Y
filter: recent
max_results: 5
"""
        return response
    
    def make_decision(self, context: DecisionContext) -> DecisionResult:
        """
        Make a decision based on the provided context.
        
        Args:
            context: Complete decision context
            
        Returns:
            DecisionResult with decision details
        """
        # 1. Retrieve relevant memories
        memories = self._retrieve_relevant_memories(
            user_id=context.user_id,
            query=context.user_message
        )
        
        # 2. Format the Chain of Thought prompt
        prompt = self._format_cot_prompt(context, memories)
        
        # 3. Execute the LLM to make a decision
        llm_response = self._execute_llm_for_decision(prompt)
        
        # 4. Parse the LLM's response
        decision_type, confidence, reasoning, action = self._parse_llm_response(llm_response)
        
        # 5. Create and return the decision result
        result = DecisionResult(
            decision_type=decision_type,
            confidence=confidence,
            reasoning=reasoning,
            action=action
        )
        
        # 6. Store the decision in memory
        decision_summary = f"Decision made: {decision_type} with confidence {confidence}"
        self._add_interaction_to_memory(
            user_id=context.user_id,
            message=decision_summary,
            metadata={
                "type": "decision", 
                "decision_type": decision_type,
                "confidence": confidence,
                "request_id": context.request_id
            }
        )
        
        return result
    
    def evaluate_tool_response(
        self, 
        context: DecisionContext,
        tool_response: ToolResponse,
        original_decision: DecisionResult
    ) -> DecisionResult:
        """
        Evaluate a tool response and decide on next steps.
        
        Args:
            context: Original decision context
            tool_response: Response from the executed tool
            original_decision: The decision that led to the tool execution
            
        Returns:
            A new decision result based on evaluating the tool response
        """
        # Create an updated context with the tool response
        updated_context = DecisionContext(
            user_id=context.user_id,
            user_message=context.user_message,
            current_state=context.current_state,
            available_tools=context.available_tools,
            previous_interactions=context.previous_interactions,
            memory_context=context.memory_context,
            request_id=context.request_id,
            metadata={
                **context.metadata,
                "tool_response": tool_response.to_dict() if hasattr(tool_response, "to_dict") else tool_response
            }
        )
        
        # Add the tool response to memory for future context
        tool_response_content = str(tool_response)
        self._add_interaction_to_memory(
            user_id=context.user_id,
            message=f"Tool response: {tool_response_content}",
            metadata={
                "type": "tool_response",
                "tool": original_decision.action.get("tool", "unknown_tool"),
                "request_id": context.request_id,
                "context_type": "task"  # Mark as task-related for better retrieval
            }
        )
        
        # Format a specialized prompt for evaluating the tool response
        evaluation_base_prompt = f"""
You previously decided to execute the tool '{original_decision.action.get("tool", "unknown")}' with these parameters:
{json.dumps(original_decision.action.get("parameters", {}), indent=2)}

The tool returned the following response:
{tool_response_content}

Based on this tool response and the original user request:
"{context.user_message}"

Please decide what to do next:
1. RESPOND: Provide a direct response to the user based on the tool results
2. EXECUTE_TOOL: Run another tool to get more information
3. CLARIFY: Ask the user for more information

## Your Reasoning:
"""
        
        # Use RAG engine for context-aware evaluation if available
        if self.rag_engine:
            # Get an enriched evaluation prompt that includes relevant context
            evaluation_prompt = self.rag_engine.enrich_prompt(
                base_prompt=evaluation_base_prompt,
                query=f"{context.user_message} {tool_response_content}",  # Combine original query with response
                user_id=context.user_id,
                context_type="task",  # Focus on task-related memories
                limit=3  # Smaller context window for focused evaluation
            )
        else:
            evaluation_prompt = evaluation_base_prompt
        
        # Execute the LLM to evaluate the tool response
        llm_evaluation = self._execute_llm_for_decision(evaluation_prompt)
        
        # Parse the LLM's evaluation
        decision_type, confidence, reasoning, action = self._parse_llm_response(llm_evaluation)
        
        # Create and return the follow-up decision
        result = DecisionResult(
            decision_type=decision_type,
            confidence=confidence,
            reasoning=reasoning,
            action=action
        )
        
        return result 
"""
RAG (Retrieval Augmented Generation) Engine

This module provides enhanced retrieval capabilities for the agent, building on 
the Mem0Memory system to offer:
1. Contextual information retrieval
2. Privacy-aware search
3. Cross-conversation references
4. Structured knowledge organization

The RAG engine acts as a bridge between the raw memory/vector storage and the 
decision-making process, providing relevant context for LLM reasoning.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime

from ..managers.memory_manager import Mem0Memory, SwarmMessage

logger = logging.getLogger(__name__)

class RagEngine:
    """
    Enhanced retrieval system for providing contextual information to the agent.
    
    This class builds on the Mem0Memory system to provide more sophisticated
    retrieval capabilities specifically designed for LLM context augmentation.
    """
    
    def __init__(
        self,
        memory_manager: Mem0Memory,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the RAG engine.
        
        Args:
            memory_manager: Mem0Memory instance for memory operations
            config: Optional configuration parameters
        """
        self.memory_manager = memory_manager
        self.config = config or {}
        
        # Configuration parameters
        self.default_context_window = self.config.get("default_context_window", 5)
        self.default_search_limit = self.config.get("default_search_limit", 10)
        self.similarity_threshold = self.config.get("similarity_threshold", 0.7)
        self.enable_cross_user = self.config.get("enable_cross_user", False)
    
    def retrieve_context(
        self,
        query: str,
        user_id: str,
        context_type: str = "all",
        limit: int = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        include_metadata: bool = True,
        conversation_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Retrieve contextual information based on a query.
        
        Args:
            query: The search query
            user_id: User ID for privacy filtering
            context_type: Type of context to retrieve ("all", "conversation", "knowledge", "task")
            limit: Maximum number of results to return (defaults to config value)
            time_range: Optional tuple of (start_time, end_time) to filter by
            include_metadata: Whether to include metadata in results
            conversation_id: Optional conversation ID to limit search to
            filters: Additional filters to apply to the search
            
        Returns:
            Dictionary with retrieved context information
        """
        if not self.memory_manager:
            logger.warning("No memory manager available for RAG retrieval")
            return {"context": [], "metadata": {"success": False, "reason": "No memory manager available"}}
        
        limit = limit or self.default_search_limit
        filters = filters or {}
        
        # Construct metadata filters based on parameters
        metadata_filters = {}
        
        if conversation_id:
            metadata_filters["conversation_id"] = conversation_id
            
        if context_type != "all":
            metadata_filters["context_type"] = context_type
            
        # Combine with user-provided filters
        metadata_filters.update(filters)
        
        try:
            # Call the memory manager's search function with our enhanced parameters
            search_results = self.memory_manager.search_memory(
                query=query,
                top_k=limit,
                user_id=user_id,
                # We would ideally pass metadata_filters here, but if the underlying
                # implementation doesn't support it, we'll filter after retrieval
            )
            
            results = search_results.get("results", [])
            
            # Apply post-retrieval filtering for metadata if needed
            if metadata_filters and results:
                filtered_results = []
                for result in results:
                    result_metadata = result.get("metadata", {})
                    
                    # Check if all filters match
                    is_match = all(
                        result_metadata.get(key) == value 
                        for key, value in metadata_filters.items()
                    )
                    
                    if is_match:
                        filtered_results.append(result)
                
                results = filtered_results
            
            # Apply similarity threshold filtering
            if self.similarity_threshold > 0:
                results = [
                    r for r in results 
                    if r.get("similarity", 0) >= self.similarity_threshold
                ]
            
            # Apply time range filtering if specified
            if time_range and results:
                start_time, end_time = time_range
                filtered_results = []
                
                for result in results:
                    result_metadata = result.get("metadata", {})
                    timestamp_str = result_metadata.get("timestamp")
                    
                    if not timestamp_str:
                        continue
                        
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                        if start_time <= timestamp <= end_time:
                            filtered_results.append(result)
                    except (ValueError, TypeError):
                        # Skip results with invalid timestamps
                        continue
                
                results = filtered_results
            
            # Format and return the context information
            context_items = []
            
            for result in results:
                context_item = {
                    "content": result.get("content", ""),
                    "relevance": result.get("similarity", 0),
                }
                
                if include_metadata:
                    context_item["metadata"] = result.get("metadata", {})
                    
                context_items.append(context_item)
            
            return {
                "context": context_items,
                "metadata": {
                    "success": True,
                    "count": len(context_items),
                    "query": query,
                    "filters": metadata_filters
                }
            }
            
        except Exception as e:
            logger.error(f"Error retrieving RAG context: {str(e)}")
            return {
                "context": [],
                "metadata": {
                    "success": False,
                    "reason": str(e),
                    "query": query
                }
            }
    
    def enrich_prompt(
        self,
        base_prompt: str,
        query: str,
        user_id: str,
        context_type: str = "all",
        limit: int = None,
        include_source: bool = True,
        custom_template: Optional[str] = None
    ) -> str:
        """
        Enrich a prompt with retrieved context.
        
        Args:
            base_prompt: The original prompt template
            query: Query to search for relevant context
            user_id: User ID for privacy filtering
            context_type: Type of context to retrieve
            limit: Maximum number of context items to include
            include_source: Whether to include source information
            custom_template: Optional custom template for context formatting
            
        Returns:
            Enriched prompt with context
        """
        # Retrieve context
        context_result = self.retrieve_context(
            query=query,
            user_id=user_id,
            context_type=context_type,
            limit=limit or self.default_context_window
        )
        
        context_items = context_result.get("context", [])
        
        if not context_items:
            # If no context found, return the original prompt with a note
            return f"{base_prompt}\n\n[No relevant context found for this query]"
        
        # Format context for inclusion in the prompt
        context_section = "\n## Relevant Context\n\n"
        
        for i, item in enumerate(context_items):
            relevance = item.get("relevance", 0)
            relevance_str = f"[Relevance: {relevance:.2f}]" if relevance else ""
            
            context_section += f"Context {i+1}: {relevance_str}\n{item['content']}\n\n"
            
            # Add source information if requested
            if include_source and "metadata" in item:
                metadata = item["metadata"]
                source_info = []
                
                if "timestamp" in metadata:
                    try:
                        timestamp = datetime.fromisoformat(metadata["timestamp"])
                        source_info.append(f"Time: {timestamp.strftime('%Y-%m-%d %H:%M')}")
                    except (ValueError, TypeError):
                        pass
                
                if "source" in metadata:
                    source_info.append(f"Source: {metadata['source']}")
                
                if "context_type" in metadata:
                    source_info.append(f"Type: {metadata['context_type']}")
                
                if source_info:
                    context_section += f"Source: {' | '.join(source_info)}\n\n"
        
        # Combine with the base prompt
        enriched_prompt = f"{base_prompt}\n{context_section}"
        
        return enriched_prompt
    
    def store_context(
        self,
        content: str,
        user_id: str,
        context_type: str = "conversation",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store new context in the memory system.
        
        Args:
            content: The content to store
            user_id: User ID for privacy
            context_type: Type of context ("conversation", "knowledge", "task")
            metadata: Additional metadata
            
        Returns:
            True if successfully stored, False otherwise
        """
        if not self.memory_manager:
            logger.warning("No memory manager available for storing context")
            return False
        
        try:
            # Prepare metadata
            combined_metadata = {
                "timestamp": datetime.now().isoformat(),
                "context_type": context_type
            }
            
            # Add custom metadata
            if metadata:
                combined_metadata.update(metadata)
            
            # Create message object
            message = SwarmMessage(
                content=content,
                user_id=user_id,
                metadata=combined_metadata
            )
            
            # Store in memory
            result = self.memory_manager.add_memory(message)
            return True
            
        except Exception as e:
            logger.error(f"Error storing context: {str(e)}")
            return False

    def get_conversation_history(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        limit: int = 10,
        include_metadata: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history.
        
        Args:
            user_id: User ID
            conversation_id: Optional specific conversation ID
            limit: Maximum number of messages to retrieve
            include_metadata: Whether to include metadata
            
        Returns:
            List of conversation messages
        """
        if not self.memory_manager:
            logger.warning("No memory manager available for conversation history")
            return []
        
        try:
            # Get memories with appropriate filtering
            all_memories = self.memory_manager.get_all_memories(user_id=user_id)
            memories = all_memories.get("memories", [])
            
            # Apply conversation_id filter if provided
            if conversation_id and memories:
                memories = [
                    m for m in memories
                    if m.get("metadata", {}).get("conversation_id") == conversation_id
                ]
            
            # Apply context_type filter for conversations
            memories = [
                m for m in memories
                if m.get("metadata", {}).get("context_type") == "conversation"
            ]
            
            # Sort by timestamp (newest first)
            try:
                memories.sort(
                    key=lambda m: datetime.fromisoformat(
                        m.get("metadata", {}).get("timestamp", "2000-01-01T00:00:00")
                    ),
                    reverse=True
                )
            except (ValueError, TypeError):
                # If sorting fails, keep original order
                pass
            
            # Limit number of results
            memories = memories[:limit]
            
            # Format results
            results = []
            for memory in memories:
                result = {
                    "content": memory.get("memory", memory.get("content", "")),
                    "role": memory.get("metadata", {}).get("role", "unknown")
                }
                
                if include_metadata:
                    result["metadata"] = memory.get("metadata", {})
                    
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {str(e)}")
            return [] 
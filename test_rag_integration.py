"""
Test script for RAG integration with Mem0.

This script verifies the RAG engine works properly with the Mem0 memory system,
providing enhanced context retrieval for the agent.
"""

import os
import sys
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta

try:
    from mem0 import Memory
    print("Successfully imported Memory class from mem0")
except ImportError as e:
    print(f"Failed to import Memory from mem0: {e}")
    print("Please install mem0: pip install mem0")
    sys.exit(1)

try:
    from src.sub_graphs.template_agent.src.common.managers.memory_manager import Mem0Memory, SwarmMessage
    from src.sub_graphs.template_agent.src.common.rag.rag_engine import RagEngine
    print("Successfully imported Mem0Memory, SwarmMessage, and RagEngine")
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    sys.exit(1)

def test_rag_with_memory():
    """Test RAG engine with Mem0Memory integration."""
    
    # Initialize the memory manager
    config_path = "mem0.config.json"
    
    # Verify config file exists
    if not os.path.exists(config_path):
        print(f"✗ Error: Config file {config_path} not found!")
        print(f"  Please make sure the mem0.config.json file exists with proper configuration.")
        sys.exit(1)
    
    # Initialize memory manager and RAG engine
    try:
        memory_manager = Mem0Memory(config_path=config_path)
        print("✓ Successfully initialized Mem0Memory")
        
        rag_engine = RagEngine(memory_manager=memory_manager)
        print("✓ Successfully initialized RAG engine")
        
        # Test setup
        user_id = "test_user"
        current_time = datetime.now()
        
        # Add some test memories for context
        memories = [
            {
                "content": "I enjoy reading science fiction books, especially those by Neal Stephenson.",
                "metadata": {"source": "test", "category": "preferences", "context_type": "knowledge"}
            },
            {
                "content": "My favorite movie is Inception because I love the complex plot.",
                "metadata": {"source": "test", "category": "preferences", "context_type": "knowledge"}
            },
            {
                "content": "I need to finish my report by Friday.",
                "metadata": {"source": "test", "category": "tasks", "context_type": "task"}
            },
            {
                "content": "User: What science fiction books would you recommend?\nAssistant: I would recommend books by Neal Stephenson.",
                "metadata": {"source": "conversation", "timestamp": (current_time - timedelta(days=2)).isoformat(), "context_type": "conversation"}
            },
            {
                "content": "User: What movies are good for people who like complex plots?\nAssistant: You might enjoy Inception or other Christopher Nolan films.",
                "metadata": {"source": "conversation", "timestamp": (current_time - timedelta(days=1)).isoformat(), "context_type": "conversation"}
            }
        ]
        
        # Add test memories to the system
        print("\nAdding test memories...")
        for i, mem in enumerate(memories):
            message = SwarmMessage(
                content=mem["content"],
                user_id=user_id,
                metadata=mem["metadata"]
            )
            try:
                result = memory_manager.add_memory(message)
                print(f"✓ Added memory {i+1}")
            except Exception as e:
                print(f"✗ Failed to add memory {i+1}: {e}")
                import traceback
                traceback.print_exc()
        
        # 1. Test basic context retrieval
        print("\nTesting RAG context retrieval...")
        query = "What kind of books do I like?"
        
        try:
            context_result = rag_engine.retrieve_context(
                query=query,
                user_id=user_id,
                limit=5
            )
            
            context_items = context_result.get("context", [])
            print(f"✓ Successfully retrieved context for query: '{query}'")
            print(f"  Found {len(context_items)} context items")
            
            for i, item in enumerate(context_items):
                print(f"  Item {i+1}: {item.get('content', '')} (Relevance: {item.get('relevance', 0):.2f})")
                if 'metadata' in item:
                    md = item['metadata']
                    print(f"    Type: {md.get('context_type', 'unknown')}, Source: {md.get('source', 'unknown')}")
        except Exception as e:
            print(f"✗ Failed to retrieve context: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
            
        # 2. Test prompt enrichment
        print("\nTesting prompt enrichment...")
        base_prompt = "You are a helpful assistant. The user has asked: 'Can you recommend some science fiction books?'"
        
        try:
            enriched_prompt = rag_engine.enrich_prompt(
                base_prompt=base_prompt,
                query="science fiction books recommendations",
                user_id=user_id,
                limit=3
            )
            
            print(f"✓ Successfully enriched prompt")
            print(f"  Original length: {len(base_prompt)} characters")
            print(f"  Enriched length: {len(enriched_prompt)} characters")
            print(f"  Added {len(enriched_prompt) - len(base_prompt)} characters of context")
        except Exception as e:
            print(f"✗ Failed to enrich prompt: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        # 3. Test filtered context retrieval
        print("\nTesting filtered context retrieval...")
        
        try:
            task_context = rag_engine.retrieve_context(
                query="report deadline",
                user_id=user_id,
                context_type="task",
                limit=2
            )
            
            task_items = task_context.get("context", [])
            print(f"✓ Successfully retrieved task context")
            print(f"  Found {len(task_items)} task items")
            
            for i, item in enumerate(task_items):
                print(f"  Task {i+1}: {item.get('content', '')}")
        except Exception as e:
            print(f"✗ Failed to retrieve filtered context: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        # 4. Test conversation history retrieval
        print("\nTesting conversation history retrieval...")
        
        try:
            conversations = rag_engine.get_conversation_history(
                user_id=user_id,
                limit=5
            )
            
            print(f"✓ Successfully retrieved conversation history")
            print(f"  Found {len(conversations)} conversations")
            
            for i, conv in enumerate(conversations):
                print(f"  Conversation {i+1}: {conv.get('content', '')}")
        except Exception as e:
            print(f"✗ Failed to retrieve conversation history: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        # 5. Test storing new context
        print("\nTesting context storage...")
        
        try:
            success = rag_engine.store_context(
                content="I need to buy groceries tomorrow.",
                user_id=user_id,
                context_type="task",
                metadata={"priority": "medium", "due": "tomorrow"}
            )
            
            if success:
                print(f"✓ Successfully stored new context")
                
                # Verify it was stored by retrieving it
                verification = rag_engine.retrieve_context(
                    query="groceries",
                    user_id=user_id,
                    context_type="task",
                    limit=1
                )
                
                if verification.get("context") and len(verification["context"]) > 0:
                    print(f"✓ Verified context was stored: {verification['context'][0].get('content', '')}")
                else:
                    print(f"✗ Could not verify context was stored")
            else:
                print(f"✗ Failed to store context")
        except Exception as e:
            print(f"✗ Error during context storage test: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
            
        print("\nRAG integration with Mem0 is working correctly!")
        
    except Exception as e:
        print(f"✗ Failed to initialize or use RAG engine: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("Testing RAG integration with Mem0...")
    test_rag_with_memory() 
"""
Test script for Mem0 with Supabase integration.

This script demonstrates how to use Mem0 for memory management with the
existing Supabase configuration and the agent_memories table.
"""

import os
import sys
import json
from typing import Dict, Any

try:
    from mem0 import Memory
    print("Successfully imported Memory class from mem0")
except ImportError as e:
    print(f"Failed to import Memory from mem0: {e}")
    print("Please install mem0: pip install mem0")
    sys.exit(1)

try:
    from src.sub_graphs.template_agent.src.common.managers.memory_manager import Mem0Memory, SwarmMessage
    print("Successfully imported Mem0Memory and SwarmMessage from memory_manager")
except ImportError as e:
    print(f"Failed to import from memory_manager: {e}")
    sys.exit(1)

def test_memory_with_supabase():
    """Test Mem0Memory with Supabase integration."""
    
    # Initialize the memory manager
    config_path = "mem0.config.json"
    
    # Verify config file exists
    if not os.path.exists(config_path):
        print(f"✗ Error: Config file {config_path} not found!")
        print(f"  Please make sure the mem0.config.json file exists with proper Supabase configuration.")
        sys.exit(1)
    
    # Verify config contains proper Supabase configuration
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        # Check if it has vector_store with Supabase provider
        if "vector_store" not in config or config["vector_store"].get("provider") != "supabase":
            print(f"⚠ Warning: Configuration may not be set up for Supabase correctly.")
            print(f"  Current vector_store provider: {config.get('vector_store', {}).get('provider')}")
            
        # Check if collection_name is agent_memories
        collection_name = config.get("vector_store", {}).get("config", {}).get("collection_name")
        if collection_name != "agent_memories":
            print(f"⚠ Warning: Collection name is {collection_name}, not 'agent_memories'")
        else:
            print(f"✓ Configuration has correct collection name: {collection_name}")
            
        print(f"✓ Successfully loaded configuration from {config_path}")
    except Exception as e:
        print(f"✗ Error loading configuration: {e}")
        sys.exit(1)
    
    # Initialize Mem0Memory
    try:
        memory_manager = Mem0Memory(config_path=config_path)
        print("✓ Successfully initialized Mem0Memory")
        
        # If memory object was created, we have SDK working
        if memory_manager.memory:
            print("✓ Successfully initialized Memory class from Mem0 SDK")
        elif memory_manager.client:
            print("✓ Successfully initialized MemoryClient from Mem0 SDK")
        else:
            print("⚠ Warning: Using CLI fallback mode - SDK initialization failed")
        
        # Test basic operations with the memory manager
        user_id = "test_user"
        
        # 1. Test adding memory
        print("\nTesting add memory...")
        message = SwarmMessage(
            content="I enjoy reading science fiction books, especially those by Neal Stephenson.",
            user_id=user_id,
            metadata={"source": "test", "category": "preferences"}
        )
        
        try:
            result = memory_manager.add_memory(message)
            print(f"✓ Successfully added memory: {result}")
        except Exception as e:
            print(f"✗ Failed to add memory: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        # 2. Test searching memory
        print("\nTesting search memory...")
        query = "What are my reading preferences?"
        
        try:
            results = memory_manager.search_memory(query, user_id=user_id)
            print(f"✓ Successfully searched memory with query: '{query}'")
            print(f"  Found {len(results.get('results', []))} results")
            for idx, item in enumerate(results.get("results", [])):
                print(f"  Result {idx+1}: {item.get('content', '')} (Score: {item.get('similarity', 0)})")
        except Exception as e:
            print(f"✗ Failed to search memory: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        # 3. Test getting all memories
        print("\nTesting get all memories...")
        
        try:
            all_memories = memory_manager.get_all_memories(user_id=user_id)
            memories = all_memories.get("memories", [])
            print(f"✓ Successfully retrieved all memories for user: {user_id}")
            print(f"  Found {len(memories)} memories")
        except Exception as e:
            print(f"✗ Failed to get all memories: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
            
        print("\nMem0 with Supabase integration is working correctly!")
        
    except Exception as e:
        print(f"✗ Failed to initialize or use Mem0Memory: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("Testing Mem0 with Supabase integration...")
    test_memory_with_supabase() 
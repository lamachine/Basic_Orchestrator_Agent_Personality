"""
Test script for Mem0 with local storage and Llama models.

This script demonstrates how to use Mem0 for memory management with local storage
and local LLMs (Llama models running through Ollama).
"""

import json
import os
import sys
from typing import Any, Dict

try:
    from mem0 import Memory

    print("Successfully imported Memory class from mem0")
except ImportError as e:
    print(f"Failed to import Memory from mem0: {e}")
    print("Please install mem0: pip install mem0")
    sys.exit(1)


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from a JSON file."""
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        print(f"✓ Successfully loaded configuration from {config_path}")
        return config
    except Exception as e:
        print(f"✗ Failed to load configuration from {config_path}: {e}")
        sys.exit(1)


def test_memory_with_local_llama():
    """Test Mem0 Memory with local Llama models through Ollama."""
    # Load configuration
    config_path = "mem0_local.config.json"
    config = load_config(config_path)

    # Check if Ollama is available
    try:
        import requests

        ollama_url = config["llm"]["config"]["ollama_base_url"]
        response = requests.get(f"{ollama_url}/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✓ Ollama is available with models: {[m.get('name') for m in models]}")
            llama_model = config["llm"]["config"]["model"]
            if not any(m.get("name", "").startswith(llama_model) for m in models):
                print(f"⚠ Warning: Model '{llama_model}' not found in Ollama. You may need to run:")
                print(f"  ollama pull {llama_model}")
        else:
            print(f"⚠ Warning: Ollama is running but returned status code {response.status_code}")
    except Exception as e:
        print(
            f"⚠ Warning: Could not connect to Ollama at {config['llm']['config']['ollama_base_url']}: {e}"
        )
        print("  Please make sure Ollama is running with 'ollama serve'")

    # Initialize Memory with configuration
    try:
        memory = Memory.from_config(config)
        print("✓ Successfully initialized Memory with local configuration")

        # Test basic operations
        user_id = "test_user"

        # 1. Test adding memory
        print("\nTesting add memory...")
        result = memory.add(
            "I enjoy reading science fiction books, especially those by Neal Stephenson.",
            user_id=user_id,
        )
        print(f"✓ Successfully added memory: {result}")

        # 2. Test searching memory
        print("\nTesting search memory...")
        query = "What are my reading preferences?"
        results = memory.search(query, user_id=user_id)
        print(f"✓ Successfully searched memory with query: '{query}'")
        print(f"  Results: {json.dumps(results, indent=2)}")

        # 3. Test getting all memories
        print("\nTesting get all memories...")
        all_memories = memory.get_all(user_id=user_id)
        print(f"✓ Successfully retrieved all memories for user: {user_id}")
        print(f"  Found {len(all_memories)} memories")

        print("\nMem0 with local storage and Llama models is working correctly!")

    except Exception as e:
        print(f"✗ Failed to initialize or use Memory: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("Testing Mem0 with local storage and Llama models...")
    test_memory_with_local_llama()

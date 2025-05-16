import os
import sys
import json

try:
    from mem0 import MemoryClient
    print("Successfully imported MemoryClient from mem0")
except ImportError as e:
    print(f"Failed to import from mem0: {e}")
    sys.exit(1)

def test_mem0_api():
    """
    Test basic Mem0 API functionality.
    
    This script requires a MEM0_API_KEY environment variable.
    """
    api_key = os.environ.get("MEM0_API_KEY")
    
    if not api_key:
        print("ERROR: MEM0_API_KEY environment variable not set")
        print("Please set it using:")
        print("export MEM0_API_KEY='your-api-key' (Linux/Mac)")
        print("set MEM0_API_KEY='your-api-key' (Windows CMD)")
        print("$env:MEM0_API_KEY='your-api-key' (Windows PowerShell)")
        return
    
    print(f"Initializing MemoryClient with API key")
    
    try:
        # Initialize client
        client = MemoryClient()
        print("✓ Successfully initialized MemoryClient")
        
        # Check available methods
        expected_methods = ["add", "search", "get_all", "delete"]
        for method in expected_methods:
            if hasattr(client, method) and callable(getattr(client, method)):
                print(f"✓ Found method: {method}")
            else:
                print(f"✗ Missing method: {method}")
        
        # Print client details for debugging
        print("\nClient details:")
        print(f"Client type: {type(client)}")
        print(f"Available methods: {[m for m in dir(client) if not m.startswith('_')]}")
        
    except Exception as e:
        print(f"ERROR initializing or using MemoryClient: {e}")

if __name__ == "__main__":
    print("Testing Mem0 API functionality...")
    test_mem0_api() 
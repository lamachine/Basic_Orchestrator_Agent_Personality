#!/usr/bin/env python
"""
Script to run the Mem0 service in Docker
"""
import os
import subprocess
import sys

def setup_environment():
    """Set up environment variables if not already set"""
    if not os.environ.get("MEM0_API_KEY"):
        api_key = input("Enter your Mem0 API key: ")
        os.environ["MEM0_API_KEY"] = api_key
    
    if not os.environ.get("SUPABASE_KEY"):
        api_key = input("Enter your Supabase key: ")
        os.environ["SUPABASE_KEY"] = api_key

def build_and_run():
    """Build and run the Docker container"""
    print("Building and starting Mem0 service in Docker...")
    try:
        subprocess.run(
            ["docker-compose", "-f", "docker-compose.mem0.yml", "up", "--build", "-d"],
            check=True
        )
        print("\nMem0 service is now running in Docker on port 8009")
        print("Test with: curl -X POST -H 'Content-Type: application/json' -d '{\"method\":\"health\"}' http://localhost:8009/health")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        sys.exit(1)

def stop():
    """Stop the Docker container"""
    print("Stopping Mem0 service...")
    try:
        subprocess.run(
            ["docker-compose", "-f", "docker-compose.mem0.yml", "down"],
            check=True
        )
        print("Mem0 service stopped")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        stop()
    else:
        setup_environment()
        build_and_run() 
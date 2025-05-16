import subprocess
import json
import logging
import os
import traceback
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Union

# Add Mem0 Python SDK imports
try:
    # Try both Memory class and MemoryClient imports
    from mem0 import Memory, MemoryClient
    HAS_MEM0_SDK = True
except ImportError:
    HAS_MEM0_SDK = False

logger = logging.getLogger(__name__)


class SwarmMessage(BaseModel):
    """Pydantic model for swarm message content."""
    content: str
    user_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Mem0Memory:
    """
    A Python wrapper for Mem0 to manage memory operations.
    This class handles adding and searching memories using the Mem0 Python SDK 
    or falling back to CLI if the SDK is not available.
    """

    def __init__(self, config_path="mem0.config.json"):
        """
        Initialize the Mem0Memory wrapper.

        Args:
            config_path (str): Path to the mem0 configuration file.
        """
        self.config_path = config_path
        self.memory = None
        self.client = None
        
        # Try to initialize the Mem0 Python SDK
        if HAS_MEM0_SDK:
            try:
                # First try to use Memory class with existing config
                try:
                    # Load configuration from file - this should be the existing Supabase config
                    with open(self.config_path, 'r') as f:
                        config = json.load(f)
                    
                    # Initialize Memory with existing configuration
                    self.memory = Memory.from_config(config)
                    logger.info(f"Initialized Mem0 Memory from config file: {self.config_path}")
                except Exception as e:
                    logger.warning(f"Could not initialize Mem0 Memory from config file: {str(e)}")
                    self.memory = None
                    
                # If Memory initialization failed and MEM0_API_KEY is available, try MemoryClient
                if self.memory is None and os.environ.get("MEM0_API_KEY"):
                    self.client = MemoryClient()
                    logger.info("Initialized Mem0 API client with environment API key")
            except Exception as e:
                logger.warning(f"Failed to initialize Mem0: {str(e)}")
                self.memory = None
                self.client = None

    def add_memory(self, message: SwarmMessage) -> Dict[str, Any]:
        """
        Add a new memory using Mem0 SDK or CLI.

        Args:
            message (SwarmMessage): The swarm message to add.

        Returns:
            dict: The response from Mem0.

        Raises:
            RuntimeError: If the Mem0 operation fails.
        """
        # Use Memory class if available (preferred for managed configuration)
        if HAS_MEM0_SDK and self.memory:
            try:
                # Format for Memory add method
                result = self.memory.add(
                    message.content, 
                    user_id=message.user_id,
                    metadata=message.metadata
                )
                return {"status": "success", "memory": result}
            except Exception as e:
                logger.error(f"Mem0 Memory add failed: {str(e)}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Mem0 Memory add failed: {str(e)}")
        
        # Use MemoryClient if available (API-based)
        elif HAS_MEM0_SDK and self.client:
            try:
                # Format for MemoryClient add method
                result = self.client.add(
                    message.content, 
                    user_id=message.user_id,
                    metadata=message.metadata
                )
                return {"status": "success", "message": result.get("message", "ok")}
            except Exception as e:
                logger.error(f"Mem0 API add failed: {str(e)}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Mem0 API add failed: {str(e)}")
        else:
            # Fall back to CLI
            cmd = [
                "npx", "mem0", "add",
                "--content", message.content,
                "--metadata", json.dumps(message.metadata),
                "--config", self.config_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"mem0 add failed: {result.stderr}")
                raise RuntimeError(f"mem0 add failed: {result.stderr}")
            return json.loads(result.stdout)

    def search_memory(self, query: str, top_k: int = 5, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Search memories using Mem0 SDK or CLI.

        Args:
            query (str): The search query.
            top_k (int, optional): Number of top results to return.
            user_id (str, optional): Filter results by user ID.

        Returns:
            dict: The search results from Mem0.

        Raises:
            RuntimeError: If the Mem0 operation fails.
        """
        # Use Memory class if available (preferred for managed configuration)
        if HAS_MEM0_SDK and self.memory:
            try:
                # Use search with user_id if provided
                if user_id:
                    results = self.memory.search(query, user_id=user_id)
                else:
                    results = self.memory.search(query)
                
                # Format results to match expected structure
                formatted_results = {
                    "results": []
                }
                
                for item in results:
                    formatted_results["results"].append({
                        "id": item.get("id", ""),
                        "content": item.get("memory", ""),
                        "metadata": item.get("metadata", {}),
                        "similarity": item.get("score", 0)
                    })
                
                return formatted_results
            except Exception as e:
                logger.error(f"Mem0 Memory search failed: {str(e)}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Mem0 Memory search failed: {str(e)}")
        
        # Use MemoryClient if available (API-based)
        elif HAS_MEM0_SDK and self.client:
            try:
                # Use search with user_id if provided
                if user_id:
                    results = self.client.search(query, user_id=user_id, limit=top_k)
                else:
                    results = self.client.search(query, limit=top_k)
                
                # Format results to match CLI output structure
                formatted_results = {
                    "results": []
                }
                
                # Handle different response formats from SDK
                if isinstance(results, list):
                    for item in results:
                        formatted_results["results"].append({
                            "id": item.get("id", ""),
                            "content": item.get("memory", ""),
                            "metadata": item.get("metadata", {}),
                            "similarity": item.get("score", 0)
                        })
                elif isinstance(results, dict) and "results" in results:
                    formatted_results = results
                
                return formatted_results
            except Exception as e:
                logger.error(f"Mem0 API search failed: {str(e)}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Mem0 API search failed: {str(e)}")
        else:
            # Fall back to CLI
            cmd = [
                "npx", "mem0", "search",
                "--query", query,
                "--top_k", str(top_k),
                "--config", self.config_path
            ]
            
            # Add user_id filter if provided
            if user_id:
                cmd.extend(["--user_id", user_id])
                
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"mem0 search failed: {result.stderr}")
                raise RuntimeError(f"mem0 search failed: {result.stderr}")
            return json.loads(result.stdout)

    def get_all_memories(self, user_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """
        Get all memories for a user using Mem0 SDK or CLI.

        Args:
            user_id (str, optional): The user ID to filter memories.
            limit (int, optional): Maximum number of memories to return.

        Returns:
            dict: All memories for the user.

        Raises:
            RuntimeError: If the Mem0 operation fails.
        """
        # Use Memory class if available (preferred for managed configuration)
        if HAS_MEM0_SDK and self.memory:
            try:
                # Get all memories for user if user_id is provided
                if user_id:
                    results = self.memory.get_all(user_id=user_id)
                else:
                    results = self.memory.get_all()
                
                return {"memories": results}
            except Exception as e:
                logger.error(f"Mem0 Memory get_all failed: {str(e)}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Mem0 Memory get_all failed: {str(e)}")
        
        # Use MemoryClient if available (API-based)
        elif HAS_MEM0_SDK and self.client:
            try:
                # Get all memories for user if user_id is provided
                if user_id:
                    results = self.client.get_all(user_id=user_id, page_size=limit)
                else:
                    results = self.client.get_all(page_size=limit)
                
                return {"memories": results}
            except Exception as e:
                logger.error(f"Mem0 API get_all failed: {str(e)}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Mem0 API get_all failed: {str(e)}")
        else:
            # Fall back to CLI
            cmd = [
                "npx", "mem0", "get-all",
                "--config", self.config_path,
                "--limit", str(limit)
            ]
            
            # Add user_id filter if provided
            if user_id:
                cmd.extend(["--user_id", user_id])
                
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"mem0 get-all failed: {result.stderr}")
                raise RuntimeError(f"mem0 get-all failed: {result.stderr}")
            return json.loads(result.stdout)

    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        Delete a specific memory using Mem0 SDK or CLI.

        Args:
            memory_id (str): The ID of the memory to delete.

        Returns:
            dict: Response from Mem0.

        Raises:
            RuntimeError: If the Mem0 operation fails.
        """
        # Use Memory class if available (preferred for managed configuration)
        if HAS_MEM0_SDK and self.memory:
            try:
                self.memory.delete(memory_id)
                return {"status": "success", "message": "Memory deleted"}
            except Exception as e:
                logger.error(f"Mem0 Memory delete failed: {str(e)}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Mem0 Memory delete failed: {str(e)}")
        
        # Use MemoryClient if available (API-based)
        elif HAS_MEM0_SDK and self.client:
            try:
                result = self.client.delete(memory_id)
                return {"status": "success", "message": result.get("message", "ok")}
            except Exception as e:
                logger.error(f"Mem0 API delete failed: {str(e)}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Mem0 API delete failed: {str(e)}")
        else:
            # Fall back to CLI
            cmd = [
                "npx", "mem0", "delete",
                "--id", memory_id,
                "--config", self.config_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"mem0 delete failed: {result.stderr}")
                raise RuntimeError(f"mem0 delete failed: {result.stderr}")
            return json.loads(result.stdout)
            
    def reset(self) -> Dict[str, Any]:
        """
        Reset all memory.
        
        Returns:
            dict: Response from Mem0.
            
        Raises:
            RuntimeError: If the Mem0 operation fails.
        """
        # Use Memory class if available (preferred for managed configuration)
        if HAS_MEM0_SDK and self.memory:
            try:
                self.memory.reset()
                return {"status": "success", "message": "Memory reset"}
            except Exception as e:
                logger.error(f"Mem0 Memory reset failed: {str(e)}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Mem0 Memory reset failed: {str(e)}")
                
        # Use MemoryClient if available (API-based)
        elif HAS_MEM0_SDK and self.client:
            try:
                result = self.client.reset()
                return {"status": "success", "message": result.get("message", "ok")}
            except Exception as e:
                logger.error(f"Mem0 API reset failed: {str(e)}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Mem0 API reset failed: {str(e)}")
        else:
            # Fall back to CLI
            cmd = [
                "npx", "mem0", "reset",
                "--config", self.config_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"mem0 reset failed: {result.stderr}")
                raise RuntimeError(f"mem0 reset failed: {result.stderr}")
            return json.loads(result.stdout) 
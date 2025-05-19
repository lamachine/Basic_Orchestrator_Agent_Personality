import logging

from common.managers.memory_manager import Mem0Memory, SwarmMessage

logger = logging.getLogger(__name__)

# Initialize Mem0Memory
mem0 = Mem0Memory()


async def add_swarm_message(content: str, user_id: str, metadata: dict = None):
    """
    Add a swarm message to mem0 memory.

    Args:
        content (str): The message content.
        user_id (str): The user ID.
        metadata (dict, optional): Additional metadata.

    Returns:
        dict: The response from mem0.
    """
    message = SwarmMessage(content=content, user_id=user_id, metadata=metadata or {})
    logger.info(f"Adding memory for user {user_id}: {content}")
    logger.debug(f"Memory metadata: {metadata}")
    return mem0.add_memory(message)


async def search_swarm_messages(query: str, user_id: str, top_k: int = 5):
    """
    Search swarm messages in mem0 memory.

    Args:
        query (str): The search query.
        user_id (str): The user ID for filtering.
        top_k (int, optional): Number of top results to return.

    Returns:
        dict: The search results from mem0.
    """
    logger.info(f"Searching memories for user {user_id} with query: {query}")
    results = mem0.search_memory(query, top_k=top_k)
    filtered_results = [
        r for r in results.get("results", []) if r.get("metadata", {}).get("user_id") == user_id
    ]
    logger.debug(f"Found {len(filtered_results)} results for user {user_id}")
    return {"results": filtered_results}

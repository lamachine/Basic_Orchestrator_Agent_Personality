import os

import pytest
from dotenv import load_dotenv
from mem0ai import Mem0

# Load environment variables
load_dotenv()


@pytest.fixture
def mem0_client():
    """Create a Mem0 client instance with local configuration."""
    return Mem0(config_file="mem0.config.json")  # Local config file


def test_local_memory_creation(mem0_client):
    """Test creating a memory in local mode."""
    # Create a test memory
    memory = mem0_client.create_memory(
        content="Test memory for local storage", metadata={"test": True}
    )
    assert memory is not None

    # Search for the memory
    results = mem0_client.search_memories("Test memory for local storage")
    assert len(results) > 0
    assert any(r.content == "Test memory for local storage" for r in results)


def test_local_memory_retrieval(mem0_client):
    """Test retrieving memories in local mode."""
    # Add a test memory
    memory = mem0_client.create_memory(
        content="This is a test memory about artificial intelligence",
        metadata={"test": True},
    )

    # Search for similar memories
    results = mem0_client.search_memories("Tell me about AI")
    assert len(results) > 0
    assert any("artificial intelligence" in r.content for r in results)

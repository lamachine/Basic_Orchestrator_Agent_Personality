import os
from dotenv import load_dotenv
from mem0ai import Mem0
import pytest

# Load environment variables
load_dotenv()

@pytest.fixture
def mem0_client():
    """Create a Mem0 client instance."""
    return Mem0()

def test_supabase_connection(mem0_client):
    """Test connection to Supabase vector store."""
    # Try to create a memory
    memory = mem0_client.create_memory(
        content="Test memory for connection verification",
        metadata={"test": True}
    )
    assert memory is not None
    assert memory.content == "Test memory for connection verification"
    
    # Try to retrieve the memory
    retrieved = mem0_client.get_memory(memory.id)
    assert retrieved is not None
    assert retrieved.id == memory.id
    
    # Clean up
    mem0_client.delete_memory(memory.id)

def test_neo4j_connection(mem0_client):
    """Test connection to Neo4j graph store."""
    # Create two memories
    memory1 = mem0_client.create_memory(
        content="First test memory",
        metadata={"test": True}
    )
    memory2 = mem0_client.create_memory(
        content="Second test memory",
        metadata={"test": True}
    )
    
    # Create a relationship
    relationship = mem0_client.create_relationship(
        source_id=memory1.id,
        target_id=memory2.id,
        relationship_type="TEST_RELATIONSHIP"
    )
    assert relationship is not None
    
    # Verify relationship
    relationships = mem0_client.get_relationships(memory1.id)
    assert len(relationships) > 0
    assert any(r.target_id == memory2.id for r in relationships)
    
    # Clean up
    mem0_client.delete_memory(memory1.id)
    mem0_client.delete_memory(memory2.id)

def test_vector_search(mem0_client):
    """Test vector search functionality."""
    # Create a test memory
    memory = mem0_client.create_memory(
        content="This is a test memory about artificial intelligence",
        metadata={"test": True}
    )
    
    # Search for similar memories
    results = mem0_client.search_memories("Tell me about AI")
    assert len(results) > 0
    assert any(r.id == memory.id for r in results)
    
    # Clean up
    mem0_client.delete_memory(memory.id) 
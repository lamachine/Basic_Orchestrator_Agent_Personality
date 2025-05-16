"""
Tests for embedding utilities.
"""

import pytest
import numpy as np
from src.common.utils.embedding_utils import EmbeddingManager

@pytest.fixture
def embedding_manager():
    """Create EmbeddingManager instance for testing."""
    return EmbeddingManager()

def test_init():
    """Test EmbeddingManager initialization."""
    manager = EmbeddingManager()
    assert manager.model is not None
    assert manager.device in ["cuda", "cpu"]

def test_get_embedding(embedding_manager):
    """Test get_embedding() returns correct shape."""
    text = "Test text"
    embedding = embedding_manager.get_embedding(text)
    assert isinstance(embedding, np.ndarray)
    assert embedding.ndim == 1
    assert embedding.shape[0] > 0

def test_get_embedding_empty(embedding_manager):
    """Test get_embedding() with empty text."""
    with pytest.raises(ValueError):
        embedding_manager.get_embedding("")

def test_get_embeddings(embedding_manager):
    """Test get_embeddings() returns correct shape."""
    texts = ["Text 1", "Text 2", "Text 3"]
    embeddings = embedding_manager.get_embeddings(texts)
    assert isinstance(embeddings, np.ndarray)
    assert embeddings.ndim == 2
    assert embeddings.shape[0] == len(texts)
    assert embeddings.shape[1] > 0

def test_get_embeddings_empty(embedding_manager):
    """Test get_embeddings() with empty list."""
    with pytest.raises(ValueError):
        embedding_manager.get_embeddings([])

def test_calculate_similarity(embedding_manager):
    """Test calculate_similarity() returns value between 0 and 1."""
    text1 = "Hello world"
    text2 = "Hello there"
    similarity = embedding_manager.calculate_similarity(text1, text2)
    assert isinstance(similarity, float)
    assert 0 <= similarity <= 1

def test_calculate_similarity_same(embedding_manager):
    """Test calculate_similarity() with identical texts."""
    text = "Hello world"
    similarity = embedding_manager.calculate_similarity(text, text)
    assert similarity == 1.0

def test_calculate_similarity_empty(embedding_manager):
    """Test calculate_similarity() with empty texts."""
    with pytest.raises(ValueError):
        embedding_manager.calculate_similarity("", "test")
    with pytest.raises(ValueError):
        embedding_manager.calculate_similarity("test", "")

def test_find_most_similar(embedding_manager):
    """Test find_most_similar() returns correct results."""
    query = "Hello world"
    candidates = ["Hello there", "Goodbye world", "Hello world"]
    results = embedding_manager.find_most_similar(query, candidates)
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(r, dict) for r in results)
    assert all("text" in r and "score" in r for r in results)
    assert all(0 <= r["score"] <= 1 for r in results)

def test_find_most_similar_threshold(embedding_manager):
    """Test find_most_similar() with threshold."""
    query = "Hello world"
    candidates = ["Hello there", "Goodbye world", "Hello world"]
    results = embedding_manager.find_most_similar(query, candidates, threshold=0.9)
    assert isinstance(results, list)
    assert all(r["score"] >= 0.9 for r in results)

def test_find_most_similar_empty(embedding_manager):
    """Test find_most_similar() with empty inputs."""
    with pytest.raises(ValueError):
        embedding_manager.find_most_similar("", ["test"])
    with pytest.raises(ValueError):
        embedding_manager.find_most_similar("test", [])

def test_batch_similarity(embedding_manager):
    """Test batch_similarity() returns correct structure."""
    queries = ["Hello", "World"]
    candidates = ["Hello there", "Goodbye world"]
    results = embedding_manager.batch_similarity(queries, candidates)
    assert isinstance(results, dict)
    assert all(q in results for q in queries)
    assert all(isinstance(r, list) for r in results.values())
    assert all(all(isinstance(item, dict) for item in r) for r in results.values())

def test_batch_similarity_empty(embedding_manager):
    """Test batch_similarity() with empty inputs."""
    with pytest.raises(ValueError):
        embedding_manager.batch_similarity([], ["test"])
    with pytest.raises(ValueError):
        embedding_manager.batch_similarity(["test"], []) 
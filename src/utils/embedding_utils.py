"""
Embedding utilities for vector operations and embeddings generation.

This module provides functions for:
1. Generating embeddings from text using various models
2. Vector operations like similarity and search
3. Caching embeddings to improve performance
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Union
import json
import hashlib
import os
import time
from datetime import datetime

# Setup logging
logger = logging.getLogger(__name__)

# Placeholder for actual embedding generation
# In a real implementation, this would use a library like OpenAI, HuggingFace, etc.
def generate_mock_embedding(text: str, model: str = "mock-embedding-model") -> List[float]:
    """
    Generate a mock embedding vector for demonstration purposes.
    In production, replace with actual embedding model call.
    
    Args:
        text: Input text to embed
        model: Name of the embedding model to use
        
    Returns:
        List of floats representing the embedding vector
    """
    # Create a deterministic but unique embedding based on text hash
    text_hash = hashlib.md5(text.encode()).digest()
    
    # Convert hash to a list of floats, normalized between -1 and 1
    vector_size = 1536  # Similar to OpenAI ada-002 embedding size
    embedding = []
    
    for i in range(vector_size):
        # Use different bytes from hash, cycling if needed
        hash_index = i % len(text_hash)
        # Convert byte to float between -1 and 1
        value = (text_hash[hash_index] / 128.0) - 1.0
        embedding.append(value)
        
    # Normalize to unit length (L2 norm)
    norm = np.linalg.norm(embedding)
    normalized = [x / norm for x in embedding]
    
    return normalized

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Cosine similarity score between -1 and 1
    """
    if len(vec1) != len(vec2):
        raise ValueError(f"Vector dimensions don't match: {len(vec1)} vs {len(vec2)}")
        
    # Convert to numpy arrays for efficient computation
    a = np.array(vec1)
    b = np.array(vec2)
    
    # Calculate cosine similarity
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    # Handle zero vectors
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    similarity = dot_product / (norm_a * norm_b)
    
    # Ensure result is within bounds
    return max(min(similarity, 1.0), -1.0)

class EmbeddingCache:
    """Simple cache for embeddings to avoid recomputing them."""
    
    def __init__(self, cache_dir: str = ".embedding_cache"):
        """
        Initialize the embedding cache.
        
        Args:
            cache_dir: Directory to store cached embeddings
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.cache = {}
        
    def _get_cache_key(self, text: str, model: str) -> str:
        """Generate a cache key from text and model."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"{model}_{text_hash}"
    
    def _get_cache_path(self, key: str) -> str:
        """Get path to cached embedding file."""
        return os.path.join(self.cache_dir, f"{key}.json")
    
    def get(self, text: str, model: str) -> Optional[List[float]]:
        """
        Retrieve embedding from cache if available.
        
        Args:
            text: Input text
            model: Embedding model name
            
        Returns:
            Cached embedding vector or None if not found
        """
        key = self._get_cache_key(text, model)
        
        # Check memory cache first
        if key in self.cache:
            return self.cache[key]
            
        # Check file cache
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                    embedding = data.get('embedding')
                    self.cache[key] = embedding
                    return embedding
            except Exception as e:
                logger.warning(f"Failed to load cached embedding: {e}")
                
        return None
    
    def put(self, text: str, model: str, embedding: List[float]) -> None:
        """
        Store embedding in cache.
        
        Args:
            text: Input text
            model: Embedding model name
            embedding: Vector to cache
        """
        key = self._get_cache_key(text, model)
        
        # Update memory cache
        self.cache[key] = embedding
        
        # Update file cache
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, 'w') as f:
                data = {
                    'text_sample': text[:100] + ('...' if len(text) > 100 else ''),
                    'model': model,
                    'embedding': embedding,
                    'cached_at': datetime.utcnow().isoformat()
                }
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Failed to cache embedding: {e}")

# Global embedding cache instance
embedding_cache = EmbeddingCache()

def get_embedding(
    text: str, 
    model: str = "mock-embedding-model",
    use_cache: bool = True
) -> List[float]:
    """
    Get embedding for text, using cache if available.
    
    Args:
        text: Text to embed
        model: Embedding model to use
        use_cache: Whether to use embedding cache
        
    Returns:
        Embedding vector
    """
    if not text or text.isspace():
        raise ValueError("Cannot embed empty text")
        
    # Try to get from cache first
    if use_cache:
        cached = embedding_cache.get(text, model)
        if cached is not None:
            return cached
    
    # Generate new embedding
    # In production, replace this with a call to OpenAI API, HuggingFace, etc.
    start_time = time.time()
    
    # For demo purposes, we use a mock embedding
    embedding = generate_mock_embedding(text, model)
    
    elapsed = time.time() - start_time
    logger.debug(f"Generated embedding in {elapsed:.2f}s")
    
    # Store in cache
    if use_cache:
        embedding_cache.put(text, model, embedding)
        
    return embedding

def batch_get_embeddings(
    texts: List[str], 
    model: str = "mock-embedding-model",
    use_cache: bool = True
) -> List[List[float]]:
    """
    Get embeddings for multiple texts, using cache if available.
    
    Args:
        texts: List of texts to embed
        model: Embedding model to use
        use_cache: Whether to use embedding cache
        
    Returns:
        List of embedding vectors
    """
    embeddings = []
    
    for text in texts:
        embedding = get_embedding(text, model, use_cache)
        embeddings.append(embedding)
        
    return embeddings

def find_similar_vectors(
    query_vector: List[float],
    vector_list: List[List[float]],
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Find most similar vectors to query vector.
    
    Args:
        query_vector: The query embedding vector
        vector_list: List of vectors to search
        top_k: Number of top results to return
        
    Returns:
        List of dictionaries with index and similarity score
    """
    results = []
    
    for i, vector in enumerate(vector_list):
        similarity = cosine_similarity(query_vector, vector)
        results.append({
            "index": i,
            "similarity": similarity
        })
    
    # Sort by similarity score, highest first
    sorted_results = sorted(results, key=lambda x: x["similarity"], reverse=True)
    
    # Return top k results
    return sorted_results[:top_k] 
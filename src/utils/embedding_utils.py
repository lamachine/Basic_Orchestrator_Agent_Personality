"""
Embedding utilities for vector operations and embeddings generation.

Functions for generating embeddings, vector operations, and caching.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Union
import json
import hashlib
import os
import time
from datetime import datetime

logger = logging.getLogger(__name__)

def generate_mock_embedding(text: str, model: str = "mock-embedding-model") -> List[float]:
    """Generate a mock embedding vector for demonstration purposes."""
    text_hash = hashlib.md5(text.encode()).digest()
    vector_size = 1536
    embedding = [((text_hash[i % len(text_hash)] / 128.0) - 1.0) for i in range(vector_size)]
    norm = np.linalg.norm(embedding)
    return [x / norm for x in embedding]

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if len(vec1) != len(vec2):
        raise ValueError(f"Vector dimensions don't match: {len(vec1)} vs {len(vec2)}")
    a = np.array(vec1)
    b = np.array(vec2)
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    similarity = dot_product / (norm_a * norm_b)
    return max(min(similarity, 1.0), -1.0)

class EmbeddingCache:
    """Simple cache for embeddings to avoid recomputing them."""
    def __init__(self, cache_dir: str = ".embedding_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.cache = {}
    def _get_cache_key(self, text: str, model: str) -> str:
        return f"{model}_{hashlib.md5(text.encode()).hexdigest()}"
    def _get_cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.json")
    def get(self, text: str, model: str) -> Optional[List[float]]:
        key = self._get_cache_key(text, model)
        if key in self.cache:
            return self.cache[key]
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
        key = self._get_cache_key(text, model)
        self.cache[key] = embedding
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

embedding_cache = EmbeddingCache()

def get_embedding(
    text: str, 
    model: str = "mock-embedding-model",
    use_cache: bool = True
) -> List[float]:
    """Get embedding for text, using cache if available."""
    if not text or text.isspace():
        raise ValueError("Cannot embed empty text")
    if use_cache:
        cached = embedding_cache.get(text, model)
        if cached is not None:
            return cached
    embedding = generate_mock_embedding(text, model)
    if use_cache:
        embedding_cache.put(text, model, embedding)
    return embedding

def batch_get_embeddings(
    texts: List[str], 
    model: str = "mock-embedding-model",
    use_cache: bool = True
) -> List[List[float]]:
    """Get embeddings for multiple texts, using cache if available."""
    return [get_embedding(text, model, use_cache) for text in texts]

def find_similar_vectors(
    query_vector: List[float],
    vector_list: List[List[float]],
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """Find most similar vectors to query vector."""
    results = [
        {"index": i, "similarity": cosine_similarity(query_vector, vector)}
        for i, vector in enumerate(vector_list)
    ]
    sorted_results = sorted(results, key=lambda x: x["similarity"], reverse=True)
    return sorted_results[:top_k] 
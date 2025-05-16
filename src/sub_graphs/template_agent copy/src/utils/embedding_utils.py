"""
Template Agent Embedding Utilities.

This module provides embedding utilities for the template agent,
inheriting core functionality from the orchestrator's embedding utilities
but adding template-specific vector operations.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Union
import json
import hashlib
import os
import time
from datetime import datetime

from src.utils.embedding_utils import (
    generate_mock_embedding as base_generate_mock_embedding,
    cosine_similarity as base_cosine_similarity,
    EmbeddingCache as BaseEmbeddingCache,
    get_embedding as base_get_embedding,
    batch_get_embeddings as base_batch_get_embeddings,
    find_similar_vectors as base_find_similar_vectors
)

from ..services.logging_service import get_logger

logger = get_logger(__name__)

def generate_mock_embedding(text: str, model: str = "template-embedding-model") -> List[float]:
    """Generate a mock embedding vector with template context."""
    embedding = base_generate_mock_embedding(text, model)
    logger.debug(f"Generated template mock embedding for model {model}")
    return embedding

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors with template validation."""
    similarity = base_cosine_similarity(vec1, vec2)
    logger.debug(f"Calculated template cosine similarity: {similarity}")
    return similarity

class EmbeddingCache(BaseEmbeddingCache):
    """Template-specific cache for embeddings."""
    def __init__(self, cache_dir: str = ".template_embedding_cache"):
        super().__init__(cache_dir)
        logger.debug(f"Initialized template embedding cache in {cache_dir}")
    
    def get(self, text: str, model: str) -> Optional[List[float]]:
        """Get embedding from cache with template context."""
        embedding = super().get(text, model)
        if embedding:
            logger.debug(f"Retrieved template embedding from cache for model {model}")
        return embedding
    
    def put(self, text: str, model: str, embedding: List[float]) -> None:
        """Put embedding in cache with template context."""
        super().put(text, model, embedding)
        logger.debug(f"Cached template embedding for model {model}")

# Create template-specific cache instance
template_embedding_cache = EmbeddingCache()

def get_embedding(
    text: str, 
    model: str = "template-embedding-model",
    use_cache: bool = True
) -> List[float]:
    """Get embedding for text with template context."""
    embedding = base_get_embedding(text, model, use_cache)
    logger.debug(f"Generated template embedding for model {model}")
    return embedding

def batch_get_embeddings(
    texts: List[str], 
    model: str = "template-embedding-model",
    use_cache: bool = True
) -> List[List[float]]:
    """Get embeddings for multiple texts with template context."""
    embeddings = base_batch_get_embeddings(texts, model, use_cache)
    logger.debug(f"Generated {len(embeddings)} template embeddings for model {model}")
    return embeddings

def find_similar_vectors(
    query_vector: List[float],
    vector_list: List[List[float]],
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """Find most similar vectors with template context."""
    results = base_find_similar_vectors(query_vector, vector_list, top_k)
    logger.debug(f"Found {len(results)} similar template vectors")
    return results 
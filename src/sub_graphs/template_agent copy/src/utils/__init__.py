"""
Template Agent Utilities.

This module provides utility functions and classes for the template agent,
including datetime handling, text processing, and embedding operations.
"""

from .datetime_utils import (
    format_datetime,
    parse_datetime,
    now,
    timestamp,
    is_valid_iso_format,
    DateTimeEncoder
)

from .text_processing import (
    clean_text,
    estimate_token_count,
    chunk_text_by_tokens,
    generate_chunk_title,
    generate_chunk_metadata,
    get_timestamp,
    split_by_section
)

from .embedding_utils import (
    generate_mock_embedding,
    cosine_similarity,
    EmbeddingCache,
    template_embedding_cache,
    get_embedding,
    batch_get_embeddings,
    find_similar_vectors
)

__all__ = [
    # Datetime utilities
    'format_datetime',
    'parse_datetime',
    'now',
    'timestamp',
    'is_valid_iso_format',
    'DateTimeEncoder',
    
    # Text processing utilities
    'clean_text',
    'estimate_token_count',
    'chunk_text_by_tokens',
    'generate_chunk_title',
    'generate_chunk_metadata',
    'get_timestamp',
    'split_by_section',
    
    # Embedding utilities
    'generate_mock_embedding',
    'cosine_similarity',
    'EmbeddingCache',
    'template_embedding_cache',
    'get_embedding',
    'batch_get_embeddings',
    'find_similar_vectors'
] 
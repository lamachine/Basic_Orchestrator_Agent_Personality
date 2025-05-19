"""
Embedding utilities for template agent.

This module provides utility functions for text embeddings and similarity calculations.
"""

import logging
from typing import Any, Dict, List, Optional, Union

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manages text embeddings and similarity calculations."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding manager.

        Args:
            model_name: Name of the sentence transformer model

        Raises:
            RuntimeError: If model fails to load
            ValueError: If model name is invalid
        """
        try:
            self.model = SentenceTransformer(model_name)
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model.to(self.device)
            logger.info(f"Initialized embedding manager with model {model_name} on {self.device}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding manager: {e}")
            raise RuntimeError(f"Failed to initialize embedding manager: {e}")

    def get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding for text.

        Args:
            text: Text to embed

        Returns:
            np.ndarray: Text embedding

        Raises:
            ValueError: If text is empty
            RuntimeError: If embedding fails
        """
        if not text:
            raise ValueError("Text cannot be empty")

        try:
            with torch.no_grad():
                embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise RuntimeError(f"Failed to get embedding: {e}")

    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Get embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            np.ndarray: Array of text embeddings

        Raises:
            ValueError: If texts list is empty
            RuntimeError: If embedding fails
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        try:
            with torch.no_grad():
                embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings
        except Exception as e:
            logger.error(f"Error getting embeddings: {e}")
            raise RuntimeError(f"Failed to get embeddings: {e}")

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            float: Similarity score (0-1)

        Raises:
            ValueError: If either text is empty
            RuntimeError: If calculation fails
        """
        if not text1 or not text2:
            raise ValueError("Texts cannot be empty")

        try:
            emb1 = self.get_embedding(text1)
            emb2 = self.get_embedding(text2)
            similarity = float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
            return similarity
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            raise RuntimeError(f"Failed to calculate similarity: {e}")

    def find_most_similar(
        self, query: str, candidates: List[str], threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Find most similar texts to query.

        Args:
            query: Query text
            candidates: List of candidate texts
            threshold: Similarity threshold

        Returns:
            List[Dict[str, Any]]: List of similar texts with scores

        Raises:
            ValueError: If query or candidates are empty
            RuntimeError: If search fails
        """
        if not query:
            raise ValueError("Query cannot be empty")
        if not candidates:
            raise ValueError("Candidates list cannot be empty")

        try:
            query_emb = self.get_embedding(query)
            candidate_embs = self.get_embeddings(candidates)

            # Calculate similarities
            similarities = np.dot(candidate_embs, query_emb) / (
                np.linalg.norm(candidate_embs, axis=1) * np.linalg.norm(query_emb)
            )

            # Get results above threshold
            results = []
            for i, score in enumerate(similarities):
                if score >= threshold:
                    results.append({"text": candidates[i], "score": float(score)})

            # Sort by score
            results.sort(key=lambda x: x["score"], reverse=True)
            return results
        except Exception as e:
            logger.error(f"Error finding similar texts: {e}")
            raise RuntimeError(f"Failed to find similar texts: {e}")

    def batch_similarity(
        self, queries: List[str], candidates: List[str], threshold: float = 0.5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Calculate similarities for multiple queries.

        Args:
            queries: List of query texts
            candidates: List of candidate texts
            threshold: Similarity threshold

        Returns:
            Dict[str, List[Dict[str, Any]]]: Dictionary of query results

        Raises:
            ValueError: If queries or candidates are empty
            RuntimeError: If calculation fails
        """
        if not queries:
            raise ValueError("Queries list cannot be empty")
        if not candidates:
            raise ValueError("Candidates list cannot be empty")

        try:
            results = {}
            for query in queries:
                results[query] = self.find_most_similar(query, candidates, threshold)
            return results
        except Exception as e:
            logger.error(f"Error calculating batch similarities: {e}")
            raise RuntimeError(f"Failed to calculate batch similarities: {e}")

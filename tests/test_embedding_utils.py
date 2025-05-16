"""
Unit tests for embedding utilities module.

This module contains tests for the embedding utilities provided
by the template agent.
"""

import unittest
import pytest
from unittest.mock import patch, MagicMock, Mock
import numpy as np
import torch

# Mock the SentenceTransformer import
with patch('src.sub_graphs.template_agent.src.common.utils.embedding_utils.SentenceTransformer'):
    from src.sub_graphs.template_agent.src.common.utils.embedding_utils import EmbeddingManager

class TestEmbeddingManager(unittest.TestCase):
    """Test cases for the EmbeddingManager class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create mock for SentenceTransformer
        self.mock_model = MagicMock()
        
        # Patch the SentenceTransformer instantiation and torch.cuda.is_available
        patcher1 = patch('src.sub_graphs.template_agent.src.common.utils.embedding_utils.SentenceTransformer')
        self.addCleanup(patcher1.stop)
        self.mock_transformer_class = patcher1.start()
        self.mock_transformer_class.return_value = self.mock_model
        
        patcher2 = patch('src.sub_graphs.template_agent.src.common.utils.embedding_utils.torch.cuda.is_available')
        self.addCleanup(patcher2.stop)
        self.mock_cuda_available = patcher2.start()
        self.mock_cuda_available.return_value = False  # Default to CPU for tests
        
        # Create the embedding manager with the mocked dependencies
        self.manager = EmbeddingManager()
    
    # Normal operation tests
    def test_initialization(self):
        """Test that EmbeddingManager initializes correctly."""
        # Assert
        self.mock_transformer_class.assert_called_once_with("all-MiniLM-L6-v2")
        self.mock_model.to.assert_called_once_with("cpu")
        self.assertEqual(self.manager.device, "cpu")
    
    def test_initialization_with_custom_model(self):
        """Test initialization with custom model name."""
        # Act
        custom_manager = EmbeddingManager(model_name="custom-model")
        
        # Assert
        self.mock_transformer_class.assert_called_with("custom-model")
    
    def test_initialization_with_cuda(self):
        """Test initialization with CUDA available."""
        # Arrange
        self.mock_cuda_available.return_value = True
        
        # Act
        cuda_manager = EmbeddingManager()
        
        # Assert
        self.assertEqual(cuda_manager.device, "cuda")
        self.mock_model.to.assert_called_with("cuda")
    
    def test_get_embedding(self):
        """Test that get_embedding() returns expected embedding."""
        # Arrange
        text = "Test text"
        expected_embedding = np.array([0.1, 0.2, 0.3])
        self.mock_model.encode.return_value = expected_embedding
        
        # Act
        result = self.manager.get_embedding(text)
        
        # Assert
        self.mock_model.encode.assert_called_once_with(text, convert_to_numpy=True)
        np.testing.assert_array_equal(result, expected_embedding)
    
    def test_get_embeddings(self):
        """Test that get_embeddings() returns expected embeddings for multiple texts."""
        # Arrange
        texts = ["Text 1", "Text 2"]
        expected_embeddings = np.array([[0.1, 0.2], [0.3, 0.4]])
        self.mock_model.encode.return_value = expected_embeddings
        
        # Act
        result = self.manager.get_embeddings(texts)
        
        # Assert
        self.mock_model.encode.assert_called_once_with(texts, convert_to_numpy=True)
        np.testing.assert_array_equal(result, expected_embeddings)
    
    def test_calculate_similarity(self):
        """Test that calculate_similarity() computes similarity correctly."""
        # Arrange
        text1 = "Text 1"
        text2 = "Text 2"
        
        # Mock get_embedding to return specific vectors
        embedding1 = np.array([1.0, 0.0])
        embedding2 = np.array([0.0, 1.0])
        
        with patch.object(self.manager, 'get_embedding') as mock_get_embedding:
            mock_get_embedding.side_effect = [embedding1, embedding2]
            
            # Act
            result = self.manager.calculate_similarity(text1, text2)
            
            # Assert
            self.assertEqual(result, 0.0)  # Orthogonal vectors have similarity 0
            mock_get_embedding.assert_any_call(text1)
            mock_get_embedding.assert_any_call(text2)
    
    def test_find_most_similar(self):
        """Test that find_most_similar() finds similar texts."""
        # Arrange
        query = "Query text"
        candidates = ["Similar text", "Different text", "Another similar"]
        
        # Mock embeddings to create known similarities
        query_embedding = np.array([1.0, 0.0])
        candidate_embeddings = np.array([
            [0.9, 0.1],   # 0.9 similarity
            [0.1, 0.9],   # 0.1 similarity
            [0.8, 0.2]    # 0.8 similarity
        ])
        
        with patch.object(self.manager, 'get_embedding') as mock_get_embedding, \
             patch.object(self.manager, 'get_embeddings') as mock_get_embeddings:
            mock_get_embedding.return_value = query_embedding
            mock_get_embeddings.return_value = candidate_embeddings
            
            # Act
            result = self.manager.find_most_similar(query, candidates, threshold=0.5)
            
            # Assert
            mock_get_embedding.assert_called_once_with(query)
            mock_get_embeddings.assert_called_once_with(candidates)
            
            self.assertEqual(len(result), 2)  # Only 2 results above threshold
            self.assertEqual(result[0]['text'], "Similar text")
            self.assertAlmostEqual(result[0]['score'], 0.9)
            self.assertEqual(result[1]['text'], "Another similar")
            self.assertAlmostEqual(result[1]['score'], 0.8)
    
    def test_batch_similarity(self):
        """Test that batch_similarity() processes multiple queries."""
        # Arrange
        queries = ["Query 1", "Query 2"]
        candidates = ["Candidate 1", "Candidate 2"]
        
        # Mock find_most_similar to return specific results
        result1 = [{"text": "Candidate 1", "score": 0.9}]
        result2 = [{"text": "Candidate 2", "score": 0.8}]
        
        with patch.object(self.manager, 'find_most_similar') as mock_find_similar:
            mock_find_similar.side_effect = [result1, result2]
            
            # Act
            result = self.manager.batch_similarity(queries, candidates)
            
            # Assert
            self.assertEqual(mock_find_similar.call_count, 2)
            mock_find_similar.assert_any_call(queries[0], candidates, 0.5)
            mock_find_similar.assert_any_call(queries[1], candidates, 0.5)
            
            self.assertEqual(result[queries[0]], result1)
            self.assertEqual(result[queries[1]], result2)
    
    # Error condition tests
    def test_initialization_error(self):
        """Test that initialization handles errors."""
        # Arrange
        self.mock_transformer_class.side_effect = Exception("Failed to load model")
        
        # Act & Assert
        with self.assertRaises(RuntimeError):
            EmbeddingManager()
    
    def test_get_embedding_empty_text(self):
        """Test that get_embedding() raises ValueError for empty text."""
        # Act & Assert
        with self.assertRaises(ValueError):
            self.manager.get_embedding("")
    
    def test_get_embeddings_empty_list(self):
        """Test that get_embeddings() raises ValueError for empty list."""
        # Act & Assert
        with self.assertRaises(ValueError):
            self.manager.get_embeddings([])
    
    def test_get_embedding_encoding_error(self):
        """Test that get_embedding() handles encoding errors."""
        # Arrange
        self.mock_model.encode.side_effect = Exception("Encoding error")
        
        # Act & Assert
        with self.assertRaises(RuntimeError):
            self.manager.get_embedding("Test text")
    
    def test_calculate_similarity_empty_texts(self):
        """Test that calculate_similarity() raises for empty texts."""
        # Act & Assert
        with self.assertRaises(ValueError):
            self.manager.calculate_similarity("", "Valid text")
        
        with self.assertRaises(ValueError):
            self.manager.calculate_similarity("Valid text", "")
    
    def test_find_most_similar_empty_query(self):
        """Test that find_most_similar() raises for empty query."""
        # Act & Assert
        with self.assertRaises(ValueError):
            self.manager.find_most_similar("", ["Valid candidate"])
    
    def test_find_most_similar_empty_candidates(self):
        """Test that find_most_similar() raises for empty candidates."""
        # Act & Assert
        with self.assertRaises(ValueError):
            self.manager.find_most_similar("Valid query", [])
    
    def test_batch_similarity_empty_queries(self):
        """Test that batch_similarity() raises for empty queries."""
        # Act & Assert
        with self.assertRaises(ValueError):
            self.manager.batch_similarity([], ["Valid candidate"])
    
    def test_batch_similarity_empty_candidates(self):
        """Test that batch_similarity() raises for empty candidates."""
        # Act & Assert
        with self.assertRaises(ValueError):
            self.manager.batch_similarity(["Valid query"], [])
    
    # Edge case tests
    def test_calculate_similarity_identical_texts(self):
        """Test that calculate_similarity() returns 1.0 for identical texts."""
        # Arrange
        text = "Identical text"
        
        # Mock get_embedding to return the same vector
        embedding = np.array([1.0, 0.0])
        
        with patch.object(self.manager, 'get_embedding') as mock_get_embedding:
            mock_get_embedding.return_value = embedding
            
            # Act
            result = self.manager.calculate_similarity(text, text)
            
            # Assert
            self.assertEqual(result, 1.0)
    
    def test_find_most_similar_no_matches(self):
        """Test that find_most_similar() handles no matches above threshold."""
        # Arrange
        query = "Query text"
        candidates = ["Different text", "Another different"]
        
        # Mock embeddings to create low similarities
        query_embedding = np.array([1.0, 0.0])
        candidate_embeddings = np.array([
            [0.1, 0.9],   # 0.1 similarity
            [0.2, 0.8]    # 0.2 similarity
        ])
        
        with patch.object(self.manager, 'get_embedding') as mock_get_embedding, \
             patch.object(self.manager, 'get_embeddings') as mock_get_embeddings:
            mock_get_embedding.return_value = query_embedding
            mock_get_embeddings.return_value = candidate_embeddings
            
            # Act
            result = self.manager.find_most_similar(query, candidates, threshold=0.5)
            
            # Assert
            self.assertEqual(len(result), 0)  # No results above threshold
    
    def test_find_most_similar_high_threshold(self):
        """Test that find_most_similar() respects high threshold."""
        # Arrange
        query = "Query text"
        candidates = ["Similar text", "Different text"]
        
        # Mock embeddings to create known similarities
        query_embedding = np.array([1.0, 0.0])
        candidate_embeddings = np.array([
            [0.9, 0.1],   # 0.9 similarity
            [0.1, 0.9]    # 0.1 similarity
        ])
        
        with patch.object(self.manager, 'get_embedding') as mock_get_embedding, \
             patch.object(self.manager, 'get_embeddings') as mock_get_embeddings:
            mock_get_embedding.return_value = query_embedding
            mock_get_embeddings.return_value = candidate_embeddings
            
            # Act
            result = self.manager.find_most_similar(query, candidates, threshold=0.95)
            
            # Assert
            self.assertEqual(len(result), 0)  # No results above high threshold
    
    def test_find_most_similar_zero_threshold(self):
        """Test that find_most_similar() includes all with zero threshold."""
        # Arrange
        query = "Query text"
        candidates = ["Similar text", "Different text"]
        
        # Mock embeddings to create known similarities
        query_embedding = np.array([1.0, 0.0])
        candidate_embeddings = np.array([
            [0.9, 0.1],   # 0.9 similarity
            [0.1, 0.9]    # 0.1 similarity
        ])
        
        with patch.object(self.manager, 'get_embedding') as mock_get_embedding, \
             patch.object(self.manager, 'get_embeddings') as mock_get_embeddings:
            mock_get_embedding.return_value = query_embedding
            mock_get_embeddings.return_value = candidate_embeddings
            
            # Act
            result = self.manager.find_most_similar(query, candidates, threshold=0.0)
            
            # Assert
            self.assertEqual(len(result), 2)  # All results included
    
    def test_get_embedding_single_word(self):
        """Test that get_embedding() handles single word inputs."""
        # Arrange
        text = "Word"
        expected_embedding = np.array([0.1, 0.2, 0.3])
        self.mock_model.encode.return_value = expected_embedding
        
        # Act
        result = self.manager.get_embedding(text)
        
        # Assert
        self.mock_model.encode.assert_called_once_with(text, convert_to_numpy=True)
        np.testing.assert_array_equal(result, expected_embedding) 
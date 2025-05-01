"""
Unit tests for the LLMQueryAgent class.

This module contains tests for the core functionality of the LLMQueryAgent,
including conversation management, LLM queries, and tool handling.
"""

import unittest
from unittest.mock import patch, MagicMock, ANY
import json
import uuid
from datetime import datetime

from src.agents.llm_query_agent import LLMQueryAgent, LLMQueryError
from src.managers.db_manager import ConversationState, TaskStatus, MessageRole
from src.config import Configuration

class TestLLMQueryAgent(unittest.TestCase):
    """Test cases for the LLMQueryAgent class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Mock dependencies
        self.db_patcher = patch('src.agents.llm_query_agent.DatabaseManager')
        self.mock_db_manager = self.db_patcher.start()
        
        # Mock the database instance
        self.mock_db = MagicMock()
        self.mock_db_manager.return_value = self.mock_db
        
        # Mock tool initialization
        self.tool_patcher = patch('src.agents.llm_query_agent.initialize_tool_dependencies')
        self.mock_tool_init = self.tool_patcher.start()
        
        # Mock requests for API calls
        self.requests_patcher = patch('src.agents.llm_query_agent.requests')
        self.mock_requests = self.requests_patcher.start()
        
        # Create a test agent
        self.agent = LLMQueryAgent()
    
    def tearDown(self):
        """Tear down test fixtures after each test method."""
        self.db_patcher.stop()
        self.tool_patcher.stop()
        self.requests_patcher.stop()
    
    def test_start_conversation_success(self):
        """Test starting a new conversation successfully."""
        # Setup
        test_title = "Test Conversation"
        mock_conv_id = 123
        
        # Configure mock
        self.mock_db.create_conversation.return_value = mock_conv_id
        
        # Exercise
        result = self.agent.start_conversation(test_title)
        
        # Verify
        self.assertTrue(result)
        self.assertEqual(self.agent.conversation_state, ConversationState.IN_PROGRESS)
        self.mock_db.create_conversation.assert_called_once_with(
            self.agent.user_id, 
            test_title, 
            ConversationState.IN_PROGRESS
        )
    
    def test_start_conversation_failure(self):
        """Test starting a conversation with database failure."""
        # Setup
        test_title = "Test Conversation"
        
        # Configure mock to simulate failure
        self.mock_db.create_conversation.side_effect = Exception("Database error")
        
        # Exercise
        result = self.agent.start_conversation(test_title)
        
        # Verify
        self.assertFalse(result)
        self.assertIsNone(self.agent.conversation_state)
    
    def test_continue_conversation_edge_case_nonexistent(self):
        """Test continuing a conversation that doesn't exist."""
        # Setup
        nonexistent_id = 9999
        
        # Configure mock
        self.mock_db.get_conversation.return_value = None
        
        # Exercise
        result = self.agent.continue_conversation(nonexistent_id)
        
        # Verify
        self.assertFalse(result)
        self.assertIsNone(self.agent.conversation_state)
        self.mock_db.get_conversation.assert_called_once_with(nonexistent_id)
    
    @patch('src.agents.llm_query_agent.requests.post')
    def test_query_llm_success(self, mock_post):
        """Test querying the LLM with a successful response."""
        # Setup
        test_prompt = "Hello, AI!"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Hello, human!",
            "model": "test-model",
            "done": True
        }
        mock_post.return_value = mock_response
        
        # Exercise
        response = self.agent.query_llm(test_prompt)
        
        # Verify
        self.assertEqual(response, "Hello, human!")
        mock_post.assert_called_once_with(
            f"{self.agent.api_url}/generate",
            json={
                "model": self.agent.model,
                "prompt": test_prompt,
                "stream": False
            }
        )
    
    @patch('src.agents.llm_query_agent.requests.post')
    def test_query_llm_failure(self, mock_post):
        """Test querying the LLM with a failed response."""
        # Setup
        test_prompt = "Hello, AI!"
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        # Exercise & Verify
        with self.assertRaises(LLMQueryError):
            self.agent.query_llm(test_prompt)
        
        mock_post.assert_called_once_with(
            f"{self.agent.api_url}/generate",
            json={
                "model": self.agent.model,
                "prompt": test_prompt,
                "stream": False
            }
        )
    
    @patch('src.agents.llm_query_agent.requests.post')
    def test_query_llm_edge_case_empty_response(self, mock_post):
        """Test querying the LLM with an empty response."""
        # Setup
        test_prompt = "Hello, AI!"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "", "done": True}
        mock_post.return_value = mock_response
        
        # Exercise
        result = self.agent.query_llm(test_prompt)
        
        # Verify
        self.assertEqual(result, "")
        mock_post.assert_called_once_with(
            f"{self.agent.api_url}/generate",
            json={
                "model": self.agent.model,
                "prompt": test_prompt,
                "stream": False
            }
        )
    
    def test_process_llm_response_with_tool_calls(self):
        """Test processing an LLM response that contains tool calls."""
        # Setup - a response with a tool call
        response_text = """
        I'll help you with that. Let me use a tool to find the information.
        
        ```tool
        {
            "name": "search",
            "args": {
                "query": "current weather in New York"
            }
        }
        ```
        
        Let me check that for you.
        """
        user_input = "What's the weather in New York?"
        
        # Mock handle_tool_calls to return a result
        with patch('src.agents.llm_query_agent.handle_tool_calls') as mock_handle_tools:
            mock_handle_tools.return_value = [
                {
                    "request_id": "test-id-123", 
                    "name": "search", 
                    "status": "pending"
                }
            ]
            
            # Exercise
            result = self.agent.process_llm_response(response_text, user_input)
            
            # Verify
            self.assertIn("response", result)
            self.assertIn("pending_tool_requests", result)
            self.assertEqual(len(result["pending_tool_requests"]), 1)
            self.assertEqual(result["pending_tool_requests"][0]["name"], "search")
            mock_handle_tools.assert_called_once()
    
    def test_process_llm_response_no_tool_calls(self):
        """Test processing an LLM response with no tool calls."""
        # Setup - a simple response with no tool calls
        response_text = "The weather in New York is currently sunny with a temperature of 75°F."
        user_input = "What's the weather in New York?"
        
        # Exercise
        result = self.agent.process_llm_response(response_text, user_input)
        
        # Verify
        self.assertIn("response", result)
        self.assertEqual(result["response"], response_text)
        self.assertNotIn("pending_tool_requests", result)
    
    def test_process_llm_response_edge_case_malformed_tool(self):
        """Test processing an LLM response with a malformed tool call."""
        # Setup - a response with a malformed tool call
        response_text = """
        I'll help you with that. Let me use a tool to find the information.
        
        ```tool
        {
            "name": "search",
            "args": { THIS IS MALFORMED JSON
                "query": "current weather in New York"
            }
        }
        ```
        
        Let me check that for you.
        """
        user_input = "What's the weather in New York?"
        
        # Exercise
        result = self.agent.process_llm_response(response_text, user_input)
        
        # Verify - it should handle the error gracefully and not crash
        self.assertIn("response", result)
        self.assertEqual(result["response"], response_text)
        # There shouldn't be any pending tool requests since the JSON was malformed
        self.assertNotIn("pending_tool_requests", result)
    
    def test_rename_conversation_success(self):
        """Test successfully renaming a conversation."""
        # Setup
        self.agent.session_id = 123
        new_title = "New Test Title"
        
        # Configure mock
        self.mock_db.update_conversation_title.return_value = True
        
        # Exercise
        result = self.agent.rename_conversation(new_title)
        
        # Verify
        self.assertTrue(result)
        self.mock_db.update_conversation_title.assert_called_once_with(123, new_title)
    
    def test_rename_conversation_failure(self):
        """Test renaming a conversation that fails."""
        # Setup
        self.agent.session_id = 123
        new_title = "New Test Title"
        
        # Configure mock to simulate failure
        self.mock_db.update_conversation_title.return_value = False
        
        # Exercise
        result = self.agent.rename_conversation(new_title)
        
        # Verify
        self.assertFalse(result)
        self.mock_db.update_conversation_title.assert_called_once_with(123, new_title)
    
    def test_rename_conversation_edge_case_no_session(self):
        """Test renaming a conversation when no session is active."""
        # Setup
        self.agent.session_id = None
        new_title = "New Test Title"
        
        # Exercise
        result = self.agent.rename_conversation(new_title)
        
        # Verify
        self.assertFalse(result)
        # The DB shouldn't be called since there's no active session
        self.mock_db.update_conversation_title.assert_not_called()

if __name__ == '__main__':
    unittest.main() 
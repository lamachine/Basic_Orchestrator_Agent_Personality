"""
Unit tests for the tool processor module.

This module contains tests for the tool processing utilities that handle
tool requests and responses.
"""

import unittest
from unittest.mock import patch, MagicMock
import json

from src.tools.tool_processor import (
    process_completed_tool_request,
    format_tool_result_for_llm,
    normalize_tool_response,
    extract_tool_calls_from_text
)

class TestProcessCompletedToolRequest(unittest.TestCase):
    """Test cases for the process_completed_tool_request function."""
    
    def test_process_tool_request_direct_message(self):
        """Test processing a tool request with a direct message field."""
        # Setup - a tool response with a direct message field
        tool_request = {
            'request_id': 'test-123',
            'response': {
                'name': 'test_tool',
                'message': 'This is a direct message'
            }
        }
        
        # Exercise
        result = process_completed_tool_request(tool_request)
        
        # Verify
        self.assertEqual(result, 'This is a direct message')
        self.assertEqual(tool_request['tool_name'], 'test_tool')
    
    def test_process_tool_request_nested_message(self):
        """Test processing a tool request with a nested message field."""
        # Setup - a tool response with a nested message
        tool_request = {
            'request_id': 'test-123',
            'response': {
                'name': 'test_tool',
                'response': {
                    'message': 'This is a nested message'
                }
            }
        }
        
        # Exercise
        result = process_completed_tool_request(tool_request)
        
        # Verify
        self.assertEqual(result, 'This is a nested message')
        self.assertEqual(tool_request['tool_name'], 'test_tool')
    
    def test_process_tool_request_missing_message(self):
        """Test processing a tool request with no message field."""
        # Setup - a tool response with no message field
        tool_request = {
            'request_id': 'test-123',
            'response': {
                'name': 'test_tool',
                'status': 'completed'
            }
        }
        
        # Exercise
        result = process_completed_tool_request(tool_request)
        
        # Verify - should use the fallback message
        self.assertEqual(result, 'Request test-123 completed with status: completed')
        self.assertEqual(tool_request['tool_name'], 'test_tool')
    
    def test_process_tool_request_result_object(self):
        """Test processing a tool request with a result object containing a message."""
        # Setup - a tool response with a result object
        tool_request = {
            'request_id': 'test-123',
            'response': {
                'name': 'test_tool',
                'result': {
                    'message': 'This is a message in result'
                }
            }
        }
        
        # Exercise
        result = process_completed_tool_request(tool_request)
        
        # Verify
        self.assertEqual(result, 'This is a message in result')
        self.assertEqual(tool_request['tool_name'], 'test_tool')
    
    def test_process_tool_request_edge_case_empty_response(self):
        """Test processing a tool request with an empty response."""
        # Setup - a tool request with an empty response
        tool_request = {
            'request_id': 'test-123',
            'response': {}
        }
        
        # Exercise
        result = process_completed_tool_request(tool_request)
        
        # Verify - should use the fallback message with unknown status
        self.assertEqual(result, 'Request test-123 completed with status: unknown')
        self.assertEqual(tool_request['tool_name'], 'unknown')

class TestFormatToolResultForLLM(unittest.TestCase):
    """Test cases for the format_tool_result_for_llm function."""
    
    def test_format_tool_result_direct(self):
        """Test formatting a tool result with a direct message."""
        # Setup
        tool_result = {
            'request_id': 'test-123',
            'tool_name': 'search',
            'message': 'The search results are: ...'
        }
        
        # Exercise
        result = format_tool_result_for_llm(tool_result)
        
        # Verify - should format correctly for LLM
        self.assertTrue(result.startswith('TOOL RESULT:'))
        self.assertIn('Tool: search', result)
        self.assertIn('Request ID: test-123', result)
        self.assertIn('Result: The search results are: ...', result)
    
    def test_format_tool_result_processed(self):
        """Test formatting a tool result that needs processing."""
        # Setup
        tool_result = {
            'request_id': 'test-123',
            'response': {
                'name': 'search',
                'message': 'The search results are: ...'
            }
        }
        
        # Mock process_completed_tool_request
        with patch('src.tools.tool_processor.process_completed_tool_request') as mock_process:
            mock_process.return_value = 'Processed message'
            
            # Exercise
            result = format_tool_result_for_llm(tool_result)
            
            # Verify
            self.assertTrue(result.startswith('TOOL RESULT:'))
            self.assertIn('Tool: unknown_tool', result)  # Should use the default since tool_name isn't set
            self.assertIn('Request ID: test-123', result)
            self.assertIn('Result: Processed message', result)
            mock_process.assert_called_once_with(tool_result)
    
    def test_format_tool_result_edge_case_minimal(self):
        """Test formatting a minimal tool result with only request_id."""
        # Setup
        tool_result = {
            'request_id': 'test-123'
        }
        
        # Mock process_completed_tool_request
        with patch('src.tools.tool_processor.process_completed_tool_request') as mock_process:
            mock_process.return_value = 'Minimal result'
            
            # Exercise
            result = format_tool_result_for_llm(tool_result)
            
            # Verify
            self.assertTrue(result.startswith('TOOL RESULT:'))
            self.assertIn('Tool: unknown_tool', result)  # Should use the default
            self.assertIn('Request ID: test-123', result)
            self.assertIn('Result: Minimal result', result)
            mock_process.assert_called_once_with(tool_result)

class TestNormalizeToolResponse(unittest.TestCase):
    """Test cases for the normalize_tool_response function."""
    
    def test_normalize_string_response(self):
        """Test normalizing a string response."""
        # Setup
        response = "This is a simple string response"
        
        # Exercise
        result = normalize_tool_response(response)
        
        # Verify
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["message"], response)
        self.assertIsNone(result["data"])
    
    def test_normalize_dict_response(self):
        """Test normalizing a dictionary response."""
        # Setup
        response = {
            "status": "in_progress",
            "message": "Still working on it",
            "data": {"progress": 50}
        }
        
        # Exercise
        result = normalize_tool_response(response)
        
        # Verify
        self.assertEqual(result["status"], "in_progress")
        self.assertEqual(result["message"], "Still working on it")
        self.assertEqual(result["data"], {"progress": 50})
    
    def test_normalize_dict_without_message(self):
        """Test normalizing a dictionary with no message but with result."""
        # Setup
        response = {
            "status": "completed",
            "result": "This is the result"
        }
        
        # Exercise
        result = normalize_tool_response(response)
        
        # Verify
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["message"], "This is the result")
        self.assertIsNone(result["data"])
    
    def test_normalize_dict_with_result_object(self):
        """Test normalizing a dictionary with a result object containing a message."""
        # Setup
        response = {
            "status": "completed",
            "result": {"message": "This is the message in result"}
        }
        
        # Exercise
        result = normalize_tool_response(response)
        
        # Verify
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["message"], "This is the message in result")
        self.assertIsNone(result["data"])
    
    def test_normalize_edge_case_non_string_non_dict(self):
        """Test normalizing a response that is neither a string nor a dictionary."""
        # Setup
        response = 123  # An integer
        
        # Exercise
        result = normalize_tool_response(response)
        
        # Verify - should convert to string
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["message"], "123")
        self.assertIsNone(result["data"])

class TestExtractToolCallsFromText(unittest.TestCase):
    """Test cases for the extract_tool_calls_from_text function."""
    
    def test_extract_single_tool_call(self):
        """Test extracting a single tool call from text."""
        # Setup
        text = "I'll search for that information using `search(task=\"find information about climate change\")`."
        
        # Exercise
        result = extract_tool_calls_from_text(text)
        
        # Verify
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "search")
        self.assertEqual(result[0]["task"], "find information about climate change")
    
    def test_extract_multiple_tool_calls(self):
        """Test extracting multiple tool calls from text."""
        # Setup
        text = """
        First, I'll search for basic information: `search(task="find information about climate change")`.
        Then, I'll check the latest news: `news(task="get recent news about climate change")`.
        Finally, I'll summarize the findings: `summarize(task="compile information about climate change")`.
        """
        
        # Exercise
        result = extract_tool_calls_from_text(text)
        
        # Verify
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["name"], "search")
        self.assertEqual(result[0]["task"], "find information about climate change")
        self.assertEqual(result[1]["name"], "news")
        self.assertEqual(result[1]["task"], "get recent news about climate change")
        self.assertEqual(result[2]["name"], "summarize")
        self.assertEqual(result[2]["task"], "compile information about climate change")
    
    def test_extract_no_tool_calls(self):
        """Test extracting tool calls from text with no tool calls."""
        # Setup
        text = "I don't need to use any tools for this request. Here's your answer."
        
        # Exercise
        result = extract_tool_calls_from_text(text)
        
        # Verify
        self.assertEqual(result, [])
    
    def test_extract_edge_case_malformed_tool_calls(self):
        """Test extracting malformed tool calls."""
        # Setup - tool call without closing parenthesis
        text = "I'll use this tool: `search(task=\"find information about climate change\"`."
        
        # Exercise
        result = extract_tool_calls_from_text(text)
        
        # Verify - shouldn't match the malformed tool call
        self.assertEqual(result, [])

if __name__ == '__main__':
    unittest.main() 
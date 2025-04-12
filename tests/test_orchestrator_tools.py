"""Tests for the orchestrator tools integration."""

import pytest
from unittest.mock import patch, MagicMock

from src.agents.orchestrator_tools import (
    add_tools_to_prompt,
    handle_tool_calls,
    format_tool_results
)


def test_add_tools_to_prompt():
    """Test adding tool descriptions to a prompt."""
    # Expected use case: Adding tools to a simple prompt
    base_prompt = "You are a helpful assistant."
    result = add_tools_to_prompt(base_prompt)
    
    # Verify the result contains both the original prompt and tool descriptions
    assert base_prompt in result
    assert "AVAILABLE TOOLS" in result
    assert "valet" in result
    assert "personal_assistant" in result
    assert "librarian" in result


@patch('src.tools.llm_integration.ToolParser.extract_tool_calls')
@patch('src.tools.llm_integration.ToolParser.execute_tool_calls')
def test_handle_tool_calls(mock_execute, mock_extract):
    """Test handling tool calls from LLM responses."""
    # Set up mocks
    mock_extract.return_value = [
        {"name": "valet", "parameters": {"task": "check schedule"}}
    ]
    mock_execute.return_value = [
        {
            "name": "valet", 
            "parameters": {"task": "check schedule"},
            "result": {
                "status": "success",
                "message": "All staff tasks are complete.",
                "data": {}
            }
        }
    ]
    
    # Expected use case: Processing a response with a tool call
    response = "I'll use the valet tool to check your schedule.\nvalet(task='check schedule')"
    result = handle_tool_calls(response)
    
    # Verify the result contains the extracted and executed tool calls
    assert "original_response" in result
    assert "tool_calls" in result
    assert "execution_results" in result
    assert result["tool_calls"] == mock_extract.return_value
    assert result["execution_results"] == mock_execute.return_value
    
    # Verify the mocks were called correctly
    mock_extract.assert_called_once_with(response)
    mock_execute.assert_called_once()


def test_format_tool_results_empty():
    """Test formatting empty tool results (edge case)."""
    # Edge case: No tool results
    results = {"execution_results": []}
    formatted = format_tool_results(results)
    
    # Verify the result is empty for no results
    assert formatted == ""


@patch('src.tools.llm_integration.ToolParser.format_results_for_llm')
def test_format_tool_results(mock_format):
    """Test formatting tool execution results."""
    # Set up mock
    mock_format.return_value = "## TOOL EXECUTION RESULTS\nSuccess!"
    
    # Expected use case: Formatting tool results
    results = {
        "execution_results": [
            {"name": "valet", "result": {"message": "Success!"}}
        ]
    }
    formatted = format_tool_results(results)
    
    # Verify the mock was called correctly
    mock_format.assert_called_once_with(results["execution_results"])
    assert formatted == "## TOOL EXECUTION RESULTS\nSuccess!"


def test_handle_tool_calls_failure():
    """Test handling tool calls with a failure case."""
    # Failure case: No tool calls in the response
    response = "I don't know how to help with that."
    result = handle_tool_calls(response)
    
    # Verify the result has empty tool calls and execution results
    assert result["original_response"] == response
    assert result["tool_calls"] == []
    assert result["execution_results"] == [] 
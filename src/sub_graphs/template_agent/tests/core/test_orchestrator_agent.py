"""Tests for Orchestrator agent functionality."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from pydantic import ValidationError

from ...src.common.agents.orchestrator_agent import OrchestratorAgent
from ...src.common.agents.base_agent import BaseAgentConfig
from ...src.common.state.state_models import MessageRole

@pytest.fixture
def orchestrator_config():
    """Create a base configuration for Orchestrator agent tests."""
    return BaseAgentConfig(
        name="test_orchestrator",
        prompt_section="Test orchestrator prompt",
        api_url="http://test-llm-api",
        model="test-model",
        max_tokens=1000,
        context_window=4000,
        enable_history=True,
        enable_logging=True,
        graph_name="test_graph"
    )

@pytest.fixture
def orchestrator_agent(orchestrator_config):
    """Create an Orchestrator agent for testing."""
    agent = OrchestratorAgent(orchestrator_config)
    # Mock the LLM service
    agent.llm = Mock()
    agent.llm.generate = AsyncMock()
    
    # Setup mock tool registry
    agent.tool_registry = Mock()
    agent.tool_registry.get_tools = AsyncMock()
    
    # Setup conversation state for logging
    agent.graph_state = {
        "conversation_state": {
            "add_message": AsyncMock()
        }
    }
    
    return agent

@pytest.fixture
def mock_tools():
    """Create mock tools for testing."""
    tool1 = AsyncMock()
    tool1.execute = AsyncMock(return_value={"status": "success", "result": "Tool 1 executed"})
    
    tool2 = AsyncMock()
    tool2.execute = AsyncMock(return_value={"status": "success", "result": "Tool 2 executed"})
    
    return {
        "tool1": tool1,
        "tool2": tool2
    }

def test_orchestrator_agent_config_validation():
    """Test BaseAgentConfig Pydantic validation for Orchestrator agent."""
    # Test valid configuration
    valid_config = BaseAgentConfig(
        name="test_orchestrator",
        prompt_section="Test prompt"
    )
    assert valid_config.name == "test_orchestrator"
    
    # Test required fields
    with pytest.raises(ValidationError):
        BaseAgentConfig(prompt_section="Missing name field")
    
    # Test type validation
    with pytest.raises(ValidationError):
        BaseAgentConfig(
            name="test", 
            enable_history="not_a_boolean"  # Should be a boolean
        )
    
    # Test nested validation
    with pytest.raises(ValidationError):
        # api_url should be a valid URL format
        BaseAgentConfig(
            name="test",
            api_url="invalid-url-format"
        )

def test_orchestrator_agent_initialization_validation():
    """Test OrchestratorAgent initialization with Pydantic validation."""
    # Test initialization with non-BaseAgentConfig object
    with pytest.raises(ValidationError):
        OrchestratorAgent({"name": "invalid_type"})
    
    # Test initialization with invalid config
    invalid_config = {"name": "test", "context_window": "invalid"}
    with pytest.raises(ValidationError):
        OrchestratorAgent(BaseAgentConfig(**invalid_config))

@pytest.mark.asyncio
async def test_request_parameter_validation(orchestrator_agent, mock_tools):
    """Test validation of route_request parameters."""
    # Setup
    orchestrator_agent.tool_registry.get_tools.return_value = mock_tools
    
    # Test with non-dict request
    with pytest.raises(TypeError):
        await orchestrator_agent.route_request("not a dict")
    
    # Test with invalid tool_name type
    with pytest.raises(TypeError):
        await orchestrator_agent.route_request({}, 123)  # tool_name should be a string or None
    
    # Test with empty request dict (should still work)
    response = await orchestrator_agent.route_request({})
    assert response["status"] == "success"
    
    # Test with None request (should raise TypeError)
    with pytest.raises(TypeError):
        await orchestrator_agent.route_request(None)

@pytest.mark.asyncio
async def test_route_request_return_value_validation(orchestrator_agent, mock_tools):
    """Test validation of route_request return values."""
    # Setup
    orchestrator_agent.tool_registry.get_tools.return_value = mock_tools
    
    # Test successful response structure
    response = await orchestrator_agent.route_request({"param": "value"}, "tool1")
    
    # Validate response structure
    assert isinstance(response, dict)
    assert "status" in response
    assert response["status"] in ["success", "error"]
    
    # For success responses, validate result field
    if response["status"] == "success":
        assert "result" in response
        assert isinstance(response["result"], str)
    
    # For error responses, validate message field
    error_response = await orchestrator_agent.route_request({}, "non_existent_tool")
    assert error_response["status"] == "error"
    assert "message" in error_response
    assert isinstance(error_response["message"], str)

@pytest.mark.asyncio
async def test_get_available_tools_return_validation(orchestrator_agent, mock_tools):
    """Test validation of get_available_tools return value."""
    # Setup
    orchestrator_agent.tool_registry.get_tools.return_value = mock_tools
    
    # Execute
    tool_list = await orchestrator_agent.get_available_tools()
    
    # Validate return type
    assert isinstance(tool_list, list)
    
    # Validate all elements are strings
    for tool_name in tool_list:
        assert isinstance(tool_name, str)
    
    # Validate empty list case
    orchestrator_agent.tool_registry.get_tools.return_value = {}
    empty_tool_list = await orchestrator_agent.get_available_tools()
    assert isinstance(empty_tool_list, list)
    assert len(empty_tool_list) == 0

@pytest.mark.asyncio
async def test_preprocessing_validation(orchestrator_agent, mock_tools):
    """Test validation of preprocessing method inputs and outputs."""
    # Setup
    orchestrator_agent.tool_registry.get_tools.return_value = mock_tools
    
    # Replace preprocess_request with one that returns non-dict (invalid)
    original_preprocess = orchestrator_agent.preprocess_request
    
    # Test preprocessing that returns invalid type
    async def invalid_preprocess(request):
        return "not a dict"  # Should be dict
    
    orchestrator_agent.preprocess_request = invalid_preprocess
    
    # Execute
    with pytest.raises(TypeError):
        await orchestrator_agent.route_request({"param": "value"}, "tool1")
    
    # Test preprocessing that modifies request correctly
    async def valid_preprocess(request):
        request["processed"] = True
        return request
    
    orchestrator_agent.preprocess_request = valid_preprocess
    
    # Execute
    await orchestrator_agent.route_request({"param": "value"}, "tool1")
    
    # Verify the tool was called with processed request
    mock_tools["tool1"].execute.assert_called_with(param="value", processed=True)
    
    # Restore original preprocessing
    orchestrator_agent.preprocess_request = original_preprocess

@pytest.mark.asyncio
async def test_postprocessing_validation(orchestrator_agent, mock_tools):
    """Test validation of postprocessing method inputs and outputs."""
    # Setup
    orchestrator_agent.tool_registry.get_tools.return_value = mock_tools
    
    # Replace postprocess_response with one that returns non-dict (invalid)
    original_postprocess = orchestrator_agent.postprocess_response
    
    # Test postprocessing that returns invalid type
    async def invalid_postprocess(response):
        return "not a dict"  # Should be dict
    
    orchestrator_agent.postprocess_response = invalid_postprocess
    
    # Execute
    with pytest.raises(TypeError):
        await orchestrator_agent.route_request({"param": "value"}, "tool1")
    
    # Test postprocessing that modifies response correctly
    async def valid_postprocess(response):
        response["postprocessed"] = True
        return response
    
    orchestrator_agent.postprocess_response = valid_postprocess
    
    # Execute
    response = await orchestrator_agent.route_request({"param": "value"}, "tool1")
    
    # Verify response was postprocessed
    assert response["postprocessed"] is True
    
    # Restore original postprocessing
    orchestrator_agent.postprocess_response = original_postprocess

@pytest.mark.asyncio
async def test_route_request_success(orchestrator_agent, mock_tools):
    """Test successful request routing to a specific tool."""
    # Test case: Normal operation - should pass
    
    # Setup
    request = {"param1": "value1", "param2": "value2"}
    tool_name = "tool1"
    orchestrator_agent.tool_registry.get_tools.return_value = mock_tools
    
    # Execute
    response = await orchestrator_agent.route_request(request, tool_name)
    
    # Verify
    assert response["status"] == "success"
    assert response["result"] == "Tool 1 executed"
    mock_tools[tool_name].execute.assert_called_once_with(**request)
    
    # Verify logging was called
    orchestrator_agent.graph_state["conversation_state"]["add_message"].assert_called_once()

@pytest.mark.asyncio
async def test_route_request_no_tool_specified(orchestrator_agent, mock_tools):
    """Test routing with default tool when none specified."""
    # Test case: Edge case - no tool specified, should use first available
    
    # Setup
    request = {"param1": "value1"}
    orchestrator_agent.tool_registry.get_tools.return_value = mock_tools
    
    # Execute
    response = await orchestrator_agent.route_request(request)  # No tool name
    
    # Verify
    assert response["status"] == "success"
    # Should have used the first tool in the list
    first_tool = list(mock_tools.values())[0]
    first_tool.execute.assert_called_once_with(**request)

@pytest.mark.asyncio
async def test_route_request_tool_not_found(orchestrator_agent, mock_tools):
    """Test routing with a non-existent tool."""
    # Test case: Error condition - should fail when tool not found
    
    # Setup
    request = {"param1": "value1"}
    tool_name = "non_existent_tool"
    orchestrator_agent.tool_registry.get_tools.return_value = mock_tools
    
    # Execute
    response = await orchestrator_agent.route_request(request, tool_name)
    
    # Verify
    assert response["status"] == "error"
    assert f"Tool {tool_name} not found" in response["message"]
    
    # Verify no tool was executed
    for tool in mock_tools.values():
        tool.execute.assert_not_called()

@pytest.mark.asyncio
async def test_route_request_no_tools_available(orchestrator_agent):
    """Test routing when no tools are available."""
    # Test case: Error condition - should fail when no tools are available
    
    # Setup
    request = {"param1": "value1"}
    orchestrator_agent.tool_registry.get_tools.return_value = {}  # Empty tools dict
    
    # Execute
    response = await orchestrator_agent.route_request(request)
    
    # Verify
    assert response["status"] == "error"
    assert "No tools available" in response["message"]

@pytest.mark.asyncio
async def test_route_request_with_error(orchestrator_agent, mock_tools):
    """Test routing with a tool that raises an exception."""
    # Test case: Error condition - should handle exceptions from tools
    
    # Setup
    request = {"param1": "value1"}
    tool_name = "tool1"
    error_message = "Tool execution error"
    mock_tools[tool_name].execute.side_effect = Exception(error_message)
    orchestrator_agent.tool_registry.get_tools.return_value = mock_tools
    
    # Execute
    response = await orchestrator_agent.route_request(request, tool_name)
    
    # Verify
    assert response["status"] == "error"
    assert error_message in response["message"]

@pytest.mark.asyncio
async def test_route_request_override(orchestrator_agent, mock_tools):
    """Test routing with override functionality."""
    # Test case: Edge case - custom override implementation
    
    # Setup
    request = {"param1": "value1"}
    tool_name = "tool1"
    override_response = {"status": "success", "result": "Override result"}
    
    # Create an override method
    orchestrator_agent.route_request_override = AsyncMock(return_value=override_response)
    
    # Execute
    response = await orchestrator_agent.route_request(request, tool_name)
    
    # Verify
    assert response == override_response
    orchestrator_agent.route_request_override.assert_called_once_with(request, tool_name)
    
    # Verify tool registry was not called since override handled it
    orchestrator_agent.tool_registry.get_tools.assert_not_called()

@pytest.mark.asyncio
async def test_request_preprocessing(orchestrator_agent, mock_tools):
    """Test request preprocessing functionality."""
    # Test case: Normal operation with preprocessing - should pass
    
    # Setup
    request = {"param1": "value1"}
    tool_name = "tool1"
    orchestrator_agent.tool_registry.get_tools.return_value = mock_tools
    
    # Create custom preprocessing that adds a parameter
    original_preprocess = orchestrator_agent.preprocess_request
    async def custom_preprocess(req):
        req["additional_param"] = "added_value"
        return req
    orchestrator_agent.preprocess_request = custom_preprocess
    
    # Execute
    await orchestrator_agent.route_request(request, tool_name)
    
    # Verify
    # Tool should be called with the preprocessed request including the additional parameter
    expected_request = {"param1": "value1", "additional_param": "added_value"}
    mock_tools[tool_name].execute.assert_called_once_with(**expected_request)
    
    # Restore original preprocessing
    orchestrator_agent.preprocess_request = original_preprocess

@pytest.mark.asyncio
async def test_response_postprocessing(orchestrator_agent, mock_tools):
    """Test response postprocessing functionality."""
    # Test case: Normal operation with postprocessing - should pass
    
    # Setup
    request = {"param1": "value1"}
    tool_name = "tool1"
    tool_response = {"status": "success", "result": "Original result"}
    mock_tools[tool_name].execute.return_value = tool_response
    orchestrator_agent.tool_registry.get_tools.return_value = mock_tools
    
    # Create custom postprocessing that modifies the response
    original_postprocess = orchestrator_agent.postprocess_response
    async def custom_postprocess(resp):
        resp["result"] = f"{resp['result']} [MODIFIED]"
        return resp
    orchestrator_agent.postprocess_response = custom_postprocess
    
    # Execute
    response = await orchestrator_agent.route_request(request, tool_name)
    
    # Verify
    assert response["status"] == "success"
    assert response["result"] == "Original result [MODIFIED]"
    
    # Restore original postprocessing
    orchestrator_agent.postprocess_response = original_postprocess

@pytest.mark.asyncio
async def test_get_available_tools(orchestrator_agent, mock_tools):
    """Test getting available tools list."""
    # Test case: Normal operation - should return list of tool names
    
    # Setup
    orchestrator_agent.tool_registry.get_tools.return_value = mock_tools
    
    # Execute
    tool_list = await orchestrator_agent.get_available_tools()
    
    # Verify
    assert isinstance(tool_list, list)
    assert "tool1" in tool_list
    assert "tool2" in tool_list
    assert len(tool_list) == 2

@pytest.mark.asyncio
async def test_get_available_tools_error(orchestrator_agent):
    """Test error handling when getting available tools."""
    # Test case: Error condition - should handle exceptions gracefully
    
    # Setup
    error_message = "Tool registry error"
    orchestrator_agent.tool_registry.get_tools.side_effect = Exception(error_message)
    
    # Execute
    tool_list = await orchestrator_agent.get_available_tools()
    
    # Verify
    assert isinstance(tool_list, list)
    assert len(tool_list) == 0  # Should return empty list on error 
"""
Tests for mcp_router.py

This module tests the MCP router functionality, including:
1. Request validation
2. Endpoint handling
3. Status checking
4. Error handling
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
import json

from ...src.common.routers.mcp_router import router, MCPRequest, get_mcp_service
from ...src.common.services.mcp_service import MCPService
from ...src.common.services.db_service import DBService


@pytest.fixture
def mock_mcp_service():
    """Create a mock MCP service."""
    mock_service = AsyncMock(spec=MCPService)
    
    # Mock call_mcp method
    mock_service.call_mcp = AsyncMock(return_value={
        "status": "pending",
        "task_id": "test-task-id",
        "message": "Task initiated"
    })
    
    # Mock check_status method
    mock_service.check_status = AsyncMock(return_value={
        "status": "completed",
        "task_id": "test-task-id",
        "result": {"data": "test result"}
    })
    
    return mock_service


@pytest.fixture
def test_app():
    """Create a test FastAPI app."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def test_client(test_app):
    """Create a test client."""
    return TestClient(test_app)


def test_mcp_request_model_validation():
    """Test MCPRequest model validation."""
    # Test case: Normal operation - should pass
    request = MCPRequest(
        endpoint_name="test_endpoint",
        capability="test_capability",
        parameters={"param1": "value1"}
    )
    
    assert request.endpoint_name == "test_endpoint"
    assert request.capability == "test_capability"
    assert request.parameters["param1"] == "value1"
    assert request.task_id is None
    
    # Test with task_id
    request = MCPRequest(
        endpoint_name="test_endpoint",
        capability="test_capability",
        parameters={"param1": "value1"},
        task_id="test-task-id"
    )
    
    assert request.task_id == "test-task-id"
    
    # Test with complex parameters
    complex_params = {
        "string_param": "value",
        "int_param": 123,
        "bool_param": True,
        "list_param": [1, 2, 3],
        "dict_param": {"key": "value"},
        "nested_param": {
            "nested_key": {
                "deeply_nested": "value"
            }
        }
    }
    
    request = MCPRequest(
        endpoint_name="test_endpoint",
        capability="test_capability",
        parameters=complex_params
    )
    
    assert request.parameters["string_param"] == "value"
    assert request.parameters["int_param"] == 123
    assert request.parameters["list_param"] == [1, 2, 3]
    assert request.parameters["nested_param"]["nested_key"]["deeply_nested"] == "value"


def test_mcp_request_model_validation_error():
    """Test MCPRequest model validation errors."""
    # Test case: Error condition - missing required fields
    with pytest.raises(ValueError):
        MCPRequest(capability="test_capability", parameters={})  # Missing endpoint_name
    
    with pytest.raises(ValueError):
        MCPRequest(endpoint_name="test_endpoint", parameters={})  # Missing capability
    
    with pytest.raises(ValueError):
        MCPRequest(endpoint_name="test_endpoint", capability="test_capability")  # Missing parameters


@pytest.mark.asyncio
async def test_get_mcp_service():
    """Test get_mcp_service dependency."""
    # Test case: Normal operation - should pass
    mock_db = AsyncMock(spec=DBService)
    
    with patch('src.common.routers.mcp_router.MCPService') as mock_mcp_class:
        mock_mcp = AsyncMock(spec=MCPService)
        mock_mcp_class.return_value = mock_mcp
        
        service = await get_mcp_service(mock_db)
        
        # Verify MCPService was created with db_service
        mock_mcp_class.assert_called_once_with(mock_db)
        assert service == mock_mcp


@pytest.mark.asyncio
async def test_mcp_endpoint(mock_mcp_service):
    """Test MCP endpoint."""
    # Test case: Normal operation - should pass
    request = MCPRequest(
        endpoint_name="test_endpoint",
        capability="test_capability",
        parameters={"param1": "value1"}
    )
    
    # Test endpoint
    response = await router.url_path_for("mcp_endpoint", capability="test_capability").app.dependency_overrides[get_mcp_service] = lambda: mock_mcp_service
    
    with patch('src.common.routers.mcp_router.get_mcp_service', return_value=mock_mcp_service):
        result = await router.routes[0].endpoint(
            "test_capability",
            request,
            mock_mcp_service
        )
    
    # Verify mcp_service.call_mcp was called correctly
    mock_mcp_service.call_mcp.assert_called_once_with(
        endpoint_name="test_endpoint",
        capability="test_capability",
        parameters={"param1": "value1"},
        task_id=None
    )
    
    # Verify response
    assert result["status"] == "pending"
    assert result["task_id"] == "test-task-id"
    assert result["message"] == "Task initiated"


@pytest.mark.asyncio
async def test_mcp_endpoint_error(mock_mcp_service):
    """Test MCP endpoint with error."""
    # Test case: Error condition - MCP service returns error
    request = MCPRequest(
        endpoint_name="test_endpoint",
        capability="test_capability",
        parameters={"param1": "value1"}
    )
    
    # Mock error response
    mock_mcp_service.call_mcp.return_value = {
        "status": "error",
        "error": "Test error message"
    }
    
    # Test endpoint
    with pytest.raises(HTTPException) as excinfo:
        with patch('src.common.routers.mcp_router.get_mcp_service', return_value=mock_mcp_service):
            await router.routes[0].endpoint(
                "test_capability",
                request,
                mock_mcp_service
            )
    
    # Verify exception
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Test error message"
    
    # Verify mcp_service.call_mcp was called
    mock_mcp_service.call_mcp.assert_called_once()


@pytest.mark.asyncio
async def test_check_status(mock_mcp_service):
    """Test check_status endpoint."""
    # Test case: Normal operation - should pass
    
    # Test endpoint
    with patch('src.common.routers.mcp_router.get_mcp_service', return_value=mock_mcp_service):
        result = await router.routes[1].endpoint(
            "test-task-id",
            mock_mcp_service
        )
    
    # Verify mcp_service.check_status was called correctly
    mock_mcp_service.check_status.assert_called_once_with("test-task-id")
    
    # Verify response
    assert result["status"] == "completed"
    assert result["task_id"] == "test-task-id"
    assert result["result"]["data"] == "test result"


@pytest.mark.asyncio
async def test_check_status_error(mock_mcp_service):
    """Test check_status endpoint with error."""
    # Test case: Error condition - MCP service returns error
    
    # Mock error response
    mock_mcp_service.check_status.return_value = {
        "status": "error",
        "error": "Task not found"
    }
    
    # Test endpoint
    with pytest.raises(HTTPException) as excinfo:
        with patch('src.common.routers.mcp_router.get_mcp_service', return_value=mock_mcp_service):
            await router.routes[1].endpoint(
                "nonexistent-task-id",
                mock_mcp_service
            )
    
    # Verify exception
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Task not found"
    
    # Verify mcp_service.check_status was called
    mock_mcp_service.check_status.assert_called_once_with("nonexistent-task-id")


def test_integration_with_fastapi_post(test_client, mock_mcp_service):
    """Test integration with FastAPI for POST request."""
    # Test case: Normal operation - should pass
    
    # Override dependency
    test_client.app.dependency_overrides[get_mcp_service] = lambda: mock_mcp_service
    
    # Make request
    response = test_client.post(
        "/mcp/test_capability",
        json={
            "endpoint_name": "test_endpoint",
            "capability": "test_capability",
            "parameters": {"param1": "value1"}
        }
    )
    
    # Verify response
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["task_id"] == "test-task-id"
    
    # Clear dependency override
    test_client.app.dependency_overrides = {}


def test_integration_with_fastapi_get(test_client, mock_mcp_service):
    """Test integration with FastAPI for GET request."""
    # Test case: Normal operation - should pass
    
    # Override dependency
    test_client.app.dependency_overrides[get_mcp_service] = lambda: mock_mcp_service
    
    # Make request
    response = test_client.get("/mcp/status/test-task-id")
    
    # Verify response
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["task_id"] == "test-task-id"
    
    # Clear dependency override
    test_client.app.dependency_overrides = {} 
"""
Unit tests for the MCP service.

Tests for the Multi-agent Communication Protocol service, including:
1. Initialization and configuration
2. Local endpoint handling
3. Remote endpoint handling
4. Request tracking and status checking
5. Error handling
"""

import pytest
import os
import json
import threading
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

from ...src.common.services.mcp_service import MCPService, PENDING_MCP_REQUESTS
from ...src.common.services.db_service import DBService


@pytest.fixture
def mock_db_service():
    """Create a mock database service."""
    mock_db = Mock(spec=DBService)
    mock_db.execute_query = Mock(return_value={"status": "success", "data": [{"result": "test"}]})
    return mock_db


@pytest.fixture
def test_config():
    """Create a test configuration."""
    return {
        "endpoints": {
            "test_local": {
                "url": "local",
                "capabilities": ["test_capability"]
            },
            "test_remote": {
                "url": "https://test.example.com",
                "capabilities": ["test_capability"],
                "auth": {"api_key": "test_key"},
                "headers": {"Accept": "application/json"}
            },
            "brave_search": {
                "url": "https://api.search.brave.com/search",
                "auth": {"api_key": "test_brave_key"},
                "capabilities": ["brave_web_search"],
                "headers": {
                    "Accept": "application/json",
                    "X-Subscription-Token": "test_brave_key"
                }
            }
        },
        "timeout": 10,
        "retry_attempts": 2
    }


@pytest.fixture
def mcp_service(mock_db_service, test_config):
    """Create a test MCP service with the test configuration."""
    with patch.object(MCPService, '_load_config', return_value=test_config):
        with patch.dict(os.environ, {"USE_AS_MCP_SERVER": "true"}):
            service = MCPService(mock_db_service)
            # Clear any pending requests from previous tests
            PENDING_MCP_REQUESTS.clear()
            return service


def test_initialization_enabled(mock_db_service, test_config):
    """Test service initialization when enabled."""
    with patch.dict(os.environ, {"USE_AS_MCP_SERVER": "true"}):
        with patch.object(MCPService, '_load_config', return_value=test_config):
            service = MCPService(mock_db_service)
            assert service.enabled is True
            assert service.config == test_config
            assert service.db_service == mock_db_service


def test_initialization_disabled(mock_db_service):
    """Test service initialization when disabled."""
    with patch.dict(os.environ, {"USE_AS_MCP_SERVER": "false"}):
        service = MCPService(mock_db_service)
        assert service.enabled is False


def test_load_config_with_defaults(mock_db_service):
    """Test loading configuration with defaults when no config file is provided."""
    with patch.dict(os.environ, {
        "USE_AS_MCP_SERVER": "true",
        "BRAVE_API_KEY": "test_key"
    }):
        service = MCPService(mock_db_service)
        assert "endpoints" in service.config
        assert "brave_search" in service.config["endpoints"]
        assert service.config["endpoints"]["brave_search"]["auth"]["api_key"] == "test_key"


def test_load_config_with_file(mock_db_service, tmp_path):
    """Test loading configuration from a file."""
    config_file = tmp_path / "test_config.json"
    test_config = {
        "endpoints": {
            "custom_endpoint": {
                "url": "https://custom.example.com",
                "capabilities": ["custom_capability"]
            }
        }
    }
    
    with open(config_file, 'w') as f:
        json.dump(test_config, f)
    
    with patch.dict(os.environ, {"USE_AS_MCP_SERVER": "true"}):
        service = MCPService(mock_db_service, str(config_file))
        assert "custom_endpoint" in service.config["endpoints"]
        assert "brave_search" in service.config["endpoints"]  # Default should still be present


@pytest.mark.asyncio
async def test_call_mcp_disabled():
    """Test calling MCP when the service is disabled."""
    with patch.dict(os.environ, {"USE_AS_MCP_SERVER": "false"}):
        service = MCPService(Mock())
        result = await service.call_mcp("test", "test", {})
        assert result["status"] == "error"
        assert "disabled" in result["error"]


@pytest.mark.asyncio
async def test_call_mcp_unknown_endpoint(mcp_service):
    """Test calling MCP with an unknown endpoint."""
    result = await mcp_service.call_mcp("unknown_endpoint", "test", {})
    assert result["status"] == "error"
    assert "Unknown MCP endpoint" in result["error"]


@pytest.mark.asyncio
async def test_call_mcp_invalid_capability(mcp_service):
    """Test calling MCP with an invalid capability."""
    result = await mcp_service.call_mcp("test_local", "invalid_capability", {})
    assert result["status"] == "error"
    assert "not supported by endpoint" in result["error"]


@pytest.mark.asyncio
async def test_call_mcp_local_endpoint(mcp_service):
    """Test calling MCP with a local endpoint."""
    # Mock the _process_local_mcp_request method to avoid threading issues in tests
    with patch.object(threading.Thread, 'start'):
        result = await mcp_service.call_mcp("test_local", "test_capability", {})
        assert result["status"] == "pending"
        assert "task_id" in result
        assert result["task_id"] in PENDING_MCP_REQUESTS


@pytest.mark.asyncio
async def test_call_mcp_remote_endpoint(mcp_service):
    """Test calling MCP with a remote endpoint."""
    # Mock the _process_remote_mcp_request method to avoid threading issues in tests
    with patch.object(threading.Thread, 'start'):
        result = await mcp_service.call_mcp("test_remote", "test_capability", {})
        assert result["status"] == "pending"
        assert "task_id" in result
        assert result["task_id"] in PENDING_MCP_REQUESTS


@pytest.mark.asyncio
async def test_process_local_mcp_request_postgres(mcp_service, mock_db_service):
    """Test processing a local MCP request for Postgres."""
    task_id = "test_postgres_task"
    PENDING_MCP_REQUESTS[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "endpoint": "postgres",
        "capability": "query",
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Call the method directly since it's normally called in a thread
    await mcp_service._process_local_mcp_request(
        "postgres", "query", {"sql": "SELECT * FROM test"}, task_id
    )
    
    # Verify the DB service was called
    mock_db_service.execute_query.assert_called_once_with("SELECT * FROM test")
    
    # Check the request was updated
    assert PENDING_MCP_REQUESTS[task_id]["status"] == "completed"


@pytest.mark.asyncio
async def test_process_local_mcp_request_unsupported(mcp_service):
    """Test processing a local MCP request for an unsupported endpoint."""
    task_id = "test_unsupported_task"
    PENDING_MCP_REQUESTS[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "endpoint": "unsupported",
        "capability": "test",
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Call the method directly
    await mcp_service._process_local_mcp_request(
        "unsupported", "test", {}, task_id
    )
    
    # Check the request was updated with an error
    assert PENDING_MCP_REQUESTS[task_id]["status"] == "error"
    assert "Unsupported local MCP endpoint" in PENDING_MCP_REQUESTS[task_id]["error"]


@pytest.mark.asyncio
async def test_process_remote_mcp_request_success(mcp_service):
    """Test processing a remote MCP request with success."""
    task_id = "test_remote_task"
    PENDING_MCP_REQUESTS[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "endpoint": "test_remote",
        "capability": "test_capability",
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Mock successful HTTP request
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success", "data": "test result"}
    
    with patch('requests.Session.post', return_value=mock_response):
        # Call the method directly
        mcp_service._process_remote_mcp_request(
            "https://test.example.com/mcp/test_capability",
            {"Content-Type": "application/json"},
            {"param": "value"},
            task_id,
            "test_remote",
            "test_capability"
        )
        
        # Sleep briefly to let the thread complete
        time.sleep(0.1)
        
        # Check the request was updated
        assert PENDING_MCP_REQUESTS[task_id]["status"] == "completed"
        assert PENDING_MCP_REQUESTS[task_id]["result"]["status"] == "success"


@pytest.mark.asyncio
async def test_process_remote_mcp_request_error(mcp_service):
    """Test processing a remote MCP request with an error."""
    task_id = "test_remote_error_task"
    PENDING_MCP_REQUESTS[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "endpoint": "test_remote",
        "capability": "test_capability",
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Mock HTTP request error
    with patch('requests.Session.post', side_effect=Exception("Test error")):
        # Call the method directly
        mcp_service._process_remote_mcp_request(
            "https://test.example.com/mcp/test_capability",
            {"Content-Type": "application/json"},
            {"param": "value"},
            task_id,
            "test_remote",
            "test_capability"
        )
        
        # Sleep briefly to let the thread complete
        time.sleep(0.1)
        
        # Check the request was updated with an error
        assert PENDING_MCP_REQUESTS[task_id]["status"] == "error"
        assert "Test error" in PENDING_MCP_REQUESTS[task_id]["error"]


@pytest.mark.asyncio
async def test_check_status_completed(mcp_service):
    """Test checking the status of a completed task."""
    task_id = "test_completed_task"
    PENDING_MCP_REQUESTS[task_id] = {
        "task_id": task_id,
        "status": "completed",
        "endpoint": "test_remote",
        "capability": "test_capability",
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "result": {"status": "success", "data": "test result"}
    }
    
    result = await mcp_service.check_status(task_id)
    assert result["status"] == "completed"
    assert result["task_id"] == task_id
    assert result["result"]["data"] == "test result"


@pytest.mark.asyncio
async def test_check_status_not_found(mcp_service):
    """Test checking the status of a non-existent task."""
    result = await mcp_service.check_status("non_existent_task")
    assert result["status"] == "error"
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_check_status_pending(mcp_service):
    """Test checking the status of a pending task."""
    task_id = "test_pending_task"
    PENDING_MCP_REQUESTS[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "endpoint": "test_remote",
        "capability": "test_capability",
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    result = await mcp_service.check_status(task_id)
    assert result["status"] == "pending"
    assert result["task_id"] == task_id
    assert "started_at" in result 
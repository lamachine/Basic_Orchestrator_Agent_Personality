"""
Unit tests for the API interface.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from .....src.common.ui.adapters.api.interface import APIInterface


@pytest.fixture
def mock_agent():
    """Create a mock agent."""
    agent = MagicMock()
    agent.process_message = MagicMock(return_value="Test response")
    return agent


@pytest.fixture
def api_interface(mock_agent):
    """Create an API interface instance."""
    return APIInterface(mock_agent)


@pytest.fixture
def test_client(api_interface):
    """Create a test client."""
    return TestClient(api_interface.app)


def test_api_interface_initialization(mock_agent):
    """Test API interface initialization."""
    interface = APIInterface(mock_agent)
    assert isinstance(interface.app, FastAPI)
    assert interface.agent == mock_agent


def test_chat_endpoint(test_client, mock_agent):
    """Test the chat endpoint."""
    response = test_client.post("/chat", json={"message": "Test message"})
    assert response.status_code == 200
    assert response.json() == {"response": "Test response"}
    mock_agent.process_message.assert_called_once_with("Test message")


def test_chat_endpoint_invalid_input(test_client):
    """Test chat endpoint with invalid input."""
    response = test_client.post("/chat", json={})
    assert response.status_code == 422


def test_status_endpoint(test_client, mock_agent):
    """Test the status endpoint."""
    mock_agent.get_status = MagicMock(return_value={"status": "active"})
    response = test_client.get("/status")
    assert response.status_code == 200
    assert response.json() == {"status": "active"}
    mock_agent.get_status.assert_called_once()


@pytest.mark.asyncio
async def test_start_method(api_interface):
    """Test the start method."""
    with patch("uvicorn.run") as mock_run:
        await api_interface.start()
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == api_interface.app
        assert kwargs["host"] == "0.0.0.0"
        assert kwargs["port"] == 8000

"""Test script for personal assistant sub-graph."""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from src.config.logging_config import get_log_config, setup_logging
from src.state.state_models import MessageRole
from src.sub_graphs.personal_assistant_agent.src.graphs.personal_assistant_graph import (
    personal_assistant_graph,
)
from src.tools.initialize_tools import get_registry

# Setup logging with our configuration system
config = {
    "file_level": logging.DEBUG,
    "console_level": logging.DEBUG,
    "log_dir": os.path.join(os.getcwd(), "logs"),
    "max_log_size_mb": 10,
    "backup_count": 5,
}

setup_logging(config)
logger = logging.getLogger(__name__)

# Enable debug logging for google auth libraries
for google_logger in ["googleapiclient", "google_auth_oauthlib", "google.auth"]:
    logging.getLogger(google_logger).setLevel(logging.DEBUG)
    # Ensure they use the root logger's handlers
    google_logger_instance = logging.getLogger(google_logger)
    google_logger_instance.handlers = []
    google_logger_instance.propagate = True


class TestConfig:
    """Test configuration."""

    def __init__(self):
        """Initialize test configuration."""
        self.original_env = dict(os.environ)
        self.validate_google_credentials()
        self.setup()

    def validate_google_credentials(self):
        """Validate Google credentials."""
        credentials_path = os.getenv(
            "GOOGLE_CREDENTIALS_FILE",
            "C:\\Users\\Owner\\secure_credentials\\google_client_secret.json",
        )
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"Google credentials file not found at {credentials_path}")
        logger.debug(f"Found Google credentials at {credentials_path}")

    def setup(self):
        """Setup test environment."""
        # Update environment variables for Gmail
        os.environ["GMAIL_ENABLED"] = "true"
        os.environ["GMAIL_CREDENTIALS_PATH"] = (
            "C:\\Users\\Owner\\secure_credentials\\google_client_secret.json"
        )
        os.environ["GOOGLE_CLIENT_SECRET_FILE"] = (
            "C:\\Users\\Owner\\secure_credentials\\google_client_secret.json"
        )
        os.environ["GOOGLE_CREDENTIALS_FILE"] = (
            "C:\\Users\\Owner\\secure_credentials\\google_client_secret.json"
        )

        # Core services
        os.environ["api_url"] = "http://localhost:11434"
        os.environ["default_model"] = "llama3.1"
        os.environ["OLLAMA_EMBEDDING_MODEL"] = "nomic-embed-text"

        # Supabase
        os.environ["url"] = "http://localhost:8000"
        os.environ["anon_key"] = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
        )
        os.environ["service_role_key"] = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"
        )

        # Character
        os.environ["CHARACTER_FILE"] = "src\\agents\\Character_Ronan_valet_orchestrator.json"

        # Setup test environment
        env_updates = {
            # Core services configuration
            "DATABASE_URL": "http://localhost:8000",  # Updated to use Kong gateway
            "LLM_API_URL": "http://localhost:11434",
            "LLM_MODEL": "llama2",
        }

        os.environ.update(env_updates)
        logger.debug("Updated environment variables:")
        for key, value in env_updates.items():
            logger.debug(f"  {key}: {value}")

    def cleanup(self):
        """Restore original environment."""
        os.environ.clear()
        os.environ.update(self.original_env)


def create_test_state() -> Dict[str, Any]:
    """Create a test state for the personal assistant.

    Returns:
        Dict[str, Any]: Initialized state dictionary for testing
    """
    state = {
        "messages": [],  # Empty list of messages
        "conversation_state": {},  # Empty dict for conversation state
        "agent_states": {},  # Empty dict for agent states
        "current_task": None,
        "task_history": [],
        "agent_results": {},
        "final_result": None,
    }
    return state


@pytest.mark.asyncio
async def test_personal_assistant():
    """Test personal assistant sub-graph."""
    logger.debug("Starting personal assistant test")

    # Setup test configuration
    config = TestConfig()

    # Create test state
    state = create_test_state()

    # Create test request to check unread emails
    request = {"task": "check unread emails"}

    try:
        # Process request
        logger.debug("Processing test request...")
        result = await personal_assistant_graph(state, request)

        # Check result
        logger.debug(f"Test completed with success={result.get('success', False)}")
        if not result.get("success", False):
            logger.error(f"Test failed: {result.get('error', 'Unknown error')}")

        # Log message history
        logger.debug(f"Message history contains {len(state['messages'])} messages")

        assert result.get("success", False), f"Test failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        raise
    finally:
        # Cleanup test environment
        config.cleanup()


@pytest.mark.asyncio
async def test_send_email():
    """Test sending email through personal assistant sub-graph."""
    logger.debug("Starting send email test")

    # Setup test configuration
    config = TestConfig()

    # Create test state
    state = create_test_state()

    # Create test request to send email
    email_params = {
        "action": "send",
        "to": "your.test.email@gmail.com",  # Replace with your test email
        "subject": "Test Email from Personal Assistant",
        "body": "This is a test email sent by the personal assistant test suite.",
    }

    request = {"task": json.dumps(email_params)}

    try:
        # Process request
        logger.debug(f"Processing email request with parameters: {request}")
        result = await personal_assistant_graph(state, request)

        # Check result
        logger.debug(f"Test completed with success={result.get('success', False)}")
        if not result.get("success", False):
            logger.error(f"Test failed: {result.get('error', 'Unknown error')}")

        # Log message history
        logger.debug(f"Message history contains {len(state['messages'])} messages")

        # Verify the result
        assert result.get("success", False), f"Test failed: {result.get('error', 'Unknown error')}"
        assert result.get("message_id"), "No message ID returned for sent email"

    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        raise
    finally:
        # Cleanup test environment
        config.cleanup()


def test_tool_message_passing_success():
    registry = get_registry()
    tool_class = registry.get_tool("personal_assistant")
    assert tool_class is not None, "personal_assistant tool not found in registry"
    response = tool_class(
        task="check unread emails",
        parameters={"folder": "inbox"},
        request_id="test-req-001",
    )
    assert response["status"] in ("success", "completed")
    assert response["request_id"] == "test-req-001"
    assert "timestamp" in response
    assert "message" in response


def test_tool_message_passing_missing_request_id():
    registry = get_registry()
    tool_class = registry.get_tool("personal_assistant")
    assert tool_class is not None, "personal_assistant tool not found in registry"
    response = tool_class(
        task="check unread emails", parameters={"folder": "inbox"}, request_id=None
    )
    assert response["status"] == "error"
    assert "request_id" in response
    assert response["request_id"] is None


def test_tool_message_passing_invalid_input():
    registry = get_registry()
    tool_class = registry.get_tool("personal_assistant")
    assert tool_class is not None, "personal_assistant tool not found in registry"
    response = tool_class(task=None, parameters={"folder": "inbox"}, request_id="test-req-003")
    assert response["status"] == "error"


if __name__ == "__main__":
    # Run both tests
    asyncio.run(test_personal_assistant())
    asyncio.run(test_send_email())

    print("\nAll tests completed")

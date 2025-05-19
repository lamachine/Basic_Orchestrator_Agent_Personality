"""Tests for the email tool."""

from datetime import datetime
from typing import Any, Dict

import pytest

from src.tools.email_tool import EmailConfig, EmailTool


@pytest.fixture
def email_config() -> Dict[str, Any]:
    """Create a test email configuration."""
    return {
        "smtp_server": "smtp.test.com",
        "smtp_port": 587,
        "username": "test@test.com",
        "password": "test_password",
        "default_from": "test@test.com",
        "use_ssl": True,
        "timeout": 30,
    }


@pytest.fixture
def email_tool(email_config: Dict[str, Any]) -> EmailTool:
    """Create a test email tool instance."""
    return EmailTool(email_config)


@pytest.mark.asyncio
async def test_send_email_success(email_tool: EmailTool):
    """Test successful email sending."""
    args = {
        "action": "send_email",
        "request_id": "test-123",
        "to": "recipient@test.com",
        "subject": "Test Subject",
        "body": "Test Body",
    }

    result = await email_tool.execute(args)

    assert result["status"] == "success"
    assert result["request_id"] == "test-123"
    assert result["message"] == "Email sent successfully"
    assert "data" in result
    assert result["data"]["to"] == "recipient@test.com"
    assert result["data"]["subject"] == "Test Subject"
    assert "timestamp" in result["data"]


@pytest.mark.asyncio
async def test_send_email_missing_fields(email_tool: EmailTool):
    """Test email sending with missing required fields."""
    args = {
        "action": "send_email",
        "request_id": "test-123",
        "to": "recipient@test.com",
        # Missing subject and body
    }

    result = await email_tool.execute(args)

    assert result["status"] == "error"
    assert result["request_id"] == "test-123"
    assert "Missing required email fields" in result["message"]


@pytest.mark.asyncio
async def test_list_emails_success(email_tool: EmailTool):
    """Test successful email listing."""
    args = {"action": "list_emails", "request_id": "test-123"}

    result = await email_tool.execute(args)

    assert result["status"] == "success"
    assert result["request_id"] == "test-123"
    assert result["message"] == "Emails retrieved successfully"
    assert "data" in result
    assert "emails" in result["data"]
    assert len(result["data"]["emails"]) > 0
    assert "id" in result["data"]["emails"][0]
    assert "subject" in result["data"]["emails"][0]
    assert "from" in result["data"]["emails"][0]
    assert "timestamp" in result["data"]["emails"][0]


@pytest.mark.asyncio
async def test_get_email_success(email_tool: EmailTool):
    """Test successful email retrieval."""
    args = {"action": "get_email", "request_id": "test-123", "email_id": "1"}

    result = await email_tool.execute(args)

    assert result["status"] == "success"
    assert result["request_id"] == "test-123"
    assert result["message"] == "Email retrieved successfully"
    assert "data" in result
    assert result["data"]["id"] == "1"
    assert "subject" in result["data"]
    assert "from" in result["data"]
    assert "body" in result["data"]
    assert "timestamp" in result["data"]


@pytest.mark.asyncio
async def test_get_email_missing_id(email_tool: EmailTool):
    """Test email retrieval with missing email ID."""
    args = {
        "action": "get_email",
        "request_id": "test-123",
        # Missing email_id
    }

    result = await email_tool.execute(args)

    assert result["status"] == "error"
    assert result["request_id"] == "test-123"
    assert "No email ID specified" in result["message"]


@pytest.mark.asyncio
async def test_unknown_action(email_tool: EmailTool):
    """Test handling of unknown action."""
    args = {"action": "unknown_action", "request_id": "test-123"}

    result = await email_tool.execute(args)

    assert result["status"] == "error"
    assert result["request_id"] == "test-123"
    assert "Unknown action" in result["message"]


@pytest.mark.asyncio
async def test_missing_action(email_tool: EmailTool):
    """Test handling of missing action."""
    args = {
        "request_id": "test-123"
        # Missing action
    }

    result = await email_tool.execute(args)

    assert result["status"] == "error"
    assert result["request_id"] == "test-123"
    assert "No action specified" in result["message"]

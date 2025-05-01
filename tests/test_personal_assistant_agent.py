# All test code is disabled for the minimal orchestrator.
"""Tests for the personal assistant agent."""

import pytest
from unittest.mock import Mock, AsyncMock
# from src.sub_graph_personal_assistant.agents.personal_assistant_agent import PersonalAssistantAgent, ToolRegistry  # (disabled for minimal orchestrator)
# from src.sub_graph_personal_assistant.config.config import PersonalAssistantConfig  # (disabled for minimal orchestrator)

@pytest.fixture
def mock_gmail_tool():
    """Create a mock Gmail tool."""
    tool = AsyncMock()
    tool.initialize = AsyncMock(return_value=True)
    tool.cleanup = AsyncMock()
    tool.execute = AsyncMock(return_value={"success": True, "message_id": "123"})
    return tool

@pytest.fixture
def mock_slack_tool():
    """Create a mock Slack tool."""
    tool = AsyncMock()
    tool.initialize = AsyncMock(return_value=True)
    tool.cleanup = AsyncMock()
    tool.execute = AsyncMock(return_value={"success": True, "channel": "general"})
    return tool

@pytest.fixture
def config():
    """Create a test configuration."""
    return PersonalAssistantConfig(
        gmail_enabled=True,
        slack_enabled=True
    )

@pytest.mark.asyncio
async def test_agent_initialization(config, mock_gmail_tool, mock_slack_tool, monkeypatch):
    """Test agent initialization."""
    # Mock tool creation
    monkeypatch.setattr("src.sub_graph_personal_assistant.tools.gmail.GmailTool", lambda _: mock_gmail_tool)
    monkeypatch.setattr("src.sub_graph_personal_assistant.tools.slack_tool.SlackTool", lambda _: mock_slack_tool)
    
    # Create and initialize agent
    agent = PersonalAssistantAgent(config)
    success = await agent.initialize()
    
    assert success
    assert agent._initialized
    assert isinstance(agent.tools, ToolRegistry)
    assert agent.tools.gmail == mock_gmail_tool
    assert agent.tools.slack == mock_slack_tool
    assert agent.source == "personal_assistant_graph.system"

@pytest.mark.asyncio
async def test_process_gmail_task(config, mock_gmail_tool, monkeypatch):
    """Test processing Gmail tasks."""
    # Mock Gmail tool
    monkeypatch.setattr("src.sub_graph_personal_assistant.tools.gmail.GmailTool", lambda _: mock_gmail_tool)
    
    # Create and initialize agent
    agent = PersonalAssistantAgent(config)
    await agent.initialize()
    
    # Test sending email
    result = await agent.process_task(
        "send email to test@example.com subject Hello body This is a test"
    )
    assert result["success"]
    mock_gmail_tool.execute.assert_called_once()
    
    # Test error handling
    mock_gmail_tool.execute.reset_mock()
    mock_gmail_tool.execute.return_value = {"success": False, "error": "Failed to send"}
    result = await agent.process_task("send email")  # Missing parameters
    assert not result["success"]
    assert "error" in result

@pytest.mark.asyncio
async def test_process_slack_task(config, mock_slack_tool, monkeypatch):
    """Test processing Slack tasks."""
    # Mock Slack tool
    monkeypatch.setattr("src.sub_graph_personal_assistant.tools.slack_tool.SlackTool", lambda _: mock_slack_tool)
    
    # Create and initialize agent
    agent = PersonalAssistantAgent(config)
    await agent.initialize()
    
    # Test sending message
    result = await agent.process_task(
        "send slack message to #general: Hello team"
    )
    assert not result["success"]  # Should fail as not implemented yet
    assert "not yet implemented" in result["error"].lower()

@pytest.mark.asyncio
async def test_cleanup(config, mock_gmail_tool, mock_slack_tool, monkeypatch):
    """Test agent cleanup."""
    # Mock tools
    monkeypatch.setattr("src.sub_graph_personal_assistant.tools.gmail.GmailTool", lambda _: mock_gmail_tool)
    monkeypatch.setattr("src.sub_graph_personal_assistant.tools.slack_tool.SlackTool", lambda _: mock_slack_tool)
    
    # Create and initialize agent
    agent = PersonalAssistantAgent(config)
    await agent.initialize()
    
    # Cleanup
    await agent.cleanup()
    assert not agent._initialized
    mock_gmail_tool.cleanup.assert_called_once()
    mock_slack_tool.cleanup.assert_called_once() 
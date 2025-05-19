"""
Unit tests for the CLI entry point.
"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ..src.run_cli import run_with_cli_interface


@pytest.fixture
def mock_agent():
    """Create a mock agent."""
    agent = MagicMock()
    agent.initialize = MagicMock(return_value=None)
    agent.start = MagicMock(return_value=None)
    return agent


@pytest.fixture
def mock_session():
    """Create a mock session."""
    session = MagicMock()
    session.id = "test_session"
    return session


@pytest.mark.asyncio
async def test_run_with_cli_interface(mock_agent, mock_session):
    """Test running with CLI interface."""
    with (
        patch(
            "src.sub_graphs.template_agent.src.run_cli.TemplateAgent",
            return_value=mock_agent,
        ),
        patch(
            "src.sub_graphs.template_agent.src.run_cli.SessionManager.create_session",
            return_value=mock_session,
        ),
        patch("src.sub_graphs.template_agent.src.run_cli.setup_logging"),
    ):

        await run_with_cli_interface()

        # Verify agent was initialized and started
        mock_agent.initialize.assert_called_once()
        mock_agent.start.assert_called_once()


@pytest.mark.asyncio
async def test_run_with_cli_interface_error_handling():
    """Test error handling in CLI interface."""
    with (
        patch(
            "src.sub_graphs.template_agent.src.run_cli.TemplateAgent",
            side_effect=Exception("Test error"),
        ),
        patch("src.sub_graphs.template_agent.src.run_cli.setup_logging"),
        pytest.raises(Exception) as exc_info,
    ):

        await run_with_cli_interface()

        assert "Test error" in str(exc_info.value)


def test_graph_path_setting():
    """Test that graph path is properly set."""
    from src.sub_graphs.template_agent.src.run_cli import _set_graph_path

    path = _set_graph_path()
    assert isinstance(path, Path)
    assert path.name == "template_agent"

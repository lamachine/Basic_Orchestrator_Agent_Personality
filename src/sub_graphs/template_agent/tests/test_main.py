"""
Unit tests for the main entry point.
"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ..src.main import find_personality_file, initialize_agent, main, run_with_interface


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


def test_find_personality_file():
    """Test finding personality file."""
    # Test with provided path
    test_path = Path("test_personality.json")
    with patch.object(Path, "exists", return_value=True):
        result = find_personality_file(test_path)
        assert result == test_path

    # Test with default path
    default_path = Path("personalities/default.json")
    with patch.object(Path, "exists", return_value=True):
        result = find_personality_file(None)
        assert result == default_path

    # Test with non-existent file
    with (
        patch.object(Path, "exists", return_value=False),
        pytest.raises(FileNotFoundError),
    ):
        find_personality_file(test_path)


def test_initialize_agent(mock_agent):
    """Test agent initialization."""
    with patch("src.sub_graphs.template_agent.src.main.TemplateAgent", return_value=mock_agent):
        agent = initialize_agent()
        assert agent == mock_agent
        mock_agent.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_run_with_interface_cli(mock_agent, mock_session):
    """Test running with CLI interface."""
    with (
        patch(
            "src.sub_graphs.template_agent.src.main.TemplateAgent",
            return_value=mock_agent,
        ),
        patch(
            "src.sub_graphs.template_agent.src.main.SessionManager.create_session",
            return_value=mock_session,
        ),
        patch("src.sub_graphs.template_agent.src.main.setup_logging"),
    ):

        await run_with_interface("cli")

        mock_agent.initialize.assert_called_once()
        mock_agent.start.assert_called_once()


@pytest.mark.asyncio
async def test_run_with_interface_api(mock_agent, mock_session):
    """Test running with API interface."""
    with (
        patch(
            "src.sub_graphs.template_agent.src.main.TemplateAgent",
            return_value=mock_agent,
        ),
        patch(
            "src.sub_graphs.template_agent.src.main.SessionManager.create_session",
            return_value=mock_session,
        ),
        patch("src.sub_graphs.template_agent.src.main.setup_logging"),
        patch("src.sub_graphs.template_agent.src.main.APIInterface") as mock_api,
    ):

        mock_api_instance = MagicMock()
        mock_api.return_value = mock_api_instance

        await run_with_interface("api")

        mock_agent.initialize.assert_called_once()
        mock_api_instance.start.assert_called_once()


def test_main_cli():
    """Test main function with CLI interface."""
    with patch("src.sub_graphs.template_agent.src.main.run_with_interface") as mock_run:
        main(["--interface", "cli"])
        mock_run.assert_called_once_with("cli", None, None)


def test_main_api():
    """Test main function with API interface."""
    with patch("src.sub_graphs.template_agent.src.main.run_with_interface") as mock_run:
        main(["--interface", "api"])
        mock_run.assert_called_once_with("api", None, None)


def test_main_with_personality():
    """Test main function with personality file."""
    with patch("src.sub_graphs.template_agent.src.main.run_with_interface") as mock_run:
        main(["--interface", "cli", "--personality", "test.json"])
        mock_run.assert_called_once_with("cli", None, Path("test.json"))


def test_main_with_session():
    """Test main function with session ID."""
    with patch("src.sub_graphs.template_agent.src.main.run_with_interface") as mock_run:
        main(["--interface", "cli", "--session", "test_session"])
        mock_run.assert_called_once_with("cli", "test_session", None)

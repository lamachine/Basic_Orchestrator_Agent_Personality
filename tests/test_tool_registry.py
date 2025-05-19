"""
Tests for the tool registry system.

These tests validate the tool registry's ability to discover, validate, and
register tool agents according to our standardized structure.
"""

import importlib
import logging
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from src.tools.registry.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


# Test fixtures
@pytest.fixture
def mock_sub_graphs_dir():
    """Create a temporary directory with mock tool agent structures."""
    temp_dir = tempfile.mkdtemp()
    sub_graphs_dir = Path(temp_dir) / "src" / "sub_graphs"
    sub_graphs_dir.mkdir(parents=True)

    # Create a valid tool agent structure
    valid_agent_dir = sub_graphs_dir / "test_agent"
    valid_agent_dir.mkdir(parents=True)
    config_dir = valid_agent_dir / "src" / "config"
    config_dir.mkdir(parents=True)

    # Create valid config file
    with open(config_dir / "tool_config.yaml", "w") as f:
        yaml.dump(
            {
                "name": "test_tool",
                "description": "A test tool for validation",
                "version": "0.1.0",
                "config": {"test_param": "value"},
                "capabilities": ["testing"],
            },
            f,
        )

    # Create invalid agent directory (missing config)
    invalid_agent_dir = sub_graphs_dir / "invalid_agent"
    invalid_agent_dir.mkdir(parents=True)
    (invalid_agent_dir / "src").mkdir(parents=True)

    # Create non-agent directory (no _agent suffix)
    non_agent_dir = sub_graphs_dir / "not_an_agent"
    non_agent_dir.mkdir(parents=True)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def registry_with_mock_dir(tmp_path):
    """Create a registry with a temporary directory."""
    registry = ToolRegistry(data_dir=str(tmp_path))
    return registry


@pytest.fixture
def mock_tool_module(tmp_path):
    """Create a mock tool module for testing."""
    # Create a mock tool directory
    tool_dir = tmp_path / "test_agent"
    tool_dir.mkdir()

    # Create a mock tool file
    tool_file = tool_dir / "test_tool.py"
    tool_file.write_text(
        """
def test_tool():
    \"\"\"Test tool description\"\"\"
    return "test result"
test_tool.description = "Test tool"
test_tool.version = "1.0.0"
test_tool.capabilities = ["test"]
test_tool.example = "test_tool()"
"""
    )

    return tool_dir


# Tests that should pass - expected use cases
@pytest.mark.asyncio
async def test_discover_tools(registry_with_mock_dir, mock_tool_module):
    """Test tool discovery."""
    # Arrange
    registry = registry_with_mock_dir

    # Act
    await registry.discover_tools()

    # Assert
    assert "test_tool" in registry.tools
    assert "test_tool" in registry.tool_configs
    assert registry.tool_configs["test_tool"]["description"] == "Test tool"
    assert registry.tool_configs["test_tool"]["version"] == "1.0.0"
    assert registry.tool_configs["test_tool"]["capabilities"] == ["test"]
    assert registry.tool_configs["test_tool"]["example"] == "test_tool()"


@pytest.mark.asyncio
async def test_get_tool(registry_with_mock_dir, mock_tool_module):
    """Test getting a tool."""
    # Arrange
    registry = registry_with_mock_dir
    await registry.discover_tools()

    # Act
    tool = registry.get_tool("test_tool")

    # Assert
    assert tool is not None
    assert tool.description == "Test tool"
    assert tool.version == "1.0.0"
    assert tool.capabilities == ["test"]
    assert tool.example == "test_tool()"


@pytest.mark.asyncio
async def test_get_config(registry_with_mock_dir, mock_tool_module):
    """Test getting a tool's config."""
    # Arrange
    registry = registry_with_mock_dir
    await registry.discover_tools()

    # Act
    config = registry.get_config("test_tool")

    # Assert
    assert config is not None
    assert config["description"] == "Test tool"
    assert config["version"] == "1.0.0"
    assert config["capabilities"] == ["test"]
    assert config["example"] == "test_tool()"


@pytest.mark.asyncio
async def test_list_tools(registry_with_mock_dir, mock_tool_module):
    """Test listing tools."""
    # Arrange
    registry = registry_with_mock_dir
    await registry.discover_tools()

    # Act
    tools = registry.list_tools()

    # Assert
    assert "test_tool" in tools
    assert len(tools) == 1


@pytest.mark.asyncio
async def test_persist_state(registry_with_mock_dir, mock_tool_module):
    """Test state persistence."""
    # Arrange
    registry = registry_with_mock_dir
    await registry.discover_tools()

    # Act
    registry._persist_state()

    # Create new registry and load state
    new_registry = ToolRegistry(data_dir=str(registry_with_mock_dir.data_dir))
    new_registry._load_persisted_state()

    # Assert
    assert "test_tool" in new_registry.tool_configs
    assert new_registry.tool_configs["test_tool"]["description"] == "Test tool"
    assert new_registry.tool_configs["test_tool"]["version"] == "1.0.0"
    assert new_registry.tool_configs["test_tool"]["capabilities"] == ["test"]
    assert new_registry.tool_configs["test_tool"]["example"] == "test_tool()"


# Tests that should fail
@pytest.mark.asyncio
async def test_discover_tools_ignores_invalid_agent(registry_with_mock_dir):
    """Test that the registry ignores invalid agent directories."""
    # Act - discover tools
    discovered_tools = await registry_with_mock_dir.discover_tools()

    # Assert - should not find our invalid_agent (no tool_config.yaml)
    assert "invalid_agent" not in registry_with_mock_dir.tool_configs
    for tool in discovered_tools:
        assert "invalid" not in tool


# Edge cases
@pytest.mark.asyncio
async def test_discover_tools_empty_directory(registry_with_mock_dir):
    """Test tool discovery with an empty sub_graphs directory."""
    # Arrange - clear out the mock sub_graphs directory
    sub_graphs_dir = Path(registry_with_mock_dir.data_dir).parent.parent / "src" / "sub_graphs"
    for item in sub_graphs_dir.iterdir():
        if item.is_dir():
            shutil.rmtree(item)

    # Act - discover tools in empty directory
    discovered_tools = await registry_with_mock_dir.discover_tools()

    # Assert - should return empty list, not error
    assert discovered_tools == []
    assert len(registry_with_mock_dir.tool_configs) == 0


if __name__ == "__main__":
    pytest.main(["-v", __file__])

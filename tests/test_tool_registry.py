"""
Tests for the tool registry system.

These tests validate the tool registry's ability to discover, validate, and
register tool agents according to our standardized structure.
"""

import pytest
import os
import shutil
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from src.tools.registry.tool_registry import ToolRegistry

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
        yaml.dump({
            "name": "test_tool",
            "description": "A test tool for validation",
            "version": "0.1.0",
            "config": {"test_param": "value"},
            "capabilities": ["testing"]
        }, f)
    
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
def registry_with_mock_dir(mock_sub_graphs_dir):
    """Create a ToolRegistry that uses the mock directory."""
    with patch('src.tools.registry.tool_registry.Path') as mock_path:
        # Mock the data directory to be in our temp dir
        data_dir = Path(mock_sub_graphs_dir) / "data" / "tool_registry"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Make real Path calls to our mock directory structure
        def path_side_effect(path_str):
            if path_str == "src/data/tool_registry":
                return data_dir
            elif path_str == "src/sub_graphs":
                return Path(mock_sub_graphs_dir) / "src" / "sub_graphs"
            else:
                # For other paths, use the real Path
                return Path(path_str)
        
        mock_path.side_effect = path_side_effect
        
        registry = ToolRegistry()
        yield registry


# Tests that should pass - expected use cases
@pytest.mark.asyncio
async def test_discover_tools_finds_valid_agent(registry_with_mock_dir):
    """Test that the registry discovers a valid tool agent."""
    # Act - discover tools
    discovered_tools = await registry_with_mock_dir.discover_tools()
    
    # Assert - should find our valid test_agent
    assert "test_tool" in registry_with_mock_dir.tool_configs
    assert "test_tool" in discovered_tools
    
    # Check config was loaded properly
    config = registry_with_mock_dir.get_config("test_tool")
    assert config is not None
    assert config["name"] == "test_tool"
    assert config["description"] == "A test tool for validation"
    assert "capabilities" in config
    assert "testing" in config["capabilities"]


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


@pytest.mark.asyncio
async def test_approve_and_revoke_tool(registry_with_mock_dir):
    """Test approving and revoking a tool."""
    # Arrange - discover tools first
    await registry_with_mock_dir.discover_tools()
    
    # Act - approve the test tool
    approved = registry_with_mock_dir.approve_tool("test_tool")
    
    # Assert - should be approved
    assert approved is True
    assert "test_tool" in registry_with_mock_dir.approved_tools
    
    # Act - revoke the tool
    revoked = registry_with_mock_dir.revoke_tool("test_tool")
    
    # Assert - should be revoked
    assert revoked is True
    assert "test_tool" not in registry_with_mock_dir.approved_tools


@pytest.mark.asyncio
async def test_get_tool_only_returns_approved(registry_with_mock_dir):
    """Test that get_tool only returns approved tools."""
    # Arrange - discover tools and load a mock implementation
    await registry_with_mock_dir.discover_tools()
    mock_tool_class = MagicMock()
    registry_with_mock_dir.tools["test_tool"] = mock_tool_class
    
    # Act & Assert - Should return None for unapproved tool
    assert registry_with_mock_dir.get_tool("test_tool") is None
    
    # Act - approve the tool
    registry_with_mock_dir.approve_tool("test_tool")
    
    # Assert - Now should return the tool class
    assert registry_with_mock_dir.get_tool("test_tool") is mock_tool_class


if __name__ == "__main__":
    pytest.main(["-v", __file__]) 
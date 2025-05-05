"""
Tests for dynamic tool loading and unloading.

These tests validate that tools can be dynamically loaded and unloaded
at runtime, and that the system handles tool availability correctly.
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
def dynamic_tool_environment():
    """Create a test environment with dynamic tools that can be added/removed."""
    temp_dir = tempfile.mkdtemp()
    
    # Create main structure
    sub_graphs_dir = Path(temp_dir) / "src" / "sub_graphs"
    sub_graphs_dir.mkdir(parents=True)
    
    # Create data directory for tool registry
    data_dir = Path(temp_dir) / "data" / "tool_registry"
    data_dir.mkdir(parents=True)
    
    # Create a base tool that will always be present
    base_tool_dir = sub_graphs_dir / "base_tool_agent"
    base_tool_dir.mkdir(parents=True)
    base_config_dir = base_tool_dir / "src" / "config"
    base_config_dir.mkdir(parents=True)
    
    with open(base_config_dir / "tool_config.yaml", "w") as f:
        yaml.dump({
            "name": "base_tool",
            "description": "A basic tool that is always present",
            "version": "0.1.0"
        }, f)
    
    # Function to add a dynamic tool
    def add_tool(name, description="A dynamic tool"):
        tool_dir = sub_graphs_dir / f"{name}_agent"
        tool_dir.mkdir(parents=True)
        config_dir = tool_dir / "src" / "config"
        config_dir.mkdir(parents=True)
        
        with open(config_dir / "tool_config.yaml", "w") as f:
            yaml.dump({
                "name": name,
                "description": description,
                "version": "0.1.0"
            }, f)
            
        print(f"DEBUG: Added tool: {name} at {tool_dir}")
        return tool_dir
    
    # Function to remove a dynamic tool
    def remove_tool(name):
        tool_dir = sub_graphs_dir / f"{name}_agent"
        if tool_dir.exists():
            shutil.rmtree(tool_dir)
            print(f"DEBUG: Removed tool: {name} from {tool_dir}")
            return True
        return False
    
    # Return the environment
    tool_env = {
        "temp_dir": temp_dir,
        "sub_graphs_dir": sub_graphs_dir,
        "data_dir": data_dir,
        "add_tool": add_tool,
        "remove_tool": remove_tool
    }
    
    yield tool_env
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def dynamic_registry(dynamic_tool_environment):
    """Create a registry that uses our dynamic tool environment."""
    with patch('src.tools.registry.tool_registry.Path') as mock_path:
        # Create a side effect that redirects paths to our temp directory
        def path_side_effect(path_str):
            if path_str == "src/data/tool_registry":
                return dynamic_tool_environment["data_dir"]
            elif path_str == "src/sub_graphs":
                return dynamic_tool_environment["sub_graphs_dir"]
            else:
                return Path(path_str)
                
        mock_path.side_effect = path_side_effect
        
        # Create and initialize registry
        registry = ToolRegistry()
        registry.approved_tools.add("base_tool")  # Pre-approve base tool
        
        yield registry


# Mock orchestrator that can use the dynamic registry
class MockOrchestrator:
    """Mock orchestrator for testing dynamic tool loading."""
    
    def __init__(self, registry):
        """Initialize the mock orchestrator."""
        self.registry = registry
        self.available_tools = {}
        self.tool_calls = []
    
    async def refresh_tools(self):
        """Refresh the available tools from the registry."""
        # Discover any new tools
        await self.registry.discover_tools()
        
        # Get all approved tools
        self.available_tools = {}
        for tool_name in self.registry.list_tools():
            tool_class = self.registry.get_tool(tool_name)
            config = self.registry.get_config(tool_name)
            if tool_class and config:
                # In a real implementation, we would initialize the tool
                self.available_tools[tool_name] = {
                    "name": tool_name,
                    "description": config.get("description", ""),
                    "version": config.get("version", "")
                }
        
        return list(self.available_tools.keys())
    
    async def call_tool(self, tool_name, task_id, parameters):
        """Simulate calling a tool."""
        if tool_name not in self.available_tools:
            return {
                "status": "error",
                "message": f"Tool {tool_name} not found or not available",
                "task_id": task_id
            }
        
        # Record the call
        self.tool_calls.append({
            "tool_name": tool_name,
            "task_id": task_id,
            "parameters": parameters
        })
        
        # Return a mock response
        return {
            "status": "success",
            "message": f"Tool {tool_name} executed successfully",
            "task_id": task_id,
            "data": {"tool_name": tool_name, "parameters": parameters}
        }


@pytest.fixture
def mock_orchestrator(dynamic_registry):
    """Create a mock orchestrator with the dynamic registry."""
    return MockOrchestrator(dynamic_registry)


# Tests that should pass
@pytest.mark.asyncio
async def test_discover_initial_tools(mock_orchestrator):
    """Test discovering the initial tools."""
    # Act - refresh tools
    tool_names = await mock_orchestrator.refresh_tools()
    
    # Assert - should find the base tool
    assert "base_tool" in tool_names
    assert len(tool_names) == 1


@pytest.mark.asyncio
async def test_add_new_tool_at_runtime(mock_orchestrator, dynamic_tool_environment):
    """Test adding a new tool at runtime."""
    # Arrange - ensure initial state
    await mock_orchestrator.refresh_tools()
    initial_tool_count = len(mock_orchestrator.available_tools)
    
    # Act - add a new tool
    dynamic_tool_environment["add_tool"]("dynamic_tool_1")
    
    # Pre-approve the tool for testing
    mock_orchestrator.registry.approve_tool("dynamic_tool_1")
    
    # Refresh tools
    tool_names = await mock_orchestrator.refresh_tools()
    
    # Assert - should find the new tool
    assert "dynamic_tool_1" in tool_names
    assert len(mock_orchestrator.available_tools) == initial_tool_count + 1


# Test that should fail
@pytest.mark.asyncio
async def test_call_removed_tool(mock_orchestrator, dynamic_tool_environment):
    """Test that calling a removed tool fails appropriately."""
    # Arrange - add and then remove a tool
    dynamic_tool_environment["add_tool"]("temporary_tool")
    mock_orchestrator.registry.approve_tool("temporary_tool")
    await mock_orchestrator.refresh_tools()
    
    # Verify tool is available
    assert "temporary_tool" in mock_orchestrator.available_tools
    
    # Remove the tool
    dynamic_tool_environment["remove_tool"]("temporary_tool")
    
    # Refresh tools
    await mock_orchestrator.refresh_tools()
    
    # Act - try to call the removed tool
    result = await mock_orchestrator.call_tool(
        tool_name="temporary_tool",
        task_id="test-removed",
        parameters={"action": "test"}
    )
    
    # Assert - should get an error
    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


# Edge cases
@pytest.mark.asyncio
async def test_multiple_tool_additions_and_removals(mock_orchestrator, dynamic_tool_environment):
    """Test adding and removing multiple tools in sequence."""
    # Start with initial tools
    await mock_orchestrator.refresh_tools()
    initial_tools = set(mock_orchestrator.available_tools.keys())
    
    # Add tool 1
    dynamic_tool_environment["add_tool"]("dynamic_tool_1")
    mock_orchestrator.registry.approve_tool("dynamic_tool_1")
    await mock_orchestrator.refresh_tools()
    assert "dynamic_tool_1" in mock_orchestrator.available_tools
    
    # Add tool 2
    dynamic_tool_environment["add_tool"]("dynamic_tool_2")
    mock_orchestrator.registry.approve_tool("dynamic_tool_2")
    await mock_orchestrator.refresh_tools()
    assert "dynamic_tool_2" in mock_orchestrator.available_tools
    
    # Remove tool 1
    dynamic_tool_environment["remove_tool"]("dynamic_tool_1")
    await mock_orchestrator.refresh_tools()
    assert "dynamic_tool_1" not in mock_orchestrator.available_tools
    assert "dynamic_tool_2" in mock_orchestrator.available_tools
    
    # Add tool 3
    dynamic_tool_environment["add_tool"]("dynamic_tool_3")
    mock_orchestrator.registry.approve_tool("dynamic_tool_3")
    await mock_orchestrator.refresh_tools()
    assert "dynamic_tool_3" in mock_orchestrator.available_tools
    
    # Remove all dynamic tools
    dynamic_tool_environment["remove_tool"]("dynamic_tool_2")
    dynamic_tool_environment["remove_tool"]("dynamic_tool_3")
    await mock_orchestrator.refresh_tools()
    
    # Should be back to initial tools
    assert set(mock_orchestrator.available_tools.keys()) == initial_tools


@pytest.mark.asyncio
async def test_unapproved_tool_not_available(mock_orchestrator, dynamic_tool_environment):
    """Test that an unapproved tool is discovered but not available for use."""
    # Add tool but don't approve it
    dynamic_tool_environment["add_tool"]("unapproved_tool")
    
    # Discover tools without approving
    discovered = await mock_orchestrator.registry.discover_tools()
    assert "unapproved_tool" in discovered
    
    # Refresh tools in orchestrator
    tool_names = await mock_orchestrator.refresh_tools()
    
    # The unapproved tool should not be available
    assert "unapproved_tool" not in tool_names
    
    # Try to call it anyway
    result = await mock_orchestrator.call_tool(
        tool_name="unapproved_tool",
        task_id="test-unapproved",
        parameters={"action": "test"}
    )
    
    # Should get an error
    assert result["status"] == "error"


if __name__ == "__main__":
    pytest.main(["-v", __file__]) 
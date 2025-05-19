"""
Tests for tool registry.
"""

import pytest

from src.common.tools.tool_registry import Tool, ToolRegistry


def test_tool_registry_creation():
    """Test ToolRegistry creation."""
    registry = ToolRegistry()
    assert isinstance(registry, ToolRegistry)
    assert registry.tools == {}


def test_register_tool():
    """Test registering a tool."""
    registry = ToolRegistry()

    def test_tool():
        return "test"

    tool = Tool(name="test_tool", description="Test tool", function=test_tool)

    registry.register_tool(tool)
    assert "test_tool" in registry.tools
    assert registry.tools["test_tool"] == tool


def test_register_duplicate_tool():
    """Test registering a duplicate tool."""
    registry = ToolRegistry()

    def test_tool():
        return "test"

    tool = Tool(name="test_tool", description="Test tool", function=test_tool)

    registry.register_tool(tool)

    with pytest.raises(ValueError):
        registry.register_tool(tool)


def test_get_tool():
    """Test getting a tool."""
    registry = ToolRegistry()

    def test_tool():
        return "test"

    tool = Tool(name="test_tool", description="Test tool", function=test_tool)

    registry.register_tool(tool)
    retrieved_tool = registry.get_tool("test_tool")
    assert retrieved_tool == tool


def test_get_nonexistent_tool():
    """Test getting a nonexistent tool."""
    registry = ToolRegistry()

    with pytest.raises(KeyError):
        registry.get_tool("nonexistent_tool")


def test_list_tools():
    """Test listing tools."""
    registry = ToolRegistry()

    def test_tool1():
        return "test1"

    def test_tool2():
        return "test2"

    tool1 = Tool(name="test_tool1", description="Test tool 1", function=test_tool1)

    tool2 = Tool(name="test_tool2", description="Test tool 2", function=test_tool2)

    registry.register_tool(tool1)
    registry.register_tool(tool2)

    tools = registry.list_tools()
    assert len(tools) == 2
    assert "test_tool1" in tools
    assert "test_tool2" in tools


def test_tool_execution():
    """Test tool execution."""
    registry = ToolRegistry()

    def test_tool():
        return "test"

    tool = Tool(name="test_tool", description="Test tool", function=test_tool)

    registry.register_tool(tool)
    result = registry.execute_tool("test_tool")
    assert result == "test"


def test_tool_execution_with_args():
    """Test tool execution with arguments."""
    registry = ToolRegistry()

    def test_tool(arg1, arg2):
        return f"{arg1} {arg2}"

    tool = Tool(name="test_tool", description="Test tool", function=test_tool)

    registry.register_tool(tool)
    result = registry.execute_tool("test_tool", "hello", "world")
    assert result == "hello world"


def test_tool_execution_nonexistent():
    """Test executing a nonexistent tool."""
    registry = ToolRegistry()

    with pytest.raises(KeyError):
        registry.execute_tool("nonexistent_tool")


def test_tool_validation():
    """Test tool validation."""
    registry = ToolRegistry()

    with pytest.raises(ValueError):
        Tool(name="", description="Test tool", function=lambda: None)

    with pytest.raises(ValueError):
        Tool(name="test_tool", description="", function=lambda: None)

    with pytest.raises(ValueError):
        Tool(name="test_tool", description="Test tool", function=None)

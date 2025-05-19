"""
Tests for tool_models.py

This module tests the tool models, including:
1. ToolType enum
2. ToolParameter model validation
3. ToolDescription model validation
4. ToolRegistry model validation
"""

import asyncio
import inspect
from typing import Any, Dict, List, Optional

import pytest
from pydantic import ValidationError

from ...src.common.models.tool_models import ToolDescription, ToolParameter, ToolRegistry, ToolType


def test_tool_type_enum():
    """Test ToolType enum."""
    # Test case: Normal operation - should pass
    assert ToolType.COMMON == "common"
    assert ToolType.SPECIALTY == "specialty"
    assert ToolType.SUBGRAPH == "subgraph"

    # Test case: All enum values are strings
    for type_value in ToolType:
        assert isinstance(type_value, str)


def test_tool_parameter_validation():
    """Test ToolParameter model validation."""
    # Test case: Normal operation - should pass
    param = ToolParameter(name="test_param", type=str, description="Test parameter", required=True)

    assert param.name == "test_param"
    assert param.type == str
    assert param.description == "Test parameter"
    assert param.required is True
    assert param.default is None

    # Test with optional parameter
    param = ToolParameter(
        name="optional_param",
        type=int,
        description="Optional parameter",
        required=False,
        default=42,
    )

    assert param.name == "optional_param"
    assert param.type == int
    assert param.description == "Optional parameter"
    assert param.required is False
    assert param.default == 42


def test_tool_parameter_validation_error():
    """Test ToolParameter validation errors."""
    # Test case: Error condition - empty name
    with pytest.raises(ValueError, match="Parameter name cannot be empty"):
        ToolParameter(name="", type=str, description="Test parameter")

    # Test case: Error condition - empty description
    with pytest.raises(ValueError, match="Parameter description cannot be empty"):
        ToolParameter(name="test_param", type=str, description="")

    # Test case: Error condition - missing required fields
    with pytest.raises(ValidationError):
        ToolParameter(name="test_param", type=str)  # Missing description

    with pytest.raises(ValidationError):
        ToolParameter(name="test_param", description="Test")  # Missing type


def test_tool_parameter_edge_cases():
    """Test ToolParameter edge cases."""
    # Test case: Edge case - complex types
    param = ToolParameter(
        name="complex_param",
        type=Dict[str, Any],
        description="Complex parameter",
        required=True,
    )

    assert param.name == "complex_param"
    assert param.type == Dict[str, Any]

    # Test case: Edge case - long description
    long_desc = "A" * 1000
    param = ToolParameter(name="long_desc_param", type=str, description=long_desc)

    assert param.description == long_desc

    # Test case: Edge case - special characters in name
    param = ToolParameter(
        name="param_with_special_chars_123!@#$",
        type=str,
        description="Parameter with special chars",
    )

    assert param.name == "param_with_special_chars_123!@#$"


# Define async test function for ToolDescription testing
async def async_test_function(param1: str, param2: int = 0) -> str:
    """Test async function for ToolDescription."""
    await asyncio.sleep(0)
    return f"Result: {param1} - {param2}"


def test_tool_description_validation():
    """Test ToolDescription model validation."""
    # Test case: Normal operation - should pass
    params = {
        "param1": ToolParameter(
            name="param1", type=str, description="Test parameter 1", required=True
        ),
        "param2": ToolParameter(
            name="param2",
            type=int,
            description="Test parameter 2",
            required=False,
            default=0,
        ),
    }

    tool = ToolDescription(
        name="test_tool",
        description="Test tool",
        parameters=params,
        function=async_test_function,
        tool_type=ToolType.COMMON,
        source="test_module",
    )

    assert tool.name == "test_tool"
    assert tool.description == "Test tool"
    assert tool.parameters == params
    assert tool.function == async_test_function
    assert tool.tool_type == ToolType.COMMON
    assert tool.source == "test_module"
    assert tool.version == "1.0.0"
    assert tool.requires_graph_state is False
    assert tool.graph_state_type is None
    assert tool.capabilities == []


def test_tool_description_validation_error():
    """Test ToolDescription validation errors."""
    params = {
        "param1": ToolParameter(
            name="param1", type=str, description="Test parameter", required=True
        )
    }

    # Test case: Error condition - empty name
    with pytest.raises(ValueError, match="Tool name cannot be empty"):
        ToolDescription(
            name="",
            description="Test tool",
            parameters=params,
            function=async_test_function,
            tool_type=ToolType.COMMON,
            source="test_module",
        )

    # Test case: Error condition - empty description
    with pytest.raises(ValueError, match="Tool description cannot be empty"):
        ToolDescription(
            name="test_tool",
            description="",
            parameters=params,
            function=async_test_function,
            tool_type=ToolType.COMMON,
            source="test_module",
        )

    # Test case: Error condition - non-callable function
    with pytest.raises(ValueError, match="Function must be callable"):
        ToolDescription(
            name="test_tool",
            description="Test tool",
            parameters=params,
            function="not_a_function",  # Not callable
            tool_type=ToolType.COMMON,
            source="test_module",
        )

    # Test case: Error condition - non-async function
    def sync_function(param1: str) -> str:
        return f"Result: {param1}"

    with pytest.raises(ValueError, match="Function must be async"):
        ToolDescription(
            name="test_tool",
            description="Test tool",
            parameters=params,
            function=sync_function,  # Not async
            tool_type=ToolType.COMMON,
            source="test_module",
        )

    # Test case: Error condition - requires_graph_state without type
    with pytest.raises(ValueError, match="Graph state type must be specified"):
        ToolDescription(
            name="test_tool",
            description="Test tool",
            parameters=params,
            function=async_test_function,
            tool_type=ToolType.COMMON,
            source="test_module",
            requires_graph_state=True,  # Requires graph state but no type
            graph_state_type=None,
        )


def test_tool_description_edge_cases():
    """Test ToolDescription edge cases."""
    params = {
        "param1": ToolParameter(
            name="param1", type=str, description="Test parameter", required=True
        )
    }

    # Test case: Edge case - tool with capabilities
    tool = ToolDescription(
        name="test_tool",
        description="Test tool",
        parameters=params,
        function=async_test_function,
        tool_type=ToolType.COMMON,
        source="test_module",
        capabilities=["capability1", "capability2"],
    )

    assert tool.capabilities == ["capability1", "capability2"]

    # Test case: Edge case - tool with graph state
    class TestGraphState:
        pass

    tool = ToolDescription(
        name="test_tool",
        description="Test tool",
        parameters=params,
        function=async_test_function,
        tool_type=ToolType.COMMON,
        source="test_module",
        requires_graph_state=True,
        graph_state_type=TestGraphState,
    )

    assert tool.requires_graph_state is True
    assert tool.graph_state_type == TestGraphState

    # Test case: Edge case - tool with custom version
    tool = ToolDescription(
        name="test_tool",
        description="Test tool",
        parameters=params,
        function=async_test_function,
        tool_type=ToolType.COMMON,
        source="test_module",
        version="2.1.3",
    )

    assert tool.version == "2.1.3"


def test_tool_registry_validation():
    """Test ToolRegistry model validation."""
    # Test case: Normal operation - should pass
    params1 = {
        "param1": ToolParameter(
            name="param1", type=str, description="Test parameter", required=True
        )
    }

    tool1 = ToolDescription(
        name="tool1",
        description="Test tool 1",
        parameters=params1,
        function=async_test_function,
        tool_type=ToolType.COMMON,
        source="test_module",
    )

    params2 = {
        "param1": ToolParameter(
            name="param1", type=str, description="Test parameter", required=True
        )
    }

    tool2 = ToolDescription(
        name="tool2",
        description="Test tool 2",
        parameters=params2,
        function=async_test_function,
        tool_type=ToolType.SPECIALTY,
        source="test_module",
    )

    registry = ToolRegistry(tools={"tool1": tool1, "tool2": tool2})

    assert "tool1" in registry.tools
    assert "tool2" in registry.tools
    assert registry.tools["tool1"].name == "tool1"
    assert registry.tools["tool2"].name == "tool2"

    # Verify tool types were categorized
    assert ToolType.COMMON in registry.tool_types
    assert ToolType.SPECIALTY in registry.tool_types
    assert "tool1" in registry.tool_types[ToolType.COMMON]
    assert "tool2" in registry.tool_types[ToolType.SPECIALTY]


def test_tool_registry_validation_error():
    """Test ToolRegistry validation errors."""
    # Test case: Error condition - duplicate tool names
    params = {
        "param1": ToolParameter(
            name="param1", type=str, description="Test parameter", required=True
        )
    }

    tool1 = ToolDescription(
        name="tool",
        description="Test tool 1",
        parameters=params,
        function=async_test_function,
        tool_type=ToolType.COMMON,
        source="test_module",
    )

    tool2 = ToolDescription(
        name="tool",
        description="Test tool 2",
        parameters=params,
        function=async_test_function,
        tool_type=ToolType.SPECIALTY,
        source="test_module",
    )

    # This should validate successfully since the keys are different
    registry = ToolRegistry(tools={"tool1": tool1, "tool2": tool2})

    # But this should fail because the keys are the same
    with pytest.raises(ValueError, match="Tool names must be unique"):
        registry = ToolRegistry(tools={"tool": tool1, "tool": tool2})  # Same key as above


def test_tool_registry_edge_cases():
    """Test ToolRegistry edge cases."""
    # Test case: Edge case - empty registry
    registry = ToolRegistry()
    assert registry.tools == {}
    assert registry.tool_types == {}

    # Test case: Edge case - registry with one tool
    params = {
        "param1": ToolParameter(
            name="param1", type=str, description="Test parameter", required=True
        )
    }

    tool = ToolDescription(
        name="solo_tool",
        description="Solo test tool",
        parameters=params,
        function=async_test_function,
        tool_type=ToolType.COMMON,
        source="test_module",
    )

    registry = ToolRegistry(tools={"solo_tool": tool})

    assert len(registry.tools) == 1
    assert len(registry.tool_types) == 1
    assert "solo_tool" in registry.tool_types[ToolType.COMMON]

    # Test case: Edge case - registry with multiple tool types
    tool1 = ToolDescription(
        name="common_tool",
        description="Common test tool",
        parameters=params,
        function=async_test_function,
        tool_type=ToolType.COMMON,
        source="test_module",
    )

    tool2 = ToolDescription(
        name="specialty_tool",
        description="Specialty test tool",
        parameters=params,
        function=async_test_function,
        tool_type=ToolType.SPECIALTY,
        source="test_module",
    )

    tool3 = ToolDescription(
        name="subgraph_tool",
        description="Subgraph test tool",
        parameters=params,
        function=async_test_function,
        tool_type=ToolType.SUBGRAPH,
        source="test_module",
    )

    registry = ToolRegistry(
        tools={"common_tool": tool1, "specialty_tool": tool2, "subgraph_tool": tool3}
    )

    assert len(registry.tools) == 3
    assert len(registry.tool_types) == 3
    assert "common_tool" in registry.tool_types[ToolType.COMMON]
    assert "specialty_tool" in registry.tool_types[ToolType.SPECIALTY]
    assert "subgraph_tool" in registry.tool_types[ToolType.SUBGRAPH]

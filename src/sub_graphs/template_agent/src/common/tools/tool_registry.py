"""
Tool registry for template agent system.

This module provides the tool registry implementation for the template agent.
It manages the registration, retrieval, and execution of tools specific to
the template agent's functionality. The registry supports three types of tools:

1. Common Tools - Core functionality shared across all template agents
2. Specialty Tools - Custom tools specific to this template agent
3. Sub-graph Tools - Tools from other agents in the graph
"""

import importlib
import inspect
import json
import logging
import os
from datetime import datetime
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from ..services.logging_service import get_logger
from ..state.state_models import GraphState

logger = get_logger(__name__)


class ToolType(Enum):
    """Types of tools that can be registered."""

    COMMON = "common"
    SPECIALTY = "specialty"
    SUBGRAPH = "subgraph"


def get_tool_example(tool_func: Any, tool_name: str) -> Optional[str]:
    """
    Get tool example from various possible sources.

    Args:
        tool_func: The tool function to extract example from
        tool_name: Name of the tool for logging

    Returns:
        Example string or None if not found
    """
    # Try direct example attribute first
    if hasattr(tool_func, "example"):
        return tool_func.example

    # Try usage_examples list
    if hasattr(tool_func, "usage_examples") and tool_func.usage_examples:
        return tool_func.usage_examples[0]

    # Try docstring
    if tool_func.__doc__:
        # Look for example in docstring
        doc_lines = tool_func.__doc__.split("\n")
        for i, line in enumerate(doc_lines):
            if "example:" in line.lower() and i + 1 < len(doc_lines):
                return doc_lines[i + 1].strip()

    logger.debug(f"No example found for tool: {tool_name}")
    return None


class ToolParameter(BaseModel):
    """Parameter definition for a tool."""

    name: str = Field(..., description="Parameter name")
    type: Type = Field(..., description="Parameter type")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=True, description="Whether the parameter is required")
    default: Any = Field(default=None, description="Default value if not required")


class ToolDescription(BaseModel):
    """Description of a tool for LLM consumption."""

    name: str = Field(..., description="The name of the tool")
    description: str = Field(..., description="Description of what the tool does")
    parameters: Dict[str, ToolParameter] = Field(..., description="Parameters the tool accepts")
    function: Callable = Field(..., description="The actual function to call")
    example: Optional[str] = Field(None, description="Example usage of the tool")
    tool_type: ToolType = Field(..., description="Type of tool (common, specialty, or subgraph)")
    source: str = Field(..., description="Source module or agent of the tool")
    version: str = Field(default="1.0.0", description="Version of the tool")
    requires_graph_state: bool = Field(
        default=False, description="Whether the tool requires graph state"
    )
    graph_state_type: Optional[Type[GraphState]] = Field(
        default=None, description="Type of graph state required"
    )
    capabilities: List[str] = Field(default_factory=list, description="List of tool capabilities")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("function")
    @classmethod
    def validate_function(cls, v: Callable) -> Callable:
        """Validate that the function is callable and has the correct signature."""
        if not callable(v):
            raise ValueError("Function must be callable")

        # Check if function is async
        if not inspect.iscoroutinefunction(v):
            raise ValueError("Function must be async")

        return v

    @field_validator("parameters")
    @classmethod
    def validate_parameters(cls, v: Dict[str, ToolParameter], info) -> Dict[str, ToolParameter]:
        """Validate that parameters match the function signature."""
        if "function" not in info.data:
            return v

        sig = inspect.signature(info.data["function"])
        param_names = set(sig.parameters.keys())

        # Check for required parameters
        for name, param in v.items():
            if param.required and name not in param_names:
                raise ValueError(f"Required parameter '{name}' not found in function signature")

        return v

    @model_validator(mode="after")
    def validate_graph_state(self) -> "ToolDescription":
        """Validate graph state requirements."""
        if self.requires_graph_state and not self.graph_state_type:
            raise ValueError("Graph state type must be specified when requires_graph_state is True")
        return self


class ToolRegistry:
    """Registry of available tools for the template agent system."""

    def __init__(self, data_dir: str = "src/data/tool_registry"):
        """
        Initialize an empty tool registry.

        Args:
            data_dir: Directory for persistent storage
        """
        self._tools: Dict[str, ToolDescription] = {}
        self._tool_types: Dict[ToolType, List[str]] = {
            ToolType.COMMON: [],
            ToolType.SPECIALTY: [],
            ToolType.SUBGRAPH: [],
        }
        self._graph_state: Optional[GraphState] = None
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load any persisted state
        self._load_persisted_state()

    def _load_persisted_state(self):
        """Load persisted tool state."""
        try:
            state_file = self.data_dir / "tool_state.json"
            if state_file.exists():
                with open(state_file, "r") as f:
                    state = json.load(f)
                    # Load tool states
                    for name, tool_data in state.get("tools", {}).items():
                        if name in self._tools:
                            self._tools[name].metadata = tool_data.get("metadata", {})
        except Exception as e:
            logger.error(f"Failed to load tool state: {e}")

    def _persist_state(self):
        """Save current state to data directory."""
        try:
            state = {
                "last_updated": datetime.utcnow().isoformat(),
                "tools": {name: {"metadata": tool.metadata} for name, tool in self._tools.items()},
            }

            state_file = self.data_dir / "tool_state.json"
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to persist tool state: {e}")

    def register_tool(self, tool_description: ToolDescription) -> None:
        """
        Register a new tool in the registry.

        Args:
            tool_description: The tool description to register

        Raises:
            ValueError: If tool validation fails
        """
        # Validate tool description
        try:
            tool_description.validate()
        except Exception as e:
            raise ValueError(f"Invalid tool description: {str(e)}")

        # Check for name conflicts
        if tool_description.name in self._tools:
            raise ValueError(f"Tool with name '{tool_description.name}' already registered")

        self._tools[tool_description.name] = tool_description
        self._tool_types[tool_description.tool_type].append(tool_description.name)
        logger.debug(f"Registered {tool_description.tool_type.value} tool: {tool_description.name}")

        # Persist state
        self._persist_state()

    def set_graph_state(self, state: GraphState) -> None:
        """Set the current graph state."""
        self._graph_state = state

    def get_tool(self, name: str) -> Optional[ToolDescription]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self, tool_type: Optional[ToolType] = None) -> List[ToolDescription]:
        """
        List all tools, optionally filtered by type.

        Args:
            tool_type: Optional tool type filter

        Returns:
            List of tool descriptions
        """
        if tool_type:
            return [self._tools[name] for name in self._tool_types[tool_type]]
        return list(self._tools.values())

    def get_tool_descriptions_for_llm(
        self, tool_type: Optional[ToolType] = None
    ) -> List[Dict[str, Any]]:
        """
        Get tool descriptions formatted for LLM consumption.

        Args:
            tool_type: Optional tool type filter

        Returns:
            List of tool descriptions in LLM format
        """
        tools = self.list_tools(tool_type)
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    name: {
                        "type": str(param.type.__name__),
                        "description": param.description,
                        "required": param.required,
                        "default": param.default,
                    }
                    for name, param in tool.parameters.items()
                },
                "example": tool.example,
                "capabilities": tool.capabilities,
            }
            for tool in tools
        ]

    async def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a tool by name.

        Args:
            name: Name of the tool to execute
            **kwargs: Arguments to pass to the tool

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found
        """
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")

        if tool.requires_graph_state and not self._graph_state:
            raise ValueError("Graph state required but not set")

        try:
            # Add graph state if required
            if tool.requires_graph_state:
                kwargs["graph_state"] = self._graph_state

            # Execute tool
            result = await tool.function(**kwargs)

            # Log execution
            logger.info(f"Executed tool: {name}")

            return result

        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            raise

    async def discover_tools(self) -> None:
        """Discover and register tools from all sources."""
        # Discover common tools
        common_tools_dir = Path(__file__).parent
        await self._discover_tools_from_directory(common_tools_dir, ToolType.COMMON)

        # Discover specialty tools
        specialty_tools_dir = Path(__file__).parent.parent.parent / "specialty" / "tools"
        if specialty_tools_dir.exists():
            await self._discover_tools_from_directory(specialty_tools_dir, ToolType.SPECIALTY)

        # Discover sub-graph tools
        await self._discover_subgraph_tools()

        # Persist state after discovery
        self._persist_state()

    async def _discover_tools_from_directory(self, directory: Path, tool_type: ToolType) -> None:
        """
        Discover tools from a specific directory.

        Args:
            directory: Directory to search for tools
            tool_type: Type of tools to register
        """
        for file in directory.glob("*.py"):
            if file.name.startswith("__"):
                continue

            try:
                # Import the module
                module_name = f"{directory.parent.name}.{directory.name}.{file.stem}"
                module = importlib.import_module(module_name)

                # Look for tool registration functions
                if hasattr(module, "register_tools"):
                    await module.register_tools(self)
                elif hasattr(module, "register_tool"):
                    tool_desc = await module.register_tool()
                    if tool_desc:
                        self.register_tool(tool_desc)

            except Exception as e:
                logger.error(f"Error discovering tools from {file}: {str(e)}")

    async def _discover_subgraph_tools(self) -> None:
        """
        Discover tools from other agents in the graph.
        This looks for tools in the parent graph and other sub-graphs.
        """
        try:
            # Get parent graph tools
            parent_graph_dir = Path(__file__).parent.parent.parent.parent.parent
            if parent_graph_dir.exists():
                await self._discover_tools_from_directory(
                    parent_graph_dir / "tools", ToolType.SUBGRAPH
                )

            # Get other sub-graph tools
            sub_graphs_dir = parent_graph_dir / "sub_graphs"
            if sub_graphs_dir.exists():
                for sub_graph in sub_graphs_dir.iterdir():
                    if sub_graph.is_dir() and sub_graph.name != "template_agent":
                        tools_dir = sub_graph / "src" / "tools"
                        if tools_dir.exists():
                            await self._discover_tools_from_directory(tools_dir, ToolType.SUBGRAPH)

        except Exception as e:
            logger.error(f"Error discovering sub-graph tools: {str(e)}")


def tool_decorator(
    name: str,
    description: str,
    tool_type: ToolType,
    source: str,
    requires_graph_state: bool = False,
    graph_state_type: Optional[Type[GraphState]] = None,
    version: str = "1.0.0",
    capabilities: List[str] = None,
):
    """
    Decorator for registering tools.

    Args:
        name: Tool name
        description: Tool description
        tool_type: Type of tool
        source: Source module or agent
        requires_graph_state: Whether tool requires graph state
        graph_state_type: Type of graph state required
        version: Tool version
        capabilities: List of tool capabilities
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        # Extract parameters from function signature
        sig = inspect.signature(func)
        parameters = {}
        for name, param in sig.parameters.items():
            if name != "graph_state":  # Skip graph_state parameter
                parameters[name] = ToolParameter(
                    name=name,
                    type=(param.annotation if param.annotation != inspect.Parameter.empty else Any),
                    description=(
                        param.default.description if hasattr(param.default, "description") else ""
                    ),
                    required=param.default == inspect.Parameter.empty,
                    default=(param.default if param.default != inspect.Parameter.empty else None),
                )

        # Create tool description
        wrapper.tool_description = ToolDescription(
            name=name,
            description=description,
            parameters=parameters,
            function=wrapper,
            tool_type=tool_type,
            source=source,
            version=version,
            requires_graph_state=requires_graph_state,
            graph_state_type=graph_state_type,
            capabilities=capabilities or [],
        )

        return wrapper

    return decorator

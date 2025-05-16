"""
Tool models for template agent.

This module defines the models used for tool management in the template agent.
"""

from typing import Dict, Any, List, Optional, Union, Type, Callable
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
import inspect

class ToolType(str, Enum):
    """Types of tools that can be registered."""
    COMMON = "common"
    SPECIALTY = "specialty"
    SUBGRAPH = "subgraph"

class ToolParameter(BaseModel):
    """Parameter definition for a tool."""
    name: str = Field(..., description="Parameter name")
    type: Type = Field(..., description="Parameter type")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=True, description="Whether the parameter is required")
    default: Any = Field(default=None, description="Default value if not required")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate parameter name."""
        if not v.strip():
            raise ValueError("Parameter name cannot be empty")
        return v

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate parameter description."""
        if not v.strip():
            raise ValueError("Parameter description cannot be empty")
        return v

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
    requires_graph_state: bool = Field(default=False, description="Whether the tool requires graph state")
    graph_state_type: Optional[Type] = Field(default=None, description="Type of graph state required")
    capabilities: List[str] = Field(default_factory=list, description="List of tool capabilities")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate tool name."""
        if not v.strip():
            raise ValueError("Tool name cannot be empty")
        return v

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate tool description."""
        if not v.strip():
            raise ValueError("Tool description cannot be empty")
        return v

    @field_validator('function')
    @classmethod
    def validate_function(cls, v: Callable) -> Callable:
        """Validate that the function is callable and has the correct signature."""
        if not callable(v):
            raise ValueError("Function must be callable")
        
        # Check if function is async
        if not inspect.iscoroutinefunction(v):
            raise ValueError("Function must be async")
        
        return v

    @field_validator('parameters')
    @classmethod
    def validate_parameters(cls, v: Dict[str, ToolParameter], info) -> Dict[str, ToolParameter]:
        """Validate that parameters match the function signature."""
        if 'function' not in info.data:
            return v
            
        sig = inspect.signature(info.data['function'])
        param_names = set(sig.parameters.keys())
        
        # Check for required parameters
        for name, param in v.items():
            if param.required and name not in param_names:
                raise ValueError(f"Required parameter '{name}' not found in function signature")
        
        return v

    @model_validator(mode='after')
    def validate_graph_state(self) -> 'ToolDescription':
        """Validate graph state requirements."""
        if self.requires_graph_state and not self.graph_state_type:
            raise ValueError("Graph state type must be specified when requires_graph_state is True")
        return self

class ToolRegistry(BaseModel):
    """Registry of available tools."""
    tools: Dict[str, ToolDescription] = Field(default_factory=dict, description="Registered tools")
    tool_types: Dict[ToolType, List[str]] = Field(default_factory=dict, description="Tools by type")

    @field_validator('tools')
    @classmethod
    def validate_tools(cls, v: Dict[str, ToolDescription]) -> Dict[str, ToolDescription]:
        """Validate tool registry."""
        if not v:
            return v
        # Ensure tool names are unique
        if len(v) != len(set(v.keys())):
            raise ValueError("Tool names must be unique")
        return v

    @model_validator(mode='after')
    def validate_tool_types(self) -> 'ToolRegistry':
        """Validate tool type mappings."""
        # Ensure all tools are properly categorized
        for name, tool in self.tools.items():
            if tool.tool_type not in self.tool_types:
                self.tool_types[tool.tool_type] = []
            if name not in self.tool_types[tool.tool_type]:
                self.tool_types[tool.tool_type].append(name)
        return self 
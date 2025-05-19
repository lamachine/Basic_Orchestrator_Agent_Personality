"""Tool registry for agent system."""

from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolDescription(BaseModel):
    """Description of a tool for LLM consumption."""

    name: str = Field(..., description="The name of the tool")
    description: str = Field(..., description="Description of what the tool does")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters the tool accepts"
    )
    function: Callable = Field(..., description="The actual function to call")
    example: Optional[str] = Field(None, description="Example usage of the tool")


class ToolRegistry:
    """Registry of available tools for the agent system."""

    def __init__(self):
        """Initialize an empty tool registry."""
        self._tools: Dict[str, ToolDescription] = {}

    def register_tool(self, tool_description: ToolDescription) -> None:
        """Register a new tool in the registry."""
        self._tools[tool_description.name] = tool_description

    def get_tool(self, name: str) -> Optional[ToolDescription]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDescription]:
        """List all available tools."""
        return list(self._tools.values())

    def get_tool_descriptions_for_llm(self) -> List[Dict[str, Any]]:
        """Get tool descriptions formatted for LLM consumption."""
        tool_descriptions = []
        for tool in self._tools.values():
            tool_descriptions.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                    "example": tool.example,
                }
            )
        return tool_descriptions

    def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name with the given parameters."""
        tool = self.get_tool(name)
        if not tool:
            return {
                "status": "error",
                "message": f"Tool '{name}' not found in registry.",
            }

        try:
            result = tool.function(**kwargs)
            return result
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error executing tool '{name}': {str(e)}",
            }

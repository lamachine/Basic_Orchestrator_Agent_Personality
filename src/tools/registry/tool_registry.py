"""Tool registry that manages tool discovery and execution."""

import asyncio
import importlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


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


class ToolWrapper:
    def __init__(self, func, config=None):
        self.func = func
        self.description = getattr(
            func, "description", f"Tool for {func.__name__.replace('_tool', '')}"
        )
        self.version = getattr(func, "version", "1.0.0")
        self.capabilities = getattr(func, "capabilities", [])
        self.example = get_tool_example(func, func.__name__.replace("_tool", ""))
        self.config = config

    async def execute(self, args):
        """Execute the tool with the given arguments."""
        return (
            await self.func(**args) if asyncio.iscoroutinefunction(self.func) else self.func(**args)
        )


class ToolRegistry:
    """Tool registry that manages tool discovery and execution."""

    def __init__(self, data_dir: str = "src/data/tool_registry"):
        """
        Initialize the tool registry.

        Args:
            data_dir: Directory for persistent storage
        """
        self.tools: Dict[str, Any] = {}
        self.tool_configs: Dict[str, dict] = {}
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load any persisted state
        self._load_persisted_state()

    async def discover_tools(self):
        """Find and register all tools in sub_graphs."""
        sub_graphs = Path("src/sub_graphs")
        if not sub_graphs.exists():
            logger.warning("sub_graphs directory not found")
            return

        discovered_tools = []
        # Scan for all agent directories (ending with _agent)
        for tool_dir in sub_graphs.glob("*_agent"):
            if not tool_dir.is_dir():
                continue

            # Extract tool name from directory name
            tool_name = tool_dir.name.replace("_agent", "")
            logger.debug(f"Looking for tool '{tool_name}' in directory {tool_dir}")

            # Look for tool implementation in both possible locations
            tool_file_paths = [
                tool_dir / f"{tool_name}_tool.py",  # Direct in agent directory
                tool_dir / "src" / "tools" / f"{tool_name}_tool.py",  # In src/tools subdirectory
            ]

            for tool_file_path in tool_file_paths:
                if tool_file_path.exists():
                    logger.debug(f"Found tool file at {tool_file_path}")
                    # Convert path to module path
                    rel_path = tool_file_path.relative_to(Path("src"))
                    module_path = (
                        f"src.{rel_path.parent.as_posix().replace('/', '.')}.{tool_name}_tool"
                    )
                    try:
                        logger.debug(f"Importing module {module_path}")
                        module = importlib.import_module(module_path)
                        # Look for a function with the same name as the tool
                        tool_func = getattr(module, f"{tool_name}_tool", None)
                        if tool_func and callable(tool_func):
                            logger.debug(f"Found tool function {tool_name}_tool in {module_path}")

                            # Check for key attributes
                            has_desc = hasattr(tool_func, "description")
                            has_ver = hasattr(tool_func, "version")
                            has_cap = hasattr(tool_func, "capabilities")
                            has_ex = hasattr(tool_func, "usage_examples")

                            logger.debug(
                                f"Tool {tool_name} attributes: description={has_desc}, "
                                f"version={has_ver}, capabilities={has_cap}, examples={has_ex}"
                            )

                            if has_desc:
                                logger.debug(
                                    f"Tool {tool_name} description: {tool_func.description[:100]}..."
                                )

                            # Create tool info
                            tool_info = {
                                "name": tool_name,
                                "description": getattr(
                                    tool_func, "description", f"Tool for {tool_name}"
                                ),
                                "version": getattr(tool_func, "version", "1.0.0"),
                                "capabilities": getattr(tool_func, "capabilities", []),
                                "example": get_tool_example(tool_func, tool_name),
                            }

                            logger.debug(f"Created tool info for {tool_name}: {tool_info}")

                            # Create wrapper instance
                            tool_class = ToolWrapper(tool_func)

                            # Store tool info and instance
                            self.tool_configs[tool_name] = tool_info
                            self.tools[tool_name] = tool_class
                            discovered_tools.append(tool_name)
                            break  # Found the tool, no need to check other paths
                    except Exception as e:
                        logger.error(
                            f"Error importing tool module {module_path}: {e}",
                            exc_info=True,
                        )

            # Persist the updated state
            self._persist_state()

        if discovered_tools:
            logger.debug(
                f"Discovered and registered {len(discovered_tools)} tools: {', '.join(discovered_tools)}"
            )
        else:
            logger.debug("No tools discovered")

    def get_tool(self, name: str) -> Optional[Any]:
        """
        Get a tool class by name.

        Args:
            name: Name of the tool

        Returns:
            Tool class or None if not found
        """
        return self.tools.get(name)

    def get_config(self, name: str) -> Optional[dict]:
        """
        Get a tool's config.

        Args:
            name: Name of the tool

        Returns:
            Tool configuration or None if not found
        """
        return self.tool_configs.get(name)

    def list_tools(self) -> List[str]:
        """
        List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self.tools.keys())

    def _persist_state(self):
        """Save current state to data directory."""
        try:
            state = {
                "last_updated": datetime.utcnow().isoformat(),
                "configs": self.tool_configs,
            }

            state_file = self.data_dir / "tool_state.json"
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to persist tool state: {e}")

    def _load_persisted_state(self):
        """Load previously persisted state if it exists."""
        try:
            state_file = self.data_dir / "tool_state.json"
            if not state_file.exists():
                return

            with open(state_file) as f:
                state = json.load(f)

            self.tool_configs = state.get("configs", {})

        except Exception as e:
            logger.error(f"Failed to load persisted tool state: {e}")

    def __repr__(self) -> str:
        """String representation of the registry."""
        return f"ToolRegistry(tools={list(self.tools.keys())})"

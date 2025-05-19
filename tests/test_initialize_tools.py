"""
Unit tests for the tool initialization module.

This module contains tests for the tool initialization and discovery
functions that handle loading and registering tools in the system.
"""

import importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.initialize_tools import (
    get_registry,
    get_tool_prompt_section,
    initialize_tool_dependencies,
    initialize_tools,
)


class TestGetRegistry(unittest.TestCase):
    """Test cases for the get_registry function."""

    @patch("src.tools.initialize_tools._registry", None)
    @patch("src.tools.registry.tool_registry.ToolRegistry")
    def test_get_registry_create_new(self, mock_registry_class):
        """Test getting a new registry instance."""
        # Arrange
        mock_registry = MagicMock()
        mock_registry_class.return_value = mock_registry

        # Act
        registry = get_registry()

        # Assert
        mock_registry_class.assert_called_once()
        self.assertEqual(registry, mock_registry)

    @patch("src.tools.initialize_tools._registry")
    def test_get_registry_existing(self, mock_registry):
        """Test getting an existing registry instance."""
        # Act
        registry = get_registry()

        # Assert
        self.assertEqual(registry, mock_registry)
        # No instantiation should occur since we already have a registry


class TestInitializeTools(unittest.TestCase):
    """Test cases for the initialize_tools function."""

    @pytest.mark.asyncio
    @patch("src.tools.initialize_tools.get_registry")
    async def test_initialize_tools_success(self, mock_get_registry):
        """Test successful tool initialization."""
        # Arrange
        mock_registry = MagicMock()
        mock_registry.discover_tools = AsyncMock()
        mock_registry.list_tools.return_value = ["tool1", "tool2", "tool3"]
        mock_get_registry.return_value = mock_registry

        # Act
        result = await initialize_tools()

        # Assert
        mock_get_registry.assert_called_once()
        mock_registry.discover_tools.assert_called_once()
        mock_registry.list_tools.assert_called_once()
        self.assertEqual(result, ["tool1", "tool2", "tool3"])

    @pytest.mark.asyncio
    @patch("src.tools.initialize_tools.get_registry")
    async def test_initialize_tools_empty(self, mock_get_registry):
        """Test initialization with no tools discovered."""
        # Arrange
        mock_registry = MagicMock()
        mock_registry.discover_tools = AsyncMock()
        mock_registry.list_tools.return_value = []
        mock_get_registry.return_value = mock_registry

        # Act
        result = await initialize_tools()

        # Assert
        self.assertEqual(result, [])
        mock_registry.discover_tools.assert_called_once()
        mock_registry.list_tools.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.tools.initialize_tools.get_registry")
    async def test_initialize_tools_exception(self, mock_get_registry):
        """Test handling of exceptions during tool initialization."""
        # Arrange
        mock_registry = MagicMock()
        mock_registry.discover_tools = AsyncMock(side_effect=Exception("Discovery error"))
        mock_get_registry.return_value = mock_registry

        # Act & Assert
        with self.assertRaises(Exception):
            await initialize_tools()
        mock_registry.discover_tools.assert_called_once()


class TestGetToolPromptSection(unittest.TestCase):
    """Test cases for the get_tool_prompt_section function."""

    @patch("src.tools.initialize_tools.get_registry")
    def test_get_prompt_with_tools(self, mock_get_registry):
        """Test generating a prompt section with available tools."""
        # Arrange
        mock_registry = MagicMock()
        mock_registry.list_tools.return_value = ["tool1", "tool2"]
        mock_registry.get_config.side_effect = lambda tool_name: {
            "tool1": {
                "description": "Tool 1 description",
                "capabilities": ["capability1", "capability2"],
                "examples": ["example1", "example2"],
            },
            "tool2": {
                "description": "Tool 2 description",
                "capabilities": ["capability3", "capability4"],
                "examples": ["example3", "example4"],
            },
        }.get(tool_name, {})
        mock_get_registry.return_value = mock_registry

        # Act
        result = get_tool_prompt_section()

        # Assert
        mock_get_registry.assert_called_once()
        mock_registry.list_tools.assert_called_once()
        self.assertIn("# AVAILABLE TOOLS", result)
        self.assertIn("## tool1", result)
        self.assertIn("Tool 1 description", result)
        self.assertIn("## tool2", result)
        self.assertIn("Tool 2 description", result)
        self.assertIn("capability1", result)
        self.assertIn("example3", result)
        self.assertIn("IMPORTANT: When using tools:", result)

    @patch("src.tools.initialize_tools.get_registry")
    def test_get_prompt_no_tools(self, mock_get_registry):
        """Test generating a prompt section with no available tools."""
        # Arrange
        mock_registry = MagicMock()
        mock_registry.list_tools.return_value = []
        mock_get_registry.return_value = mock_registry

        # Act
        result = get_tool_prompt_section()

        # Assert
        self.assertIn("# AVAILABLE TOOLS", result)
        self.assertIn("No tools are currently available.", result)

    @patch("src.tools.initialize_tools.get_registry")
    def test_get_prompt_missing_config(self, mock_get_registry):
        """Test generating a prompt with a tool that has no config."""
        # Arrange
        mock_registry = MagicMock()
        mock_registry.list_tools.return_value = ["tool1", "missing_config"]
        mock_registry.get_config.side_effect = lambda tool_name: {
            "tool1": {
                "description": "Tool 1 description",
                "capabilities": ["capability1"],
                "examples": ["example1"],
            }
        }.get(tool_name, None)
        mock_get_registry.return_value = mock_registry

        # Act
        result = get_tool_prompt_section()

        # Assert
        self.assertIn("## tool1", result)
        # The missing_config tool should be silently ignored
        self.assertNotIn("## missing_config", result)


class TestInitializeToolDependencies(unittest.TestCase):
    """Test cases for the initialize_tool_dependencies function."""

    @pytest.mark.asyncio
    @patch("importlib.util.find_spec")
    async def test_initialize_dependencies_found(self, mock_find_spec):
        """Test initializing dependencies when modules are found."""
        # Arrange
        mock_find_spec.return_value = MagicMock()  # Non-None return means module exists

        # Act
        result = await initialize_tool_dependencies()

        # Assert
        mock_find_spec.assert_called_with("openai")
        self.assertTrue(result["librarian"])

    @pytest.mark.asyncio
    @patch("importlib.util.find_spec")
    async def test_initialize_dependencies_not_found(self, mock_find_spec):
        """Test initializing dependencies when modules are not found."""
        # Arrange
        mock_find_spec.return_value = None  # Module doesn't exist

        # Act
        result = await initialize_tool_dependencies()

        # Assert
        mock_find_spec.assert_called_with("openai")
        self.assertFalse(result["librarian"])

    @pytest.mark.asyncio
    @patch("importlib.util.find_spec")
    async def test_initialize_dependencies_import_error(self, mock_find_spec):
        """Test initializing dependencies when import error occurs."""
        # Arrange
        mock_find_spec.side_effect = ImportError("Import failed")

        # Act
        result = await initialize_tool_dependencies()

        # Assert
        mock_find_spec.assert_called_with("openai")
        self.assertFalse(result["librarian"])

    @pytest.mark.asyncio
    @patch("importlib.util.find_spec")
    async def test_initialize_dependencies_with_llm_agent(self, mock_find_spec):
        """Test initializing dependencies with an LLM agent."""
        # Arrange
        mock_find_spec.return_value = MagicMock()
        mock_llm_agent = MagicMock()

        # Act
        result = await initialize_tool_dependencies(llm_agent=mock_llm_agent)

        # Assert
        mock_find_spec.assert_called_with("openai")
        self.assertTrue(result["librarian"])

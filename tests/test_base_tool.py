"""
Unit tests for the BaseTool class.

This module contains tests for the BaseTool abstract base class
which provides the foundation for all tools in the system.
"""

import unittest
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.base_tool import BaseTool


# Test implementation of BaseTool for testing
class TestToolImplementation(BaseTool):
    """A concrete implementation of BaseTool for testing."""

    def __init__(self, name="test_tool", description="Test tool description"):
        super().__init__(name, description)
        self.execute_called = False
        self.execute_params = {}

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Implementation of the execute method."""
        self.execute_called = True
        self.execute_params = kwargs
        return {
            "status": "success",
            "message": "Test execution successful",
            "data": kwargs,
        }


# Tests for expected use
class TestBaseToolNormalOperations(unittest.TestCase):
    """Test cases for the normal operations of the BaseTool class."""

    def test_initialization(self):
        """Test that a BaseTool subclass initializes correctly."""
        # Arrange
        name = "test_tool"
        description = "This is a test tool"

        # Act
        tool = TestToolImplementation(name, description)

        # Assert
        self.assertEqual(tool.name, name)
        self.assertEqual(tool.description, description)

    def test_get_metadata(self):
        """Test that a BaseTool subclass returns correct metadata."""
        # Arrange
        name = "search_tool"
        description = "Search for information"
        tool = TestToolImplementation(name, description)

        # Act
        metadata = tool.get_metadata()

        # Assert
        self.assertEqual(metadata["name"], name)
        self.assertEqual(metadata["description"], description)
        self.assertEqual(metadata["type"], "TestToolImplementation")

    @pytest.mark.asyncio
    async def test_execute_method(self):
        """Test that the execute method works correctly."""
        # Arrange
        tool = TestToolImplementation()
        params = {"query": "test query", "limit": 10}

        # Act
        result = await tool.execute(**params)

        # Assert
        self.assertTrue(tool.execute_called)
        self.assertEqual(tool.execute_params, params)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Test execution successful")
        self.assertEqual(result["data"], params)

    def test_validate_params_default(self):
        """Test the default parameter validation."""
        # Arrange
        tool = TestToolImplementation()
        params = {"query": "test"}

        # Act
        result = tool.validate_params(params)

        # Assert
        self.assertTrue(result)


# Tests for error conditions
class TestBaseToolErrorConditions(unittest.TestCase):
    """Test cases for error conditions in the BaseTool class."""

    def test_direct_instantiation_fails(self):
        """Test that BaseTool cannot be instantiated directly."""
        # Act and Assert
        with self.assertRaises(TypeError):
            BaseTool("direct", "Should not work")

    @pytest.mark.asyncio
    async def test_execute_abstract_method(self):
        """Test that the execute method is properly abstract."""

        # Arrange
        class IncompleteToolImplementation(BaseTool):
            """A tool implementation that doesn't override execute."""

            pass

        # Act and Assert
        with self.assertRaises(TypeError):
            IncompleteToolImplementation("incomplete", "Missing execute implementation")

    @pytest.mark.asyncio
    async def test_execute_with_exception(self):
        """Test handling when execute raises an exception."""

        # Arrange
        class ErrorToolImplementation(BaseTool):
            """A tool implementation that raises an exception."""

            async def execute(self, **kwargs):
                raise ValueError("Test exception")

        tool = ErrorToolImplementation("error_tool", "Raises exceptions")

        # Act and Assert
        with self.assertRaises(ValueError):
            await tool.execute(param="value")


# Tests for edge cases
class TestBaseToolEdgeCases(unittest.TestCase):
    """Test cases for edge cases in the BaseTool class."""

    def test_empty_name_description(self):
        """Test initialization with empty name and description."""
        # Arrange and Act
        tool = TestToolImplementation("", "")

        # Assert
        self.assertEqual(tool.name, "")
        self.assertEqual(tool.description, "")

        # Metadata should still work
        metadata = tool.get_metadata()
        self.assertEqual(metadata["name"], "")
        self.assertEqual(metadata["description"], "")

    def test_validate_params_override(self):
        """Test overriding the validate_params method."""

        # Arrange
        class ValidatedToolImplementation(TestToolImplementation):
            """A tool with custom parameter validation."""

            def validate_params(self, params):
                return "required_param" in params

        tool = ValidatedToolImplementation()

        # Act and Assert
        self.assertTrue(tool.validate_params({"required_param": "value"}))
        self.assertFalse(tool.validate_params({"wrong_param": "value"}))

    @pytest.mark.asyncio
    async def test_execute_with_no_params(self):
        """Test execute with no parameters."""
        # Arrange
        tool = TestToolImplementation()

        # Act
        result = await tool.execute()

        # Assert
        self.assertTrue(tool.execute_called)
        self.assertEqual(tool.execute_params, {})
        self.assertEqual(result["data"], {})

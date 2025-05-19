"""Base class for personal assistant tools."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import structlog
from pydantic import BaseModel

from src.tools.base_tool import BaseTool

logger = structlog.get_logger(__name__)


class PersonalAssistantTool(BaseTool, ABC):
    """Base class for all personal assistant tools.

    Extends the main BaseTool class with personal assistant specific functionality.
    """

    def __init__(self, name: str, description: str, config: Optional[Dict[str, Any]] = None):
        """Initialize the tool with optional configuration.

        Args:
            name: Tool name
            description: Tool description
            config: Optional configuration dictionary for the tool
        """
        super().__init__(name, description)
        self.config = config or {}
        self.logger = logger.bind(tool=self.__class__.__name__)
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the tool's connections and authentication.

        This method should be called before using the tool.
        Must be implemented by subclasses.

        Returns:
            bool: True if initialization successful
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up tool resources.

        This method should be called when done using the tool.
        Must be implemented by subclasses.
        """
        pass

    async def __aenter__(self) -> "PersonalAssistantTool":
        """Async context manager entry.

        Returns:
            Self for use in async with statements
        """
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit.

        Ensures cleanup is called when exiting context.
        """
        await self.cleanup()

    def _check_initialized(self) -> None:
        """Check if tool is initialized before use.

        Raises:
            RuntimeError: If tool is not initialized
        """
        if not self._initialized:
            raise RuntimeError(
                f"{self.__class__.__name__} must be initialized before use. "
                "Call initialize() first."
            )


class ToolResponse(BaseModel):
    """Base model for tool responses.

    All tool-specific response models should inherit from this.
    """

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

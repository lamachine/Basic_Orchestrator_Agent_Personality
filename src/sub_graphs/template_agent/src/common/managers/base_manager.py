"""
Base Manager Module

This module implements the base manager class that all managers inherit from.
It provides common functionality for state management, logging, and error handling.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field

from ..config import ServiceCapability, ServiceConfig
from ..config.base_config import BaseConfig
from ..services.state_service import StateService
from ..state.state_models import GraphState, Message, MessageStatus, MessageType

T = TypeVar("T", bound=BaseModel)
S = TypeVar("S", bound=BaseModel)


class ManagerState(BaseModel):
    """Base state model for managers."""

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error_count: int = 0
    success_count: int = 0
    last_update: Optional[datetime] = None


class BaseManager(Generic[T, S]):
    """Base class for all managers.

    Type Parameters:
        T: Configuration type (must inherit from BaseConfig)
        S: State type (must inherit from BaseModel)
    """

    def __init__(self, config: T, state_type: Type[S] = ManagerState):
        """Initialize the base manager.

        Args:
            config: Manager configuration
            state_type: Type of state to use
        """
        self.config = config
        self._state: S = state_type()
        self._initialized = False
        self._setup_logging()

    async def __aenter__(self):
        """Async context manager entry."""
        if not self._initialized:
            await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()

    async def initialize(self) -> None:
        """Initialize the manager.

        This method should be overridden by subclasses to perform any necessary initialization.
        """
        self._initialized = True

    async def cleanup(self) -> None:
        """Clean up resources.

        This method should be overridden by subclasses to perform any necessary cleanup.
        """
        if self._initialized:
            await self.persist_state()
            self._initialized = False

    def _setup_logging(self) -> None:
        """Set up logging for the manager."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    @property
    def is_enabled(self) -> bool:
        """Check if the manager is enabled."""
        return getattr(self.config, "enabled", True)

    @property
    def last_update(self) -> Optional[datetime]:
        """Get the last update timestamp."""
        return self._state.last_update

    @property
    def error_count(self) -> int:
        """Get the error count."""
        return self._state.error_count

    @property
    def success_count(self) -> int:
        """Get the success count."""
        return self._state.success_count

    def update_state(self, message: Message) -> None:
        """Update the state with a new message.

        Args:
            message: Message to add to state
        """
        self._state.last_update = datetime.now()

        if message.status == MessageStatus.ERROR:
            self._state.error_count += 1
        elif message.status == MessageStatus.SUCCESS:
            self._state.success_count += 1

    def get_capability(self, name: str) -> Optional[ServiceCapability]:
        """Get a specific capability by name.

        Args:
            name: Name of the capability

        Returns:
            ServiceCapability if found, None otherwise
        """
        return self.config.get_capability(name)

    def is_capability_enabled(self, name: str) -> bool:
        """Check if a specific capability is enabled.

        Args:
            name: Name of the capability

        Returns:
            True if enabled, False otherwise
        """
        return self.config.is_capability_enabled(name)

    def get_merged_config(self) -> Dict[str, Any]:
        """Get merged configuration from parent and local.

        Returns:
            Merged configuration dictionary
        """
        return self.config.get_merged_config()

    def create_message(
        self,
        content: str,
        message_type: MessageType,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Create a new message.

        Args:
            content: Message content
            message_type: Type of message
            data: Optional data dictionary
            metadata: Optional metadata dictionary

        Returns:
            New Message instance
        """
        return Message(
            type=message_type,
            status=MessageStatus.PENDING,
            content=content,
            data=data or {},
            metadata=metadata or {},
        )

    def create_error_message(
        self, content: str, error_data: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Create an error message.

        Args:
            content: Error message content
            error_data: Optional error data

        Returns:
            New error Message instance
        """
        return Message(
            type=MessageType.ERROR,
            status=MessageStatus.ERROR,
            content=content,
            data=error_data or {},
            metadata={"error_timestamp": datetime.now().isoformat()},
        )

    async def update_state(self, update: Dict[str, Any]) -> None:
        """Update the manager's state.

        Args:
            update: Dictionary of state updates
        """
        for key, value in update.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)
        self._state.updated_at = datetime.now()

    async def get_state(self) -> S:
        """Get the current state.

        Returns:
            Current state
        """
        return self._state

    async def persist_state(self) -> None:
        """Persist the current state to storage.

        This method should be overridden by subclasses to implement persistence.
        """
        pass

    async def load_state(self) -> None:
        """Load state from storage.

        This method should be overridden by subclasses to implement state loading.
        """
        pass

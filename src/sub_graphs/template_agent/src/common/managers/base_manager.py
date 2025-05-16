"""
Base Manager Module

This module implements the base manager class that all managers inherit from.
It provides common functionality for state management, logging, and error handling.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import logging
from pathlib import Path

from ..config.logging_config import get_log_level
from ..services.state_service import StateService
from .state_models import GraphState, Message, MessageType, MessageStatus
from .service_models import ServiceConfig, ServiceCapability

class ManagerState(BaseModel):
    """Base state model for managers."""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseManager:
    """Base class for all managers."""
    
    def __init__(self, config: ServiceConfig):
        """Initialize the base manager.
        
        Args:
            config: Service configuration
        """
        self.config = config
        self.state = GraphState()
        self._last_update = datetime.now()
        self._error_count = 0
        self._success_count = 0
        self.state_service = None
        self._setup_logging(get_log_level(), None)
        self._initialized = False
        
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
        
    def _setup_logging(self, log_level: int, log_file: Optional[Path]) -> None:
        """Set up logging for the manager."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Add file handler if log_file is provided
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
    @property
    def is_enabled(self) -> bool:
        """Check if the manager is enabled."""
        return self.config.enabled

    @property
    def last_update(self) -> datetime:
        """Get the last update timestamp."""
        return self._last_update

    @property
    def error_count(self) -> int:
        """Get the error count."""
        return self._error_count

    @property
    def success_count(self) -> int:
        """Get the success count."""
        return self._success_count

    def update_state(self, message: Message) -> None:
        """Update the state with a new message.
        
        Args:
            message: Message to add to state
        """
        self.state.messages.append(message)
        self._last_update = datetime.now()
        
        if message.status == MessageStatus.ERROR:
            self._error_count += 1
        elif message.status == MessageStatus.SUCCESS:
            self._success_count += 1

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

    def create_message(self, 
                      content: str, 
                      message_type: MessageType,
                      data: Dict[str, Any] = None,
                      metadata: Dict[str, Any] = None) -> Message:
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
            metadata=metadata or {}
        )

    def create_error_message(self, 
                           content: str,
                           error_data: Dict[str, Any] = None) -> Message:
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
            metadata={"error_timestamp": datetime.now().isoformat()}
        )
        
    async def update_state(self, update: Dict[str, Any]) -> None:
        """
        Update the manager's state.
        
        Args:
            update: Dictionary of state updates
        """
        for key, value in update.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
        self.state.updated_at = datetime.now()
        
    async def get_state(self) -> GraphState:
        """
        Get the current state.
        
        Returns:
            Current state
        """
        return self.state
        
    async def persist_state(self) -> None:
        """
        Persist the current state to storage.
        
        If state_service is provided, saves state using the service.
        Otherwise, does nothing.
        """
        if self.state_service:
            try:
                await self.state_service.save_state(
                    manager_name=self.__class__.__name__,
                    state=self.state
                )
            except Exception as e:
                self.logger.error(f"Error persisting state: {e}")
        
    async def load_state(self) -> None:
        """
        Load state from storage.
        
        If state_service is provided, loads state using the service.
        Otherwise, does nothing.
        """
        if self.state_service:
            try:
                loaded_state = await self.state_service.load_state(
                    manager_name=self.__class__.__name__,
                    state_class=self.state.__class__
                )
                if loaded_state:
                    self.state = loaded_state
            except Exception as e:
                self.logger.error(f"Error loading state: {e}") 
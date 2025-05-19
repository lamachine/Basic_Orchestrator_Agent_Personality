"""
Template Manager Module

This module provides examples and documentation for implementing specialty managers.
It serves as a template for extending or creating new managers.

IMPORTANT: This file contains only examples and documentation.
DO NOT include active code that could override common functionality.
All actual implementations should be in separate files.

Example Patterns:
1. Extending existing managers
2. Creating new managers
3. Overriding base methods
4. Using multiple inheritance
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ...common.managers.base_manager import BaseManager, ManagerState
from ...common.managers.session_manager import SessionManager, SessionState
from ...common.services.state_service import StateService

# Example 1: Extending SessionManager
# ----------------------------------
"""
To extend an existing manager:

1. Create a new state class:
```python
class ExtendedSessionState(SessionState):
    # Add new fields specific to your specialty
    specialty_field: str = "default"
    specialty_count: int = 0
    last_specialty_action: Optional[datetime] = None
    specialty_metadata: Dict[str, Any] = Field(default_factory=dict)
```

2. Create a new manager class:
```python
class ExtendedSessionManager(SessionManager):
    def __init__(self,
                 session_service: Any,
                 state: Optional[ExtendedSessionState] = None,
                 log_level: Optional[int] = None,
                 log_file: Optional[Path] = None,
                 state_service: Optional[StateService] = None):
        super().__init__(
            session_service=session_service,
            state=state or ExtendedSessionState(),
            log_level=log_level,
            log_file=log_file,
            state_service=state_service
        )

    async def specialty_action(self, action: str) -> None:
        # Implement specialty functionality
        pass
```
"""


class ExtendedSessionState(SessionState):
    """
    Extended session state with additional fields.

    This shows how to add new state fields to an existing manager.
    """

    # Add new fields specific to your specialty
    specialty_field: str = "default"
    specialty_count: int = 0
    last_specialty_action: Optional[datetime] = None
    specialty_metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtendedSessionManager(SessionManager):
    """
    Extended session manager with additional functionality.

    This shows how to add new methods to an existing manager.
    """

    def __init__(
        self,
        session_service: Any,  # Replace with actual service type
        state: Optional[ExtendedSessionState] = None,
        log_level: Optional[int] = None,
        log_file: Optional[Path] = None,
        state_service: Optional[StateService] = None,
    ):
        """
        Initialize the extended session manager.

        Args:
            session_service: Session service instance
            state: Optional initial state
            log_level: Optional logging level override
            log_file: Optional log file path
            state_service: Optional state service for persistence
        """
        super().__init__(
            session_service=session_service,
            state=state or ExtendedSessionState(),
            log_level=log_level,
            log_file=log_file,
            state_service=state_service,
        )

    async def specialty_action(self, action: str) -> None:
        """
        Example of a new specialty method.

        Args:
            action: Action to perform
        """
        try:
            # Update specialty state
            self.state.specialty_count += 1
            self.state.last_specialty_action = datetime.now()
            self.state.specialty_field = action

            # Call parent method if needed
            # await super().some_parent_method()

            # Persist state
            await self.persist_state()

        except Exception as e:
            self.logger.error(f"Error performing specialty action: {e}")
            raise RuntimeError(f"Failed to perform specialty action: {e}")

    async def get_specialty_stats(self) -> Dict[str, Any]:
        """
        Get specialty statistics.

        Returns:
            Dictionary of specialty statistics
        """
        return {
            "specialty_count": self.state.specialty_count,
            "last_action": self.state.last_specialty_action,
            "specialty_field": self.state.specialty_field,
            "metadata": self.state.specialty_metadata,
        }


# Example 2: Creating a New Manager
# -------------------------------
"""
To create a new manager:

1. Define your state:
```python
class CustomState(ManagerState):
    custom_id: Optional[str] = None
    custom_name: str = "default"
    custom_data: Dict[str, Any] = Field(default_factory=dict)
    custom_timestamp: Optional[datetime] = None
    custom_count: int = 0
```

2. Create your manager:
```python
class CustomManager(BaseManager):
    def __init__(self,
                 custom_service: Any,
                 state: Optional[CustomState] = None,
                 log_level: Optional[int] = None,
                 log_file: Optional[Path] = None,
                 state_service: Optional[StateService] = None):
        super().__init__(
            state=state or CustomState(),
            log_level=log_level,
            log_file=log_file,
            state_service=state_service
        )
        self.custom_service = custom_service
```
"""


class CustomState(ManagerState):
    """
    Custom state for a new manager.

    This shows how to create a completely new state model.
    """

    # Define your state fields
    custom_id: Optional[str] = None
    custom_name: str = "default"
    custom_data: Dict[str, Any] = Field(default_factory=dict)
    custom_timestamp: Optional[datetime] = None
    custom_count: int = 0


class CustomManager(BaseManager):
    """
    Custom manager implementation.

    This shows how to create a completely new manager.
    """

    def __init__(
        self,
        custom_service: Any,  # Replace with actual service type
        state: Optional[CustomState] = None,
        log_level: Optional[int] = None,
        log_file: Optional[Path] = None,
        state_service: Optional[StateService] = None,
    ):
        """
        Initialize the custom manager.

        Args:
            custom_service: Custom service instance
            state: Optional initial state
            log_level: Optional logging level override
            log_file: Optional log file path
            state_service: Optional state service for persistence
        """
        super().__init__(
            state=state or CustomState(),
            log_level=log_level,
            log_file=log_file,
            state_service=state_service,
        )
        self.custom_service = custom_service

    async def custom_method(self, param: str) -> Dict[str, Any]:
        """
        Example of a custom method.

        Args:
            param: Parameter for the method

        Returns:
            Result of the operation

        Raises:
            RuntimeError: If operation fails
        """
        try:
            # Update state
            self.state.custom_count += 1
            self.state.custom_timestamp = datetime.now()
            self.state.custom_name = param

            # Perform custom operation
            result = await self.custom_service.do_something(param)

            # Update state with result
            self.state.custom_data.update(result)

            # Persist state
            await self.persist_state()

            return result

        except Exception as e:
            self.logger.error(f"Error in custom method: {e}")
            raise RuntimeError(f"Failed to perform custom operation: {e}")

    async def get_custom_info(self) -> Dict[str, Any]:
        """
        Get custom information.

        Returns:
            Dictionary of custom information
        """
        return {
            "id": self.state.custom_id,
            "name": self.state.custom_name,
            "count": self.state.custom_count,
            "timestamp": self.state.custom_timestamp,
            "data": self.state.custom_data,
        }


# Example 3: Overriding Base Methods
# --------------------------------
"""
To override base methods:

```python
class OverrideManager(BaseManager):
    async def persist_state(self) -> None:
        # Implement custom persistence
        pass

    async def load_state(self) -> None:
        # Implement custom loading
        pass
```
"""


class OverrideManager(BaseManager):
    """
    Example of overriding base manager methods.

    This shows how to completely override base functionality.
    """

    async def persist_state(self) -> None:
        """
        Override persist_state with custom implementation.

        This shows how to completely replace base functionality.
        """
        try:
            # Your custom persistence logic here
            # For example, using a different storage mechanism
            pass

        except Exception as e:
            self.logger.error(f"Error in custom persistence: {e}")
            raise RuntimeError(f"Failed to persist state: {e}")

    async def load_state(self) -> None:
        """
        Override load_state with custom implementation.

        This shows how to completely replace base functionality.
        """
        try:
            # Your custom loading logic here
            # For example, loading from a different source
            pass

        except Exception as e:
            self.logger.error(f"Error in custom loading: {e}")
            raise RuntimeError(f"Failed to load state: {e}")


# Example 4: Using Multiple Inheritance
# ----------------------------------
"""
To use multiple inheritance:

```python
class MultiState(ManagerState):
    # Combine fields from different state types
    pass

class MultiManager(BaseManager, SessionManager):
    # Combine functionality from multiple managers
    pass
```
"""


class MultiState(ManagerState):
    """State that combines multiple state types."""

    # Combine fields from different state types
    pass


class MultiManager(BaseManager, SessionManager):
    """
    Example of multiple inheritance.

    This shows how to combine functionality from multiple managers.
    """

    pass


# Best Practices
# -------------
"""
1. Always maintain state consistency
2. Implement proper error handling
3. Document any custom methods and fields
4. Test manager functionality thoroughly
5. Keep specialty logic separate from common functionality
6. Use Pydantic models for state validation
7. Implement proper logging
8. Handle state persistence appropriately

Example Error Handling:
```python
try:
    # Your code here
    pass
except Exception as e:
    self.logger.error(f"Error in operation: {e}")
    raise RuntimeError(f"Failed to perform operation: {e}")
```

Example State Management:
```python
# Update state
self.state.some_field = new_value
self.state.updated_at = datetime.now()

# Persist state
await self.persist_state()
```

Example Logging:
```python
self.logger.debug("Detailed information")
self.logger.info("General information")
self.logger.warning("Warning message")
self.logger.error("Error message")
```
"""

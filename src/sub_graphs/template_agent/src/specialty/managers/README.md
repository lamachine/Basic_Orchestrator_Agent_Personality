"""
Specialty Manager Implementation

This directory is for implementing specialty managers that extend or override the base template manager functionality.

## Structure

- `session_manager.py`: Example implementation showing how to extend the base session manager
- `message_manager.py`: Example implementation showing how to extend the base message manager
- `state_manager.py`: Example implementation showing how to extend the base state manager

## How to Extend the Template Manager

1. Import the base template manager:
```python
from ...common.managers.base_manager import BaseManager
```

2. Create your specialty manager by extending the base:
```python
class SpecialtyManager(BaseManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add specialty initialization
```

## Best Practices

1. Always maintain parent request ID tracking
2. Implement proper error handling and state management
3. Document any custom methods and properties
4. Test manager functionality thoroughly
5. Keep specialty logic separate from common functionality
"""

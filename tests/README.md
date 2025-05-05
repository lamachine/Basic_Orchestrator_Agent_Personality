# Tool Integration Test Suite

This directory contains tests for the tool integration system of the Basic Orchestrator Agent Personality framework. The tests follow a Test-Driven Development (TDD) approach to guide the implementation of the tool integration features.

## Test Organization

The tests are organized according to the implementation checklist in our project plan:

1. **Discovery & Registration Tests**
   - `test_tool_registry.py` - Tests for discovering and registering tools

2. **Standardized Interface Tests**
   - `test_personal_assistant_interface.py` - Tests for the standardized tool interface

3. **Modular Structure Tests**
   - `test_modular_structure.py` - Tests for modular architecture and abstraction

4. **State Management Tests**
   - `test_tool_state_management.py` - Tests for state persistence and conversation history

5. **Task Functionality Tests**
   - `test_personal_assistant_task_list.py` - Tests for the task list implementation

6. **Dynamic Loading Tests**
   - `test_dynamic_tool_loading.py` - Tests for dynamic loading and unloading of tools

7. **Orchestrator Integration Tests**
   - `test_orchestrator_tools.py` - Tests for orchestrator tool integration
   - `test_tool_processor.py` - Tests for tool call processing

## Running Tests

We provide a convenient script to run the tests: `run_tool_tests.py` in the project root. This script allows you to run specific test groups or all tests.

### Basic Usage

Run all tests:
```bash
python run_tool_tests.py
```

Run a specific test group:
```bash
python run_tool_tests.py discovery
```

Run with verbose output:
```bash
python run_tool_tests.py -v
```

Stop on first failure:
```bash
python run_tool_tests.py -x
```

List available test groups:
```bash
python run_tool_tests.py -l
```

### Available Test Groups

- **Individual Test Groups**:
  - `discovery` - Tool discovery and registration tests
  - `interface` - Standardized tool interface tests
  - `modular` - Modular structure and abstraction tests
  - `state` - State management and persistence tests
  - `task` - Task list functionality tests
  - `dynamic` - Dynamic tool loading/unloading tests
  - `orchestrator` - Orchestrator integration tests

- **Combined Test Groups**:
  - `structure` - All structure-related tests (discovery + modular)
  - `functionality` - All functionality tests (interface + task)
  - `integration` - All integration tests (dynamic + state)
  - `existing` - Only existing tests from before our implementation
  - `all` - All test files

## Test Structure

Each test file follows a consistent structure:

1. **Fixtures** - Setup code for the tests, creating mock objects, temporary files, etc.
2. **Tests That Should Pass** - Tests for expected behavior with valid inputs
3. **Tests That Should Fail** - Tests that validate error handling with invalid inputs
4. **Edge Cases** - Tests for boundary conditions and unusual scenarios

Each test is designed to be independent and isolated from others. Tests use temporary files and directories when testing file operations to avoid interfering with the actual project state.

## Adding New Tests

When adding new tests, follow these guidelines:

1. **Name your test file** according to what it's testing: `test_<feature>.py`
2. **Follow the standard structure** with fixtures, passing tests, failing tests, and edge cases
3. **Include docstrings** that explain what each test is validating
4. **Use pytest markers** appropriately (`@pytest.mark.asyncio` for async tests)
5. **Update `run_tool_tests.py`** to include your new test file in the appropriate test group

Example test template:
```python
"""
Tests for <feature>.

These tests validate <description of what's being tested>.
"""

import pytest
# Import other necessary modules

# Test fixtures
@pytest.fixture
def fixture_name():
    """Description of what this fixture provides."""
    # Setup code
    yield # The test resource
    # Cleanup code

# Tests that should pass
def test_expected_behavior():
    """Test that <feature> works as expected with valid inputs."""
    # Arrange
    # Act
    # Assert

# Tests that should fail
def test_failure_case():
    """Test that <feature> handles invalid inputs appropriately."""
    # Arrange
    # Act & Assert failure
    with pytest.raises(SomeException):
        # Code that should raise exception

# Edge cases
def test_edge_case():
    """Test <feature> with boundary conditions."""
    # Arrange
    # Act
    # Assert

if __name__ == "__main__":
    pytest.main(["-v", __file__])
```

## Debugging Tests

The tests include debug print statements to help troubleshoot failures:

- Look for `print(f"DEBUG: ...")` statements in the code
- Run tests with `-v` for more detailed output
- Use pytest's `-xvs` flags for verbose output and to see print statements:
  ```bash
  python -m pytest tests/test_file.py -xvs
  ```

## Test Dependencies

The tests use these libraries:
- pytest - The main testing framework
- pytest-asyncio - For testing async functions
- pydantic - For data validation models 
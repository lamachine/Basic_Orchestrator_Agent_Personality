# UI Module

This directory contains the user interface implementations for the orchestrator system.

## Overview

The UI module provides a flexible interface system that separates the core agent functionality from the presentation and interaction layers. This allows the orchestrator to be used with different interfaces (CLI, API, web, etc.) without changing the core logic.

## Structure

- `interface.py`: Abstract base class defining the interface contract
- `cli.py`: Command-line interface implementation
- `adapters/`: Low-level I/O adapters for platform independence
  - `io_adapter.py`: Input/output adapters for different platforms

## Interface Architecture

The interface system follows these design principles:

1. **Separation of Concerns**: The agent logic is completely separated from user interaction
2. **Interface Contract**: All interfaces implement the same `UserInterface` abstract base class
3. **Pluggable Design**: New interfaces can be added without modifying the agent code
4. **Platform Independence**: I/O operations are abstracted to work consistently across platforms

## UserInterface

The abstract `UserInterface` class defines the contract that all interface implementations must follow:

- `start()`: Initialize and start the interface
- `stop()`: Gracefully shut down the interface
- `display_message(message)`: Show a message to the user
- `display_error(error)`: Show an error message
- `get_user_input()`: Retrieve input from the user
- `process_agent_response(response)`: Handle and display an agent's response
- `display_tool_result(result)`: Show the result of a tool execution
- `process_user_command(command)`: Handle special user commands (e.g., 'exit')

## CLI Interface

The `CLIInterface` implementation provides a command-line interface with these features:

- Non-blocking input for checking tool completions while waiting for user input
- Handling of special commands like 'exit' and 'rename'
- Cross-platform support (Windows/Unix/MacOS)
- Terminal formatting for better readability

## I/O Adapters

The I/O adapters abstract platform-specific details:

- `InputAdapter`: Base class for input handling
  - `WindowsInputAdapter`: Windows-specific implementation
  - `UnixInputAdapter`: Unix/Linux/MacOS implementation
- `OutputAdapter`: Platform-independent output operations

## Adding a New Interface

To add a new interface:

1. Create a new class that extends `UserInterface`
2. Implement all required methods
3. Register the interface in `main.py`
4. Create a specific launcher (e.g., `run_web.py`)

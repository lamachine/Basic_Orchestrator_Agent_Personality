# Basic Orchestrator Agent

A modular orchestrator system for LLM agents with tool support.

## Overview

This project implements a flexible orchestrator that allows LLMs to use tools and manage conversations. The system follows a modular architecture that separates agent intelligence, user interfaces, and tool implementations.

## Features

- **LLM Integration**: Connect to local LLMs through Ollama API
- **Tool Support**: Extensible tool system with asynchronous execution
- **Conversation Management**: Persistent conversation history and context
- **Multiple Interfaces**: Support for CLI, API, and web interfaces
- **Platform Independence**: Works consistently across different operating systems

## Project Structure

The project is organized into a modular structure:

- `src/`: Source code
  - `agents/`: Agent implementations
    - `base_agent.py`: Common agent functionality
    - `llm_query_agent.py`: Core LLM orchestration agent
    - `orchestrator_tools.py`: Tool handling utilities
  - `config/`: Configuration files and settings
  - `services/`: Service implementations
    - `db_services/`: Database services
    - `llm_services/`: LLM API services
    - `logging_services/`: Logging utilities
  - `tools/`: Tool implementations
    - `tool_processor.py`: Tool response processing utilities
    - `tool_registry.py`: Registry of available tools
  - `ui/`: User interface implementations
    - `interface.py`: Interface abstract base class
    - `cli.py`: Command-line interface
    - `adapters/`: I/O adapters for platform independence
  - `main.py`: Main entry point
  - `run_cli.py`: CLI-specific launcher
- `tests/`: Test files
  - `test_llm_query_agent.py`: Tests for LLMQueryAgent
  - `test_tool_processor.py`: Tests for tool processing
  - `test_cli_interface.py`: Tests for CLI interface
  - `test_io_adapter.py`: Tests for I/O adapters

## Architecture

The system follows a modular architecture with clear separation of concerns:

1. **Agents**: Core intelligence that coordinates LLM interactions and tool usage
2. **Tools**: External capabilities that agents can invoke
3. **Services**: Shared infrastructure like database and logging
4. **UI**: User interfaces for interacting with the system

### Interfaces

The system supports multiple interface types through the abstract `UserInterface` class:

- `CLIInterface`: Command-line interface with non-blocking input
- (Planned) `APIInterface`: RESTful API server
- (Planned) `WebInterface`: Web-based UI
- (Planned) `GraphInterface`: Integration with sub-graphs

## Setup

### Prerequisites

- Python 3.10 or later
- Ollama running locally (or accessible via API)
- PostgreSQL database (optional, for persistence)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/Basic_Orchestrator_Agent_Personality.git
   cd Basic_Orchestrator_Agent_Personality
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the system:
   - Copy `.env.example` to `.env`
   - Update settings in `.env` for your environment

## Running the System

You can run the system in different ways:

```bash
# Using the main entry point with CLI interface (default)
python src/main.py

# Explicitly using the CLI interface
python src/run_cli.py

# With debug logging enabled
python src/run_cli.py --debug

# Continue an existing session
python src/run_cli.py --session SESSION_ID
```

## Development

### Testing

Run the tests with:

```bash
python -m unittest discover tests
```

### Adding a New Tool

1. Create a new function to implement the tool
2. Register the tool in the tool registry
3. Add appropriate documentation and tests

### Adding a New Interface

1. Create a new class that extends `UserInterface`
2. Implement all required methods
3. Update `main.py` to include the new interface option
4. Create a specific launcher file

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Thanks to the Ollama team for the local LLM runtime
- Inspired by various agent frameworks in the LLM ecosystem 
# Basic Orchestrator Agent: Project Plan

## Project Overview

The Basic Orchestrator Agent is a modular system for LLM agents with tool support. It provides a flexible architecture that separates agent intelligence, user interfaces, and tool implementations. The system is designed to be extensible, maintainable, and follow clean code principles.

## Architecture

The project follows a modular architecture with clear separation of concerns:

1. **Agents**: Core intelligence that coordinates LLM interactions and tool usage
2. **Tools**: External capabilities that agents can invoke
3. **Services**: Shared infrastructure like database and logging
4. **UI**: User interfaces for interacting with the system
5. **State Management**: Handling application state and persistence
6. **Graphs**: LangGraph workflow definitions

### Core Components

#### Agents
- `BaseAgent`: Foundation class for all agents
- `OrchestratorAgent`: Central coordinator for the agent ecosystem
  - Simplified process_message method
  - Streamlined tool handling with async execution
  - Personality injection capability
  - Improved conversation state management
  - Enhanced logging with [PROMPT_CHAIN] prefixes
- `LLMQueryAgent`: Core LLM orchestration agent
- `PersonalityAgent`: Injects personality into agent responses

#### Services
- `LLMService`: Interface to LLM providers (Ollama)
- `DBService`: Database operations and persistence
  - Consistent environment variable handling
  - Standardized CRUD operations
  - Robust error handling
- `LoggingService`: Centralized logging system
- `SessionService`: Session management
- `MessageService`: Message handling and persistence
  - Fixed add_message implementation
  - Aligned with MessageState usage
  - Verified database integration
  - Confirmed error handling

#### Managers
- `SessionManager`: Handles user sessions
- `DBManager`: Coordinates database operations
  - Core functionality verified across versions
  - Standardized environment variables
  - Consistent error handling
- `StateManager`: Manages application state

#### Tools
- `ToolRegistry`: Registry of available tools
  - Simplified tool registration system
  - Removed approval system
  - Streamlined tool discovery
  - Added state persistence
  - Basic tool execution support
- `ToolProcessor`: Tool response processing utilities
- Various tool implementations

#### UI
- `BaseUserInterface`: Abstract interface class
- `CLIInterface`: Command-line interface
  - Improved display handler
  - Better message formatting
  - Enhanced user experience
- (Planned) `APIInterface`: RESTful API
- (Planned) `WebInterface`: Web UI

#### State
- `MessageState`: Represents conversation state
- `GraphState`: LangGraph state management

## Code Style and Conventions

### Python Guidelines
- Use Python 3.10 or later
- Follow PEP 8 style guide
- Type hints for all function parameters and return values
- Docstrings in Google style format
- Black for code formatting

### Naming Conventions
- Classes: CamelCase (e.g., `BaseAgent`)
- Functions/Methods: snake_case (e.g., `process_message`)
- Variables: snake_case (e.g., `user_input`)
- Constants: UPPER_SNAKE_CASE (e.g., `DEFAULT_MODEL`)
- Modules: snake_case (e.g., `tool_registry.py`)

### File Structure
- Module-based organization (e.g., all agent code in `src/agents/`)
- Target length: 200 lines to take advantage of Cursor file reading limit.
- Maximum file length: 500 lines
- One class per file (with exceptions for closely related small classes)
- Clean `__init__.py` files with only docstrings

### Error Handling
- Use try/except blocks with specific exceptions
- Log all errors with appropriate level
- Return meaningful error messages

### Testing
- Unit tests for all components
- Tests follow same structure as main code
- At least 3 test cases per component (success, failure, edge)
- Test Coverage Requirements:
  - Core Components (Agents, Services, Tools): 80% minimum coverage
  - UI Components: 70% minimum coverage
  - Integration Points: 90% minimum coverage
- Test Categories:
  - Unit Tests: Individual component functionality
  - Integration Tests: Component interaction and data flow
  - End-to-End Tests: Complete user workflows
- Test Organization:
  - Mirror src/ directory structure in tests/
  - One test file per module
  - Fixtures in conftest.py for shared test setup
- Test Documentation:
  - Clear test descriptions
  - Arrange/Act/Assert pattern
  - Mock external dependencies
  - Document test data requirements

## Current Priorities

1. Complete the modularization of the codebase
2. Integrate scraper functionality
3. Implement sub-graph support
4. Add personal assistant features
5. Expand tool ecosystem with Google integration
6. Maintain and expand test coverage:
   - Complete message service tests
   - Enhance orchestrator agent tests
   - Add integration tests for tool registry
   - Implement end-to-end workflow tests

## Future Plans

1. Web UI interface
2. Multiple LLM provider support
3. Advanced memory capabilities with mem0
4. Expanded tool ecosystem

## Integration with External Systems

- **Supabase**: Primary database backend
- **Ollama**: Local LLM provider
- **Docker**: Containerization for components
- **Google APIs**: For tasks integration
- **LangGraph**: For agent workflow management
- **Pydantic**: For data validation and communication

## Development Workflow

1. Create plans and break down to checklist tasks
2. Create comprehensive tests first
3. Implement functionality
4. Document code and features
5. Update project status
6. Review and refactor

## Graph Communication Paradigm

All communications between graphs will come down through tools, and be handled by one of the following interfaces:
- `sub_graph_interface.py`: Uses message passing for graph-to-graph communication (default for initial development)
- `api_interface.py`: Handles web-based interactions (e.g., MCP)
- `cli_interface.py`: Enables direct terminal-based interface for stand-alone tool/graph deployment

Initial development will use the sub_graph paradigm with message passing, leveraging all existing orchestrator infrastructure.

# Tool Integration System

This document explains the tool integration with the graph orchestration system.

## Overview

The tool integration system allows the orchestrator to use specialized tools for different tasks. Each tool provides a specific functionality, and the orchestrator can route requests to the appropriate tool based on the user's needs.

## Architecture

The system has three main components:

1. **Tool Implementations**: Individual tools that perform specific tasks
2. **Tool Utilities**: Common functions for working with tools and the state system
3. **Graph Integration**: Functions that connect tools with the graph orchestration system

## Tools

We've implemented three mock tools:

- **valet_tool**: For managing household staff, schedule, and personal affairs
- **personal_assistant_tool**: For handling emails, messages, and to-do lists
- **librarian_tool**: For research, documentation, and knowledge management

Each tool returns structured data with a consistent format:

```python
{
    "status": "success",
    "message": "Human-readable response",
    "data": {
        # Tool-specific data structure
    }
}
```

## State Integration

The tools are integrated with the state management system:

1. Tools receive tasks from the LLM
2. Tool execution is tracked in the state
3. Tool results are stored in the conversation history
4. The LLM can use tool results in subsequent responses

## Key Files

- `src/tools/valet.py`, `src/tools/personal_assistant.py`, `src/tools/librarian.py`: Individual tool implementations
- `src/tools/tool_registry.py`: Registry of available tools with descriptions
- `src/tools/tool_utils.py`: Common utility functions for working with tools
- `src/tools/graph_integration.py`: Functions for integrating tools with the graph system
- `src/graphs/orchestrator_example.py`: Example orchestrator graph that uses tools

## Using Tools in the Graph

The tools are integrated into the graph using the following pattern:

1. The LLM node processes user input and decides whether to use a tool
2. If a tool is needed, the LLM generates a tool call
3. The router function detects the tool call and routes to the appropriate tool node
4. The tool node executes the tool and updates the state
5. Control returns to the LLM node with the updated state, including tool results

## Testing

The tool integration has comprehensive tests:

- Tests for the orchestrator tools integration
- Tests for the tool utility functions
- Tests for the graph integration

Each set of tests includes tests for expected use cases, edge cases, and failure scenarios.

## Future Enhancements

1. Implement real tool functionality instead of mock responses
2. Add more sophisticated routing based on natural language understanding
3. Support chaining multiple tools for complex tasks
4. Add automatic tool selection based on task analysis 


# Tools Module

This directory contains the tool processing system for the orchestrator.

## Overview

The tools module provides utilities for handling tool requests and responses, enabling the agent to use external tools and process their results consistently. These utilities abstract the complexity of different tool response formats and provide a unified interface for the agent.

## Structure

- `tool_processor.py`: Core tool processing utilities
- `initialize_tools.py`: Tool initialization and dependency setup
- `tool_registry.py`: Registry and metadata for available tools

## Tool Processing

The tool processing system handles:

1. **Tool Request Formatting**: Preparing requests for tools in a consistent format
2. **Response Processing**: Parsing and normalizing responses from different tools
3. **Result Formatting**: Formatting tool results for display and LLM context

### Key Components

#### `process_completed_tool_request`

This function extracts the result message from a completed tool request, handling various response structures and providing fallbacks for unusual formats.

```python
result = process_completed_tool_request(tool_request)
print(f"Tool result: {result}")
```

#### `format_tool_result_for_llm`

Formats a tool result specifically for inclusion in an LLM prompt, making it easy for the model to understand and use the tool's output.

```python
formatted_result = format_tool_result_for_llm(tool_result)
prompt = f"User query: {query}\n\n{formatted_result}\n\nPlease respond based on this information."
```

#### `normalize_tool_response`

Converts different response formats (strings, dictionaries, etc.) into a standardized structure with consistent fields.

```python
normalized = normalize_tool_response(raw_response)
status = normalized["status"]
message = normalized["message"]
```

#### `extract_tool_calls_from_text`

Identifies tool call requests within LLM-generated text, using a regex pattern to extract the tool name and parameters.

```python
tool_calls = extract_tool_calls_from_text(llm_response)
for call in tool_calls:
    execute_tool(call["name"], call["task"])
```

## Adding a New Tool

To add a new tool:

1. Create a function that performs the tool's operation
2. Register the tool in the tool registry with its metadata
3. Ensure the tool returns responses in a format compatible with the processing utilities

## Error Handling

The tool processing system is designed to handle:

- **Missing fields**: Using fallback values when expected fields are absent
- **Different formats**: Converting various response formats to a standard structure
- **Nested data**: Extracting relevant information from complex nested structures
- **Timeouts**: Managing long-running tool executions that exceed time limits 
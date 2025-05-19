# Agents Module

This directory contains the agent implementations for the orchestrator system.

## Overview

The agents module provides the core intelligence of the system, handling LLM interactions, conversation management, and tool orchestration. The agents act as mediators between users, external tools, and language models.

## Structure

- `base_agent.py`: Base agent class with common functionality
- `llm_query_agent.py`: Core agent for orchestrating LLM interactions
- `orchestrator_tools.py`: Tool handling utilities for agents

## Agent Architecture

The agent architecture follows these design principles:

1. **Decoupling**: Separating core agent logic from UI and tool implementations
2. **Stateful Conversations**: Managing conversation state and history
3. **Tool Orchestration**: Coordinating asynchronous tool executions
4. **LLM Integration**: Handling communication with language models

## LLMQueryAgent

The `LLMQueryAgent` is the central agent responsible for:

- **Conversation Management**: Creating, continuing, and tracking conversations
- **LLM Interaction**: Sending queries to the LLM and processing responses
- **Tool Handling**: Detecting and executing tool calls in LLM responses
- **Context Management**: Maintaining conversation context for better responses

### Key Methods

#### Conversation Management

These methods have been moved to the DatabaseManager class:

- `start_conversation(user_id, title)`: Begin a new conversation
- `continue_conversation(session_id, user_id)`: Resume an existing conversation
- `list_conversations(user_id)`: Retrieve user conversations
- `rename_conversation(session_id, new_title)`: Update a conversation's title
- `delete_conversation(session_id)`: Delete a conversation and its messages

#### LLM Interaction

- `generate_prompt(user_input)`: Construct a prompt for the LLM
- `query_llm(prompt)`: Send a query to the LLM and get a response
- `get_conversation_context()`: Retrieve context from previous messages

#### Tool Processing

- `process_llm_response(response_text, user_input)`: Process LLM output for tool calls
- `handle_tool_completion(request_id, original_query)`: Process completed tool requests
- `check_pending_tools()`: Check for any tools that have completed execution

## BaseAgent

The `BaseAgent` class provides foundational capabilities for all agents:

- **Basic Configuration**: API endpoints, model settings, etc.
- **Database Connection**: Interface to the persistence layer
- **Logging**: Consistent logging across all agents

## Adding a New Agent

To add a new agent:

1. Extend the `BaseAgent` class
2. Implement the required interface methods
3. Register the agent with any necessary services
4. Connect the agent to the appropriate UI components

## Error Handling

The agent system includes robust error handling for:

- **LLM API Failures**: Retrying and degrading gracefully
- **Tool Execution Errors**: Capturing and reporting issues
- **Database Problems**: Maintaining operation with limited persistence
- **Conversation State Errors**: Recovering from invalid state transitions

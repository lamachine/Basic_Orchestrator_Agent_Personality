# Database Architecture

This document describes the database architecture of the Basic Orchestrator Agent Personality system. The database layer is organized into three main components:

1. **DatabaseService**: A stateless service layer that handles low-level database operations.
2. **Component Managers**: Specialized database managers for specific domain objects.
3. **DatabaseManager**: A high-level manager that coordinates between component managers.

## Architecture Overview

```
┌────────────────────┐
│   Client Modules   │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  DatabaseManager   │
└─────────┬──────────┘
          │
          ▼
┌─────────┴──────────┐
│  Component Managers │
│                     │
│ ┌─────────────────┐ │
│ │MessageManagerDB │ │
│ └─────────────────┘ │
│ ┌─────────────────┐ │
│ │ConversationMgrDB│ │
│ └─────────────────┘ │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  DatabaseService   │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│     Database       │
└────────────────────┘
```

## Component Responsibilities

### DatabaseService

The `DatabaseService` class is a stateless service that provides:

- Low-level database operations (insert, select, update, delete)
- No business logic or state management
- Direct interface to the database (Supabase)
- Error handling and logging for database operations

Key characteristics:
- Stateless: maintains no internal state
- Single responsibility: database access operations
- No decision-making logic

### Component Managers

Component managers are specialized managers for specific domain objects:

1. **MessageManagerDB**: Handles operations related to messages
   - Adding, retrieving, searching, and deleting messages
   - Message-specific business logic

2. **ConversationManagerDB**: Handles operations related to conversations
   - Creating, retrieving, updating, and deleting conversations
   - Conversation-specific business logic

Key characteristics:
- Domain-specific logic and operations
- Access database only through the DatabaseService
- Lightweight business logic appropriate to their domain

### DatabaseManager

The `DatabaseManager` class is a high-level manager that:

- Provides a unified API for database operations
- Coordinates between component managers
- Handles cross-cutting concerns
- Type conversion and parameter normalization

Key characteristics:
- Composition of specialized managers
- Unified API for client modules
- String/integer ID conversion
- Cross-component operations (e.g., deleting a conversation and its messages)

## Usage Patterns

### Direct Database Operations

For simple database operations, client modules can use the `DatabaseManager` directly:

```python
# Create a new conversation
conversation_id = db_manager.create_conversation(user_id="user123", name="Project Planning")

# Add a message to the conversation
db_manager.add_message(
    session_id=conversation_id,
    role="user",
    content="Let's discuss the project timeline",
    metadata={"timestamp": datetime.now().isoformat()}
)
```

### Cross-Component Operations

The `DatabaseManager` handles operations that span multiple components:

```python
# Delete a conversation and all its messages
db_manager.delete_conversation(conversation_id="12345")
```

## Design Principles

The database architecture follows these key principles:

1. **Separation of Concerns**: Each component has a clear, single responsibility
2. **Composition Over Inheritance**: Using composition to build complex functionality
3. **Statelessness**: Service layer is stateless for better scalability
4. **Error Handling**: Comprehensive error handling at each layer
5. **Type Safety**: Consistent handling of parameter types (string/int conversions)

## Future Enhancements

Potential enhancements to this architecture include:

1. Adding transaction support for multi-step operations
2. Implementing caching for frequently accessed data
3. Supporting asynchronous database operations
4. Adding more specialized component managers for other domain objects

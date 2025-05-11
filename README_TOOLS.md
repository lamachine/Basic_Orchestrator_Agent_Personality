# Tool Integration System

This document explains the tool integration system for the Basic Orchestrator Agent Personality framework.

## Overview

The tool integration system allows the orchestrator to use specialized tools for different tasks. Each tool provides specific functionality, and the orchestrator routes requests to the appropriate tool based on the user's needs.

Tools are implemented as modular, self-contained sub-agents that follow a standardized structure. The system is designed to make tools easily discoverable, loadable, and configurable without modifying the orchestrator code.

## Architecture Principles

The system follows these key principles:

1. **Modularity**: Each tool is a self-contained module that can be added/removed without changing the orchestrator
2. **Standardized Structure**: All tools follow the same directory structure and interface patterns
3. **Hierarchical Processing**: Tools can contain sub-tools, creating a hierarchical agent structure
4. **Clean Abstraction**: Each layer is only aware of the layer directly below it
5. **Consistent Communication**: All components use standardized message formats

## System Components

The system has these main components:

1. **Tool Registry**: Discovers, validates, and loads tools
   - Dynamic tool discovery
   - Configuration validation
   - State persistence
   - Tool approval management

2. **Tool Interface**: Standardized communication between orchestrator and tools
   - Message passing protocol
   - Request tracking system
   - State management
   - Error handling

3. **Tool Implementation**: Individual tool functionality
   - Core business logic
   - Sub-tool management
   - State persistence
   - Error recovery

4. **State Management**: Handles tool state and persistence
   - Request tracking
   - Message history
   - Tool state persistence
   - Session management

5. **Communication Layer**: Manages inter-tool communication
   - Message routing
   - Request/response handling
   - Error propagation
   - State synchronization

## Tool Discovery and Loading

When the program starts:
1. The orchestrator runs to the point of functional communications
2. It scans the `src/sub_graphs` folder for tool agents
3. It checks each discovered tool against the list of approved agents
4. If not approved, it prompts the user to approve the agent
5. For approved tools, it loads the tool configuration and validates it
6. Valid tools are registered in the tool registry
7. Invalid tools trigger an error log and the system continues

## Standard File Structure

Each tool follows this standardized structure:

```
/<name>_agent/
    .env                    # Environment variables
    requirements.txt        # Dependencies
    README.md              # Tool documentation
    LICENSE                # License information
    .gitignore            # Git ignore rules
    
    /logs                  # Log files
    /tests                 # Test files
        test_<toolname>.py # Tool-specific tests
        conftest.py        # Shared test fixtures
    
    <toolname>_tool.py     # Pydantic model for parent graph
    
    /src
        /agents            # Business logic
            <toolname>_agent.py
            base_agent.py  # Base agent class
        
        /config            # Configuration files
            tool_config.yaml    # Tool registry info
            graph_config.py     # Graph-specific settings
            llm_config.py       # LLM configuration
            db_config.py        # Database configuration
        
        /db               # Database models and operations
            models.py
            operations.py
        
        /graphs           # LangGraph workflow definitions
            <toolname>_graph.py
        
        /managers         # State and session management
            state_manager.py
            session_manager.py
        
        /services         # Core services
            llm_service.py
            message_service.py
            db_service.py
        
        /state           # State models and persistence
            state_models.py
            state_manager.py
        
        /sub_graphs      # Sub-tools this tool may use
            /<subtool>_agent/
                # (Same structure as parent)
        
        /tools           # Tool implementations
            <toolname>_tool.py
            tool_utils.py
        
        /ui              # Connection points
            sub_graph_interface.py
            cli_interface.py
        
        /utils           # Utility functions
            logging_utils.py
            error_utils.py
        
        main.py          # Entry point
```

## Tool Registry System

The Tool Registry provides a simple, file-based system for discovering, loading, and managing tools.  Each level of graph will handle its own tools with it's own registry, keeping the levels cleanly separated and preventing overwhelming any one agent or level of the stack.

### Tool Configuration

Each tool requires a YAML configuration file (`tool_config.yaml`):

```yaml
name: personal_assistant
description: Handles emails, messages, and to-do lists
version: "0.1.0"

# Tool-specific configuration
config:
  default_email: "user@example.com"
  max_retries: 3
  timeout_seconds: 30

# Required capabilities
capabilities:
  - email
  - calendar
  - tasks

# Additional metadata
metadata:
  author: "Basic Orchestrator"
  created: "2024-05-01"
```

### Persistence

- Tool configurations and approvals are persisted in `src/data/tool_registry`
- Uses simple JSON storage for tool states
- Only persists necessary information (configs and metadata)
- Tools themselves are dynamically imported when needed

## Tool Installation Process

Tools are installed by adding their entire folder structure to the appropriate sub_graphs directory. The system supports hierarchical tool installation, allowing each graph to manage its own set of tools.

### Installation Levels

1. **Orchestrator Level Tools**
   - Location: `orchestrator/src/sub_graphs/`
   - Example: `personal_assistant_agent/`
   - These tools are directly available to the orchestrator
   - Installation: Copy the entire tool folder into the orchestrator's sub_graphs directory
   ```bash
   # Example: Installing personal_assistant_agent
   cp -r personal_assistant_agent/ orchestrator/src/sub_graphs/
   ```

2. **Sub-Graph Level Tools**
   - Location: `orchestrator/src/sub_graphs/<parent_tool>/src/sub_graphs/`
   - Example: `orchestrator/src/sub_graphs/personal_assistant_agent/src/sub_graphs/google_suite_email_agent/`
   - These tools are available to their parent tool
   - Installation: Copy the entire tool folder into the parent tool's sub_graphs directory
   ```bash
   # Example: Installing google_suite_email_agent into personal_assistant_agent
   cp -r google_suite_email_agent/ orchestrator/src/sub_graphs/personal_assistant_agent/src/sub_graphs/
   ```

### Installation Process

1. **Prepare the Tool**
   - Ensure the tool follows the standard file structure
   - Verify all required files are present
   - Check tool_config.yaml is properly configured

2. **Install the Tool**
   - Copy the entire tool folder to the appropriate sub_graphs directory
   - The tool registry will automatically discover the new tool
   - The system will prompt for tool approval on next startup

3. **Verify Installation**
   - Check the tool appears in the tool registry
   - Verify the tool is properly configured
   - Test basic tool functionality

### Directory Structure Example

```
orchestrator/
└── src/
    └── sub_graphs/
        ├── personal_assistant_agent/
        │   └── src/
        │       └── sub_graphs/
        │           ├── google_suite_email_agent/
        │           ├── calendar_agent/
        │           └── task_agent/
        ├── research_agent/
        │   └── src/
        │       └── sub_graphs/
        │           ├── web_search_agent/
        │           └── document_analysis_agent/
        └── other_tools/
```

### Important Notes

1. **Tool Independence**
   - Each tool is self-contained
   - Tools can be moved between different parent graphs
   - Tools maintain their own configuration and state

2. **Security**
   - Tools must be approved before use
   - Each tool runs in its own context
   - Tools can only access their designated resources

3. **Maintenance**
   - Tools can be updated by replacing their folder
   - Configuration changes require tool restart
   - State is preserved across updates

4. **Troubleshooting**
   - Check tool registry logs for installation issues
   - Verify tool configuration is valid
   - Ensure all dependencies are installed

## Parent Graph Tool Node

Each sub-graph must provide a standardized tool node for its parent graph to use. This node serves as the entry point for all parent graph interactions and ensures consistent communication patterns throughout the system.

### Tool Node Structure

The parent graph tool node is implemented as a Pydantic model in the root of the sub-graph:

```python
# personal_assistant_tool.py
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class PersonalAssistantTool(BaseModel):
    """Tool interface for parent graph to interact with personal assistant."""
    
    name: str = "personal_assistant"
    description: str = "Handles personal tasks, emails, and calendar management"
    version: str = "0.1.0"
    
    # Tool-specific configuration
    config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "default_email": "user@example.com",
            "max_retries": 3,
            "timeout_seconds": 30
        }
    )
    
    # Required capabilities
    capabilities: list[str] = ["email", "calendar", "tasks"]
    
    async def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool request from the parent graph.
        
        Args:
            request: The request from the parent graph containing:
                - request_id: Unique identifier for this request
                - parent_request_id: ID of the parent request
                - action: The action to perform
                - parameters: Tool-specific parameters
                
        Returns:
            Dict containing:
                - request_id: Echo of the request ID
                - parent_request_id: Echo of the parent request ID
                - status: success|partial|failure
                - data: Tool-specific response data
                - metadata: Additional context
        """
        # Implementation specific to personal assistant
        pass
```

### Tool Node Requirements

1. **Standard Interface**
   - Must implement a Pydantic model
   - Must provide name, description, and version
   - Must implement execute() method
   - Must handle request_id and parent_request_id

2. **Configuration**
   - Must support tool-specific configuration
   - Must declare required capabilities
   - Must validate input parameters
   - Must handle errors gracefully

3. **Communication**
   - Must use standardized message format
   - Must maintain request chain tracking
   - Must provide status updates
   - Must handle async operations

4. **Error Handling**
   - Must catch and report errors
   - Must provide meaningful error messages
   - Must support retry strategies
   - Must maintain error context

### Example Usage

```python
# In parent graph
async def handle_user_request(request: Dict[str, Any]):
    # Create tool instance
    tool = PersonalAssistantTool()
    
    # Execute tool
    response = await tool.execute({
        "request_id": "uuid-123",
        "parent_request_id": "uuid-456",
        "action": "send_email",
        "parameters": {
            "to": "user@example.com",
            "subject": "Test Email",
            "body": "Hello from the tool!"
        }
    })
    
    # Handle response
    if response["status"] == "success":
        # Process successful response
        pass
    else:
        # Handle error
        pass
```

### Benefits

1. **Clean Abstraction**
   - Parent graphs only need to know the tool interface
   - Implementation details are hidden
   - Changes to tool internals don't affect parent

2. **Consistent Communication**
   - Standardized message format
   - Predictable error handling
   - Clear status reporting

3. **Easy Integration**
   - Simple to add new tools
   - Clear interface requirements
   - Well-documented patterns

4. **Maintainable Code**
   - Clear separation of concerns
   - Standardized error handling
   - Consistent patterns

## Standard Message Format

Tools use standardized message formats for communication:

```python
{
    "request_id": "uuid",  # Unique identifier for the request chain
    "parent_request_id": "uuid",  # ID of parent request if this is a sub-request
    "status": "success",
    "message": "Human-readable response",
    "data": {
        # Tool-specific data structure
    }
}
```

For specific message types:

- **Tool Status Messages**:
  ```python
  {
      "request_id": "uuid",
      "parent_request_id": "uuid",  # Optional, for sub-requests
      "type": "status",
      "status": "acknowledged|running|completed|error",
      "tool_name": "tool_id",
      "task_id": "unique_task_id",
      "timestamp": "ISO-timestamp",
      "message": "human readable message"
  }
  ```

- **Results/Completion**:
  ```python
  {
      "request_id": "uuid",
      "parent_request_id": "uuid",  # Optional, for sub-requests
      "type": "result",
      "status": "success|partial|failure",
      "data": {},  # Tool-specific result data
      "metadata": {},  # Additional context/metadata
      "next_actions": []  # Suggested follow-up actions
  }
  ```

- **Error Messages**:
  ```python
  {
      "request_id": "uuid",
      "parent_request_id": "uuid",  # Optional, for sub-requests
      "type": "error",
      "error_code": "ERROR_TYPE",
      "message": "human readable error",
      "details": {},  # Detailed error info
      "recoverable": boolean,
      "retry_strategy": "retry_pattern"
  }
  ```

### Request Tracking and Closure

1. **Request ID Generation**:
   - Each new request gets a unique UUID
   - Sub-requests inherit parent_request_id
   - Request IDs are used for tracking and correlation

2. **Request Lifecycle**:
   - Creation: When a new request is initiated
   - Propagation: Through the tool chain
   - Completion: When the request is fulfilled
   - Closure: When all sub-requests are complete

3. **State Management**:
   - Requests are tracked in the state manager
   - Sub-requests are linked to parent requests
   - State is persisted for request recovery
   - Request history is maintained for auditing

4. **Request Closure Rules**:
   - A request is considered complete when:
     - All sub-requests are complete
     - The main task is fulfilled
     - Any cleanup is performed
   - Closure is logged and persisted
   - Parent requests are notified of completion

## Using Tools in the Orchestrator

The tools are integrated into the orchestrator using this pattern:

1. The LLM node processes user input and decides whether to use a tool
2. If a tool is needed, the LLM generates a tool call
3. The router function detects the tool call, assigns it a task id, and routes to the appropriate tool node asynchronously
4. The tool node executes the tool and updates the state
5. Control returns to to the LLM immediately after a tool call.  
6. The central graph node then monitors the task queue for the tool call to complete.  It then updates the state with the results and routes the response to the LLM.

All communications between orchestrator and tools use structured tool calls rather than natural language, ensuring clean separation and reliable communication.

## Tool Hierarchies

Tools can use other tools, creating a hierarchical structure:

- The orchestrator can use the personal_assistant tool
- The personal_assistant tool can use email_agent, task_agent, and calendar_agent tools
- Each level is unaware of implementation details more than one level below

When a user installs a tool like personal_assistant, the orchestrator automatically knows to route all communications, social media, task, and calendar requests to it. If the tool is removed, that capability is no longer available.

## RAG and Message Search Capabilities

The system includes built-in RAG (Retrieval Augmented Generation) capabilities for searching through message history:

1. **Vector Search**
   - Messages are automatically embedded using the LLM service
   - Embeddings are stored in the `embedding_nomic` column
   - Supports semantic search across all messages
   - Respects user-level privacy through filtering

2. **Search Methods**
   ```python
   # Basic text search
   messages = await message_service.search_messages(
       query="search term",
       user_id="user123"
   )
   
   # Semantic search with filters
   messages = await db_service.semantic_message_search(
       query_text="search term",
       embedding=query_embedding,
       user_id="user123",
       match_count=5,
       match_threshold=0.7
   )
   ```

3. **Privacy and Access Control**
   - All searches are filtered by user_id
   - Messages are only accessible to authorized users
   - Line-level security is enforced through user_id filtering

4. **Integration with LLM**
   - LLM can use RAG to find relevant context
   - Supports cross-conversation reference
   - Maintains conversation history for context

### Using RAG in Tools

Tools can leverage RAG capabilities by:
1. Using `message_service.search_messages()` for basic text search
2. Using `db_service.semantic_message_search()` for semantic search
3. Implementing custom search logic using the vector search capabilities

Example tool implementation:
```python
async def search_related_messages(
    query: str,
    user_id: str,
    match_count: int = 5
) -> List[Dict[str, Any]]:
    """
    Search for messages related to the query.
    
    Args:
        query: Search query
        user_id: User ID for privacy filtering
        match_count: Number of matches to return
        
    Returns:
        List of related messages
    """
    # Get query embedding
    embedding = await llm_service.get_embedding(query)
    
    # Perform semantic search
    results = await db_service.semantic_message_search(
        query_text=query,
        embedding=embedding,
        user_id=user_id,
        match_count=match_count
    )
    
    return results
```

## Graph Communication Paradigm

All communications between graphs will come down through tools, and be handled by one of the following interfaces:
- `sub_graph_interface.py`: Uses message passing for graph-to-graph communication (default for initial development)
- `api_interface.py`: Handles web-based interactions (e.g., MCP)
- `cli_interface.py`: Enables direct terminal-based interface for stand-alone tool/graph deployment

Initial development will use the sub_graph paradigm with message passing, leveraging all existing orchestrator infrastructure.

# Orchestrator-Specific Documentation

## What Makes the Orchestrator Unique
1. **Core Functionality**
   - LLM configs: conversation Y, reasoning N, tools Y, encoding Y
   - Database configs: sql Y, vector Y, state N, knowledge_graph N
   - System prompt complexity
   - Tool routing logic

2. **Configuration Requirements**
   - Conversation config/hooks
   - Personality config (if using conversation)
   - LLM configuration options
   - Database configuration options
   - State management options
   - Logging configuration
   - User configuration for line-level security

3. **Configuration Inheritance Options**
   - Use parent configuration
   - Use local configuration
   - Use remote configuration
   - Hybrid approach with fallbacks

## Current Issues
1. Google Authentication Failures
   - [ ] Fix Google auth in personal assistant
   - [ ] Verify auth flow in tool chain
   - [ ] Test auth persistence
   - [ ] Document auth requirements

2. Message Flow Issues
   - [ ] Fix message routing through personal assistant
   - [ ] Verify LLM connection in personal assistant
   - [ ] Test message persistence
   - [ ] Document message flow

3. Tool Integration Issues
   - [ ] Fix dummy email tool integration
   - [ ] Verify tool discovery
   - [ ] Test tool execution
   - [ ] Document tool requirements

# Template-Specific Documentation

## What Every Graph Needs (Generic/Template)
- graph_name: Unique name for the graph/agent (from config)
- system_prompt: Default system prompt (from config)
- llm_config: How to access LLM (parent, local, remote)
- db_config: How to access DB (parent, local, remote)
- state_config: State management (parent, local, stand-alone)
- logging_config: Logging level, file, etc.
- user_config: User/role/line-level security (parent/local)

## Implementation Plan
1. Expand graph_config.py to include all generic config fields (with docstrings)
2. Move orchestrator-specific fields to a subclass or a separate config (if needed)
3. Update the orchestrator's graph file to use the new config structure
4. Do the same for personal_assistant and other agents

## File Review Checklist
- In master (orchestrator), is the code "as simple as possible, but no simpler?"
- In master, is the code zen?
- In master, is there graph-function specific code (i.e. orchestrator_only) that could be moved to another file to make a cleaner master template?
- After satisfactory review, create a clean template file for template_agent
- In personal_assistant_agent, is there graph-function specific code (i.e. personal_assistant_only) that could be moved to another file to make a cleaner match to the template?
- Update to proper file names and reference names for the personal_assistant_agent (variable name?)

# Rapid Development Path

### Phase 0: Quick Start Tools and Templates
1. [ ] Create Basic Template
   - [ ] Extract minimal working template from orchestrator
   - [ ] Create template_agent with basic structure
   - [ ] Document template usage and customization
   - [ ] Add example tool implementation

2. [ ] Implement First Test Tool
   - [ ] Create simple email tool for personal_assistant
   - [ ] Implement basic message passing
   - [ ] Add minimal error handling
   - [ ] Test basic functionality

3. [ ] Document Known Risks
   - [ ] List potential core changes that would affect tools
   - [ ] Document workarounds for current limitations
   - [ ] Create migration guide for future updates
   - [ ] Add version compatibility notes

### Known Risks and Limitations
1. **Core Changes That May Affect Tools**
   - Request ID system changes
   - Message format updates
   - Configuration inheritance modifications
   - State management changes
   - LLM integration updates

2. **Current Workarounds**
   - Use simple UUID for request tracking
   - Implement basic message validation
   - Use local configuration only
   - Minimal state persistence
   - Basic error handling

3. **Future Migration Needs**
   - Update request ID handling
   - Migrate to new message formats
   - Implement configuration inheritance
   - Enhance state management
   - Add advanced error handling

# Implementation Planning and Checklist

## Critical Design Decisions and Discussions

### 1. Request ID and Message Flow (CRITICAL)
- [ ] Design request ID inheritance system
  - [ ] Review current UUID implementation
  - [ ] Evaluate options for additional IDs (metadata vs separate tracking)
  - [ ] Design parent/child request relationship
  - [ ] Document request chain tracking approach
  - [ ] Related to: File Review I.A, Message Format V.A

### 2. Message Format Standardization (CRITICAL)
- [ ] Define message format requirements
  - [ ] CLI to JSON format transition
  - [ ] Message validation rules
  - [ ] Error handling standards
  - [ ] Status reporting format
  - [ ] Related to: Message Format V, Documentation Updates VII

### 3. Configuration Inheritance (CRITICAL)
- [ ] Define configuration inheritance strategy
  - [ ] LLM config inheritance (parent/local/remote)
  - [ ] DB config inheritance (parent/local/remote)
  - [ ] State management (parent/local/standalone)
  - [ ] User config inheritance for line-level security
  - [ ] Logging config inheritance
  - [ ] Related to: File Review I.B, Configuration Updates VII

### 4. RAG Implementation (CRITICAL)
- [ ] Design RAG integration
  - [ ] Search method implementation
  - [ ] Privacy controls
  - [ ] Cross-conversation reference handling
  - [ ] Related to: RAG Awareness II.B

### 5. LLM Integration and Selection (IMPORTANT)
- [ ] Design LLM selection and configuration system
  - [ ] Graph-level vs global selection
  - [ ] Task-specific LLM support
  - [ ] Configuration inheritance rules
  - [ ] LLM evaluation for request closure
  - [ ] Related to: LLM Integration VI, Technical Debt VIII.E

### 6. Multi-Personality System (DEFERRED)
- [ ] Design personality system
  - [ ] Personality configuration structure
  - [ ] Switching mechanism
  - [ ] State management per personality
  - [ ] Documentation requirements
  - [ ] Related to: Deferred Items I

## Implementation Paths

### Path A: Rapid Development (After Critical Decisions)
1. [ ] Create Basic Template
   - [ ] Extract minimal working template from orchestrator
   - [ ] Create template_agent with basic structure
   - [ ] Document template usage and customization
   - [ ] Add example tool implementation

2. [ ] Implement First Test Tool
   - [ ] Create simple email tool for personal_assistant
   - [ ] Implement basic message passing
   - [ ] Add minimal error handling
   - [ ] Test basic functionality

3. [ ] Document Known Risks
   - [ ] List potential core changes that would affect tools
   - [ ] Document workarounds for current limitations
   - [ ] Create migration guide for future updates
   - [ ] Add version compatibility notes

### Known Risks and Limitations
1. **Core Changes That May Affect Tools**
   - Request ID system changes
   - Message format updates
   - Configuration inheritance modifications
   - State management changes
   - LLM integration updates

2. **Current Workarounds**
   - Use simple UUID for request tracking
   - Implement basic message validation
   - Use local configuration only
   - Minimal state persistence
   - Basic error handling

3. **Future Migration Needs**
   - Update request ID handling
   - Migrate to new message formats
   - Implement configuration inheritance
   - Enhance state management
   - Add advanced error handling

### Path B: Full Implementation
1. [ ] Request ID System
   - [ ] Implement UUID handling
   - [ ] Add parent request tracking
   - [ ] Update state management
   - [ ] Add to database schema

2. [ ] Message Format Implementation
   - [ ] Implement JSON message format
   - [ ] Add CLI compatibility layer
   - [ ] Update documentation
   - [ ] Add validation

3. [ ] RAG Integration
   - [ ] Add search methods to base agent
   - [ ] Update system prompts
   - [ ] Add examples
   - [ ] Test functionality

4. [ ] Configuration System
   - [ ] Implement inheritance system
   - [ ] Add configuration validation
   - [ ] Update documentation
   - [ ] Test inheritance

5. [ ] State Management
   - [ ] Implement state persistence
   - [ ] Add request tracking
   - [ ] Update documentation
   - [ ] Test state handling

6. [ ] LLM Selection System
   - [ ] Add LLM configuration
   - [ ] Implement selection logic
   - [ ] Add switching capability
   - [ ] Update documentation

7. [ ] Multi-Personality System
   - [ ] Implement personality configuration
   - [ ] Add switching capability
   - [ ] Update state management
   - [ ] Add documentation

8. [ ] Advanced Features
   - [ ] Add advanced error handling
   - [ ] Implement retry strategies
   - [ ] Add monitoring
   - [ ] Update documentation

9. [ ] Testing
   - [ ] Add unit tests
   - [ ] Add integration tests
   - [ ] Add performance tests
   - [ ] Update test documentation

10. [ ] Documentation
    - [ ] Update API documentation
    - [ ] Add usage examples
    - [ ] Update configuration guide
    - [ ] Add troubleshooting guide

11. [ ] Maintenance and Optimization
    - [ ] Code Review
    - [ ] Review message passing code
    - [ ] Check request ID handling
    - [ ] Verify error handling
    - [ ] Update tests

    - [ ] Performance Optimization
    - [ ] Profile critical paths
    - [ ] Optimize message handling
    - [ ] Improve state management
    - [ ] Update documentation

    - [ ] Security Review
    - [ ] Review authentication
    - [ ] Check authorization
    - [ ] Verify privacy controls
    - [ ] Update security docs



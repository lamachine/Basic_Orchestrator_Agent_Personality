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






# Implementation Planning and Checklist

## I. Critical Discussion and Decisions
These must be discussed and answered before any code is written. They are the foundation of the project and establish our task order.

### A. Request ID and Message Flow (CRITICAL)
    1. Questions and concerns
        a. [ ] How to handle request ID inheritance across multiple levels?
        b. [ ] How to maintain context through async operations?
        c. [ ] How to track parent-child relationships?
        - [ ] Design request ID inheritance system
        - [ ] Review current UUID implementation
        - [ ] Evaluate options for additional IDs (metadata vs separate tracking)
        - [ ] Design parent/child request relationship
        - [ ] Document request chain tracking approach
        - [ ] Related to: File Review I.A, Message Format V.A

    2. Decisions
        a. Implement "Request Context" pattern for distributed systems
        b. Use UUID for request IDs
        c. Store parent-child relationships in metadata

    3. Benefits:
        a.  Clean separation of concerns
        b.  Easy to track request flow
        c.  Maintains context through async operations
        d.  Simple to implement and understand
        e.  Follows standard patterns used in distributed systems

    4. Key Advantages:
    - [x] Each level only needs to know about its own request_id
    - [x] Parent-child relationships are preserved in metadata
    - [x] Easy to trace request flow through logs
    - [x] Works well with async operations
    - [x] Maintains context through the entire request lifecycle

    5. Implementation Notes:
    - [x] Core functionality required before rapid deployment
    - [x] Will be implemented in base graph functionality
    - [x] Complexity: Medium
    - [x] Risk: Low
    - [x] Time Estimate: 2-3 days

    6. Related to: File Review I.A, Message Format V.A

### B. Message Format Standardization (CRITICAL)
    1. Questions and concerns
    - [ ] How to standardize messages between CLI and LLM?
    - [ ] How to handle validation and error reporting?
    - [ ] How to maintain backward compatibility?

    - [ ] Define message format requirements
    - [ ] CLI to JSON format transition
    - [ ] Message validation rules
    - [ ] Error handling standards
    - [ ] Status reporting format
    - [ ] Related to: Message Format V, Documentation Updates VII

    2. Decisions
    - [x] Define message format requirements
        - [x] CLI to JSON format transition
        - [x] Message validation rules
        - [x] Error handling standards
        - [x] Status reporting format
        - [x] Related to: Message Format V, Documentation Updates VII

    3. Benefits:
    - [x] Consistent message handling across all components
    - [x] Clear validation rules
    - [x] Standardized error handling
    - [x] Predictable status reporting

    4. Key Advantages:
    - [x] Single source of truth for message structure
    - [x] Easy to validate and process messages
    - [x] Clear error handling patterns
    - [x] Consistent status updates

    5. Implementation Notes:
    - [x] Will be implemented in base interface
    - [x] Required for all new tools
    - [x] Complexity: Medium
    - [x] Risk: Low
    - [x] Time Estimate: 2-3 days

    6. Related to: Message Format V, Documentation Updates VII

    7. Implementation Tasks:
        a. Core Message Format Implementation
            - [ ] Update src/ui/base_interface.py with new MessageFormat class
            - [ ] Add message validation methods
            - [ ] Add error handling methods
            - [ ] Add status reporting methods
            - [ ] Add message type enums

        b. Interface Updates
            - [ ] Update src/ui/cli/interface.py
            - [ ] Update src/ui/cli/display.py
            - [ ] Update src/ui/cli/commands.py
            - [ ] Update src/ui/cli/tool_handler.py
            - [ ] Update src/ui/cli/session_handler.py

        c. Agent Updates
            - [ ] Update src/agents/orchestrator_agent.py
            - [ ] Update src/agents/base_agent.py
            - [ ] Update src/agents/llm_query_agent.py
            - [ ] Update src/agents/personality_agent.py

        d. Tool Updates
            - [ ] Update src/tools/orchestrator_tools.py
            - [ ] Update tool execution flow
            - [ ] Update tool response format
            - [ ] Update error handling

        e. State Management Updates
            - [ ] Update src/state/state_models.py
            - [ ] Update src/state/state_manager.py
            - [ ] Update src/state/state_validator.py
            - [ ] Update src/state/state_errors.py

        f. Service Updates
            - [ ] Update src/services/message_service.py
            - [ ] Update src/services/logging_service.py
            - [ ] Update src/services/llm_service.py

        g. Testing
            - [ ] Add unit tests for MessageFormat
            - [ ] Add integration tests for message flow
            - [ ] Add validation tests
            - [ ] Add error handling tests
            - [ ] Add status reporting tests

        h. Documentation
            - [ ] Update message format documentation
            - [ ] Add validation rules documentation
            - [ ] Add error handling documentation
            - [ ] Add status reporting documentation

    8. Testing and Validation
    - [ ] Test message flow through all components
    - [ ] Verify error handling
    - [ ] Validate status reporting
    - [ ] Check backward compatibility


### C. Services Source Configuration (CRITICAL)
    1. Questions and concerns
    - [ ] How to handle service inheritance?
    - [ ] How to manage service lifecycle?
    - [ ] How to handle remote services?
    - [ ] Define configuration inheritance strategy
  - [ ] LLM config inheritance (parent/local/remote)
  - [ ] DB config inheritance (parent/local/remote)
  - [ ] State management (parent/local/standalone)
  - [ ] User config inheritance for line-level security
  - [ ] Logging config inheritance
  - [ ] Related to: File Review I.B, Configuration Updates VII

    

    2. Decisions
    - [x] Separate service source (LOCAL/REMOTE/PARENT) from service offering (NONE/SERVE)
    - [x] Each graph manages only its own services
    - [x] No awareness of child graphs

    3. Benefits:
    - [x] Clear separation of service source and offering
    - [x] Each graph manages only its own services
    - [x] No awareness of child graphs
    - [x] Simple parent-child relationship

    4. Key Advantages:
    - [x] Clean separation of concerns
    - [x] Flexible service configuration
    - [x] Easy to add new services
    - [x] Clear service lifecycle management

    5. Implementation Notes:
    - [x] Will be implemented in base graph functionality
    - [x] Required for service management
    - [x] Complexity: Medium
    - [x] Risk: Low
    - [x] Time Estimate: 2-3 days

    6. Related to: File Review I.B, Configuration Updates VII


Bob


### D. RAG Implementation (CRITICAL)
    1. Questions and concerns
    - [ ] How to integrate RAG with existing message flow?
    - [ ] How to handle vector storage?
    - [ ] How to manage privacy and access control?
    - [ ] Design RAG integration
    - [ ] Search method implementation
    - [ ] Privacy controls
    - [ ] Cross-conversation reference handling
    - [ ] Related to: RAG Awareness II.B

    2. Decisions
    - [ ] TBD

    3. Benefits:
    - [ ] TBD

    4. Key Advantages:
    - [ ] TBD

    5. Implementation Notes:
    - [ ] TBD

    6. Related to: RAG Awareness II.B

### E. LLM Integration and Selection (IMPORTANT)
    1. Questions and concerns
    - [ ] How to handle multiple LLM providers?
    - [ ] How to manage model selection?
    - [ ] How to handle fallbacks?
    - [ ] Design LLM selection and configuration system
    - [ ] Graph-level vs global selection
    - [ ] Task-specific LLM support
    - [ ] Configuration inheritance rules
    - [ ] LLM evaluation for request closure
    - [ ] Related to: LLM Integration VI, Technical Debt VIII.E

    2. Decisions
    - [ ] TBD

    3. Benefits:
    - [ ] TBD

    4. Key Advantages:
    - [ ] TBD

    5. Implementation Notes:
    - [ ] TBD

    6. Related to: LLM Integration VI, Technical Debt VIII.E

### F. Multi-Personality System (DEFERRED)
    1. Questions and concerns
    - [ ] How to manage personality switching?
    - [ ] How to maintain context across personalities?
    - [ ] How to handle personality-specific tools?

    2. Decisions
    - [ ] DEFERRED

    3. Benefits:
    - [ ] TBD

    4. Key Advantages:
    - [ ] TBD

    5. Implementation Notes:
    - [ ] TBD

    6. Related to: Deferred Items I

### G. Graph Database - Memories Mem0 Server (TBD)

### H. State Management (CRITICAL)
    1. Questions and concerns
    - [ ] How to integrate with existing state management?
    - [ ] How to handle synchronization?
    - [ ] How to manage access control?

    2. Decisions
    - [ ] TBD

    3. Benefits:
    - [ ] TBD

    4. Key Advantages:
    - [ ] TBD

    5. Implementation Notes:
    - [ ] TBD

    6. Related to: State Management III.C


    I Service configuration
        - [ ] Define configuration inheritance strategy
        - [ ] LLM config inheritance (parent/local/remote)
        - [ ] DB config inheritance (parent/local/remote)
        - [ ] State management (parent/local/standalone)
        - [ ] User config inheritance for line-level security
        - [ ] Logging config inheritance
        - [ ] Related to: File Review I.B, Configuration Updates VII

## II. Housekeeping and Foundation Edits
Core features needed for MVP. High risk changes with high return.

### A. [ ] File Review and Cleanup
   - [ ] Review orchestrator_agent.py as template
   - [ ] Clean up legacy files
   - [ ] Update imports and references

### B. [ ] Directory Structure Standardization
   - [ ] Review proper directory structure
   - [ ] Verify file locations
   - [ ] Check for duplicates
   - [ ] Validate imports


### C. Request ID and Message Flow Implementation
    1. [ ] Core Implementation
        ```python
        class RequestContext:
            """Standard request context for tracking request flow."""
            def __init__(self, request_id: str = None, parent_request_id: str = None):
                self.request_id = request_id or str(uuid.uuid4())
                self.parent_request_id = parent_request_id
                self.timestamp = datetime.now()
                self.metadata = {}

            def create_child_context(self) -> 'RequestContext':
                """Create a new context for a child request."""
                return RequestContext(
                    request_id=str(uuid.uuid4()),
                    parent_request_id=self.request_id
                )

            def to_metadata(self) -> Dict[str, Any]:
                """Convert to metadata format for logging."""
                return {
                    "request_id": self.request_id,
                    "parent_request_id": self.parent_request_id,
                    "timestamp": self.timestamp.isoformat(),
                    **self.metadata
                }
        ```

    2. [ ] Message Handling
        ```python
        async def handle_request(request: Dict[str, Any], context: RequestContext) -> Dict[str, Any]:
            # Log incoming request
            await log_message(
                content=request["content"],
                metadata=context.to_metadata(),
                sender="orchestrator",
                target="tool"
            )

            # Create child context for tool
            tool_context = context.create_child_context()
            
            # Pass to tool
            result = await tool.execute(request, tool_context)
            
            # Log response
            await log_message(
                content=result["content"],
                metadata=context.to_metadata(),  # Use original context for response
                sender="tool",
                target="orchestrator"
            )
        ```

    3. [ ] Tool Execution
        ```python
        async def execute_tool(tool_name: str, task: Dict[str, Any], context: RequestContext) -> Dict[str, Any]:
            """Execute a tool using the registry."""
            try:
                # Log request
                await log_and_persist_message(
                    session_state=context.session_state,
                    role=MessageRole.TOOL,
                    content=f"Tool request: {task}",
                    metadata=context.to_metadata(),
                    sender=f"orchestrator.{tool_name}",
                    target=f"{tool_name}.system"
                )

                # Create child context for tool
                tool_context = context.create_child_context()
                
                # Execute tool
                result = await tool.execute(task, tool_context)
                
                # Log response
                await log_and_persist_message(
                    session_state=context.session_state,
                    role=MessageRole.TOOL,
                    content=f"Tool response: {result}",
                    metadata=context.to_metadata(),
                    sender=f"{tool_name}.system",
                    target=f"orchestrator.{tool_name}"
                )
                
                return result
            except Exception as e:
                # Log error with context
                await log_and_persist_message(
                    session_state=context.session_state,
                    role=MessageRole.ERROR,
                    content=str(e),
                    metadata=context.to_metadata(),
                    sender=f"{tool_name}.system",
                    target=f"orchestrator.{tool_name}"
                )
                raise
        ```

### D. RAG Implementation

   - [ ] Add search methods to base agent
   - [ ] Update system prompts
   - [ ] Add examples
   - [ ] Test functionality

### E. Message Format Standardization Implementation
    1. [ ] Core Message Format
    ```python
    class MessageFormat:
        """Standard message format for all system communications."""
        
        @staticmethod
        def create_request(
            method: str,
            params: Dict[str, Any],
            request_id: Optional[str] = None,
            parent_request_id: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create a standardized request message."""
            return {
                "request_id": request_id or str(uuid.uuid4()),
                "parent_request_id": parent_request_id,
                "type": "request",
                "method": method,
                "params": params,
                "timestamp": datetime.now().isoformat()
            }
        
        @staticmethod
        def create_response(
            request_id: str,
            result: Dict[str, Any],
            status: str = "success",
            metadata: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            """Create a standardized response message."""
            return {
                "request_id": request_id,
                "type": "response",
                "status": status,
                "result": result,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            }
        
        @staticmethod
        def create_error(
            request_id: str,
            error_code: str,
            message: str,
            details: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            """Create a standardized error message."""
            return {
                "request_id": request_id,
                "type": "error",
                "status": "error",
                "error": {
                    "code": error_code,
                    "message": message,
                    "details": details or {}
                },
                "timestamp": datetime.now().isoformat()
            }
        
        @staticmethod
        def create_status_update(
            request_id: str,
            status: str,
            progress: Optional[float] = None,
            message: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create a standardized status update message."""
            return {
                "request_id": request_id,
                "type": "status",
                "status": status,
                "progress": progress,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
    ```

### F. Services Source Configuration Implementation
1. [ ] Service Configuration
```python
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class ServiceSource(str, Enum):
    """Source of service implementation."""
    LOCAL = "local"      # Run service locally
    REMOTE = "remote"    # Use remote service
    PARENT = "parent"    # Use parent's service

class ServiceOffering(str, Enum):
    """Whether this graph offers the service to child graphs."""
    NONE = "none"        # Don't offer service
    SERVE = "serve"      # Offer service to children

class ServiceConfig(BaseModel):
    """Base configuration for any service (LLM, DB, Logging, etc)."""
    source: ServiceSource = ServiceSource.LOCAL
    offering: ServiceOffering = ServiceOffering.NONE
    url: Optional[str] = None  # For remote services
    config: Dict[str, Any] = {}  # Service-specific config

class LLMServiceConfig(ServiceConfig):
    """LLM service configuration."""
    model: str = "default"
    temperature: float = 0.7
    max_tokens: int = 2000

class DBServiceConfig(ServiceConfig):
    """Database service configuration."""
    provider: str = "sqlite"
    database: str = "default.db"

class LoggingServiceConfig(ServiceConfig):
    """Logging service configuration."""
    level: str = "INFO"
    format: str = "standard"
```

2. [ ] Service Management
```python
class BaseGraphServices:
    """Base class for graph service management."""
    def __init__(self, config: Dict[str, ServiceConfig], parent_services: Optional['BaseGraphServices'] = None):
        self.config = config
        self.parent_services = parent_services
        self._service_instances = {}
        self._offered_services = {}

    async def get_service(self, service_name: str) -> Any:
        """Get service instance based on configuration."""
        if service_name not in self._service_instances:
            service_config = self.config[service_name]
            
            if service_config.source == ServiceSource.PARENT and self.parent_services:
                # Use parent's service
                self._service_instances[service_name] = await self.parent_services.get_service(service_name)
            elif service_config.source == ServiceSource.REMOTE:
                # Create remote connection
                self._service_instances[service_name] = await self._create_remote_service(service_name)
            else:
                # Create local service
                self._service_instances[service_name] = await self._create_local_service(service_name)

            # If this graph offers the service, store it
            if service_config.offering == ServiceOffering.SERVE:
                self._offered_services[service_name] = self._service_instances[service_name]

        return self._service_instances[service_name]

    async def _create_remote_service(self, service_name: str) -> Any:
        """Create connection to remote service."""
        # Implementation depends on service type
        pass

    async def _create_local_service(self, service_name: str) -> Any:
        """Create local service instance."""
        # Implementation depends on service type
        pass

    def get_offered_services(self) -> Dict[str, Any]:
        """Get services this graph offers to children."""
        return self._offered_services
```

3. [ ] Graph Configuration
```python
class GraphConfig(BaseModel):
    """Graph-level configuration with service management."""
    name: str
    services: Dict[str, ServiceConfig] = Field(default_factory=dict)

    def initialize_services(self, parent_services: Optional[BaseGraphServices] = None) -> BaseGraphServices:
        """Initialize service management."""
        return BaseGraphServices(self.services, parent_services)

## III. Early Fast and High Risk Deployment
Minimum functionality with templates. Initial tools with minimal effort.


1. [ ] File Review and Cleanup
   - [ ] Review orchestrator_agent.py as template
   - [ ] Review personal_assistant_agent.py
   - [ ] Clean up legacy files
   - [ ] Update imports and references

### A. Create Basic Template
1. [ ] Extract minimal working template from orchestrator
2. [ ] Create template_agent with basic structure
3. [ ] Document template usage and customization
4. [ ] Add example tool implementation

### B. Create First Tool (Personal Assistant)
1. [ ] Create basic structure
2. [ ] Implement core functionality
3. [ ] Add basic error handling
4. [ ] Test basic operations

### C. Create First Tool for a Tool (Email)
1. [ ] Create email tool structure
2. [ ] Implement basic email operations
3. [ ] Add error handling
4. [ ] Test email functionality

### D. Start Running and Keep Notes on Issues
1. [ ] Set up logging
2. [ ] Create issue tracking
3. [ ] Document workarounds
4. [ ] Plan fixes

## IV. Required Edits
Necessary changes before broad deployment. Medium/high risk changes.

### A. RAG Implementation
1. [ ] Design RAG integration
2. [ ] Implement vector storage
3. [ ] Add search functionality
4. [ ] Test and validate

### B. LLM Integration
1. [ ] Design LLM selection system
2. [ ] Implement provider management
3. [ ] Add fallback handling
4. [ ] Test integration

### C. State Management
1. [ ] Implement state persistence
2. [ ] Add request tracking
3. [ ] Update documentation
4. [ ] Test state handling

## V. Standard Deployment
Create standard deployment template and upgrade existing tools.


1. [ ] File Review and Cleanup
   - [ ] Review orchestrator_agent.py as template
   - [ ] Review personal_assistant_agent.py
   - [ ] Clean up legacy files
   - [ ] Update imports and references

### A. Create Standard Deployment Template
1. [ ] Create deployment template
2. [ ] Document deployment process
3. [ ] Add configuration examples
4. [ ] Create upgrade guide

### B. Upgrade Existing Tools
1. [ ] Upgrade personal assistant
2. [ ] Upgrade email tool
3. [ ] Update documentation
4. [ ] Test compatibility

### C. Update Documentation
1. [ ] Update API documentation
2. [ ] Add usage examples
3. [ ] Update configuration guide
4. [ ] Add troubleshooting guide

## VI. Enhancement Edits
Medium risk changes if critical. Repairs and low risk features.

### A. Advanced Features
1. [ ] Add advanced error handling
2. [ ] Implement retry strategies
3. [ ] Add monitoring
4. [ ] Update documentation

### B. Performance Optimization
1. [ ] Profile critical paths
2. [ ] Optimize message handling
3. [ ] Improve state management
4. [ ] Update documentation

### C. Security Review
1. [ ] Review authentication
2. [ ] Check authorization
3. [ ] Verify privacy controls
4. [ ] Update security docs

## VII. Future Migration Needs
Tasks required for future system updates and improvements.

### A. Request ID System
1. [ ] Update request ID handling in all tools
2. [ ] Migrate to new request context system
3. [ ] Update documentation and examples

### B. Message Format
1. [ ] Migrate all tools to new message formats
2. [ ] Update validation and error handling
3. [ ] Update documentation and examples

### C. Configuration System
1. [ ] Implement configuration inheritance in all tools
2. [ ] Update service management
3. [ ] Update documentation and examples

### D. State Management
1. [ ] Enhance state persistence
2. [ ] Update state tracking
3. [ ] Update documentation and examples

### E. Error Handling
1. [ ] Implement advanced error handling
2. [ ] Add retry strategies
3. [ ] Update documentation and examples

## VIII. Technical Debt
1. [ ] Code Review
   - [ ] Review message passing code
   - [ ] Check request ID handling
   - [ ] Verify error handling
   - [ ] Update tests

2. [ ] Performance Optimization
   - [ ] Profile critical paths
   - [ ] Optimize message handling
   - [ ] Improve state management
   - [ ] Update documentation

3. [ ] Security Review
   - [ ] Review authentication
   - [ ] Check authorization
   - [ ] Verify privacy controls
   - [ ] Update security docs




*** Bob Notes ***
start back at "No, on to the checklist sectin and notes"

[Previous README content remains unchanged through line 266]

---

# Implementation Planning and Checklist

## Critical Design Decisions and Discussions




## Implementation Checklist

### Phase 1: Core Structure and Templates




### Phase 2: Critical Features
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

### Phase 3: Configuration and State
1. [ ] Configuration System
   - [ ] Implement inheritance system
   - [ ] Add configuration validation
   - [ ] Update documentation
   - [ ] Test inheritance

2. [ ] State Management
   - [ ] Implement state persistence
   - [ ] Add request tracking
   - [ ] Update documentation
   - [ ] Test state handling

### Phase 4: Post-Template Features
1. [ ] LLM Selection System
   - [ ] Add LLM configuration
   - [ ] Implement selection logic
   - [ ] Add switching capability
   - [ ] Update documentation

2. [ ] Multi-Personality System
   - [ ] Implement personality configuration
   - [ ] Add switching capability
   - [ ] Update state management
   - [ ] Add documentation

3. [ ] Advanced Features
   - [ ] Add advanced error handling
   - [ ] Implement retry strategies
   - [ ] Add monitoring
   - [ ] Update documentation

### Phase 5: Testing and Documentation
1. [ ] Testing
   - [ ] Add unit tests
   - [ ] Add integration tests
   - [ ] Add performance tests
   - [ ] Update test documentation

2. [ ] Documentation
   - [ ] Update API documentation
   - [ ] Add usage examples
   - [ ] Update configuration guide
   - [ ] Add troubleshooting guide

### Phase 6: Maintenance and Optimization
1. [ ] Code Review
   - [ ] Review message passing code
   - [ ] Check request ID handling
   - [ ] Verify error handling
   - [ ] Update tests

2. [ ] Performance Optimization
   - [ ] Profile critical paths
   - [ ] Optimize message handling
   - [ ] Improve state management
   - [ ] Update documentation

3. [ ] Security Review
   - [ ] Review authentication
   - [ ] Check authorization
   - [ ] Verify privacy controls
   - [ ] Update security docs

[Previous Critical Design Decisions section remains unchanged]
============================
## Rapid Development Path

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

[Previous Implementation Checklist section remains unchanged]

+++++++++++++++++++++++++++++++++

[Previous README content remains unchanged through line 266]

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
[Previous Implementation Checklist section remains unchanged]

============================
### 1. Request ID and Message Flow (CRITICAL) [x]
- [x] Design request ID inheritance system
  - [x] Review current UUID implementation
  - [x] Evaluate options for additional IDs (metadata vs separate tracking)
  - [x] Design parent/child request relationship
  - [x] Document request chain tracking approach
  - [x] Related to: File Review I.A, Message Format V.A

[Previous sections remain unchanged until Implementation Paths]

## Implementation Paths

### Path A: Rapid Development (After Critical Decisions)
1. [ ] Implement Request Context System
   - [ ] Create RequestContext class in src/state/state_models.py
     ```python
     class RequestContext:
         def __init__(self, request_id: str = None, parent_request_id: str = None):
             self.request_id = request_id or str(uuid.uuid4())
             self.parent_request_id = parent_request_id
             self.timestamp = datetime.now()
             self.metadata = {}
     ```
   - [ ] Add child context creation method
   - [ ] Add metadata conversion method
   - [ ] Add session state handling

2. [ ] Update Message Logging
   - [ ] Modify log_and_persist_message to use RequestContext
   - [ ] Update message_service.py to handle context metadata
   - [ ] Add context validation in state_models.py
   - [ ] Update database schema if needed

3. [ ] Update Tool Execution Flow
   - [ ] Modify execute_tool in orchestrator_tools.py
   - [ ] Update tool interface to accept RequestContext
   - [ ] Add context handling in tool responses
   - [ ] Update error handling with context

4. [ ] Update Graph Integration
   - [ ] Modify graph nodes to use RequestContext
   - [ ] Update state management for context
   - [ ] Add context validation in graph edges
   - [ ] Update graph documentation

5. [ ] Testing and Validation
   - [ ] Add unit tests for RequestContext
   - [ ] Test context propagation through tools
   - [ ] Verify request chain tracking
   - [ ] Test error handling with context

[Previous sections remain unchanged]

=============================
Let me analyze the current message flow and format handling:
Current Implementation:
The CLI interface (src/ui/cli/interface.py) uses a MessageFormat class from base_interface.py for standardizing messages
Messages are passed through several layers:
CLI Interface → Orchestrator Agent → Tools
Each layer has its own message format handling
Issues Found:
Inconsistent message formats between layers
Some direct string passing instead of structured JSON
Mixed usage of simple dictionaries and MessageFormat objects
Tool responses not fully standardized
Specific Problems:
orchestrator_agent.py sometimes returns simple {"response": message} instead of proper MessageFormat
Tool results are formatted differently from regular messages
CLI display handles multiple message formats
No clear validation of message structure between layers
Difficulty to Fix:
Complexity: Medium
Risk: Low (mostly additive changes)
Effort: Moderate (need to update multiple files)
Here's what we need to do to standardize the message format:

    code block

Implementation Plan:
[ ] Update base_interface.py with new MessageFormat class
[ ] Modify CLI interface to use MessageFormat consistently
[ ] Update orchestrator agent to use MessageFormat
[ ] Standardize tool response format
[ ] Add message validation between layers
[ ] Update display handlers for consistent formatting

============================

After analyzing the codebase, I can see that we have several validation and error handling mechanisms in place, but they're not consistently applied across all message flows. Here's what we have and what we need to add:
Existing Validation:
StateValidator class for task transitions and message sequences
Message Pydantic model with content validation
Basic error handling in MessageFormat
Message persistence validation in log_and_persist_message
Missing Pieces:
No consistent validation between CLI and orchestrator
Inconsistent error format between tools and main system
No standardized status reporting
No validation of message format at boundaries
Proposed Solution:
We should implement a comprehensive message handling system that includes:

    code block

Implementation Plan:
[ ] Update base_interface.py with new MessageFormat class
[ ] Add message validation at system boundaries
[ ] Standardize error handling across all components
[ ] Implement consistent status reporting
[ ] Add validation tests for all message types
Benefits:
Consistent message format throughout the system
Better error tracking and debugging
Improved status reporting
Easier to implement new interfaces
Better validation at system boundaries

============================

### 2. Message Format Standardization (CRITICAL) [x]
- [x] Define message format requirements
  - [x] CLI to JSON format transition
  - [x] Message validation rules
  - [x] Error handling standards
  - [x] Status reporting format
  - [x] Related to: Message Format V, Documentation Updates VII

[Previous sections remain unchanged until Implementation Paths]

### Path A: Rapid Development (After Critical Decisions)
1. [ ] Implement Message Format Standardization
   - [ ] Core Message Format Implementation
     - [ ] Update src/ui/base_interface.py with new MessageFormat class
     - [ ] Add message validation methods
     - [ ] Add error handling methods
     - [ ] Add status reporting methods
     - [ ] Add message type enums

   - [ ] Interface Updates
     - [ ] Update src/ui/cli/interface.py
     - [ ] Update src/ui/cli/display.py
     - [ ] Update src/ui/cli/commands.py
     - [ ] Update src/ui/cli/tool_handler.py
     - [ ] Update src/ui/cli/session_handler.py

   - [ ] Agent Updates
     - [ ] Update src/agents/orchestrator_agent.py
     - [ ] Update src/agents/base_agent.py
     - [ ] Update src/agents/llm_query_agent.py
     - [ ] Update src/agents/personality_agent.py

   - [ ] Tool Updates
     - [ ] Update src/tools/orchestrator_tools.py
     - [ ] Update tool execution flow
     - [ ] Update tool response format
     - [ ] Update error handling

   - [ ] State Management Updates
     - [ ] Update src/state/state_models.py
     - [ ] Update src/state/state_manager.py
     - [ ] Update src/state/state_validator.py
     - [ ] Update src/state/state_errors.py

   - [ ] Service Updates
     - [ ] Update src/services/message_service.py
     - [ ] Update src/services/logging_service.py
     - [ ] Update src/services/llm_service.py

   - [ ] Testing
     - [ ] Add unit tests for MessageFormat
     - [ ] Add integration tests for message flow
     - [ ] Add validation tests
     - [ ] Add error handling tests
     - [ ] Add status reporting tests

   - [ ] Documentation
     - [ ] Update message format documentation
     - [ ] Add validation rules documentation
     - [ ] Add error handling documentation
     - [ ] Add status reporting documentation

2. [ ] Testing and Validation
   - [ ] Test message flow through all components
   - [ ] Verify error handling
   - [ ] Validate status reporting
   - [ ] Check backward compatibility

[Previous sections remain unchanged]

============================

I noticed you did some example code for each of your solutions but it does not appear to be saved in the readme_tools document.  Do you need these?  
------------
class RequestContext:
    """Standard request context for tracking request flow."""
    def __init__(self, request_id: str = None, parent_request_id: str = None):
        self.request_id = request_id or str(uuid.uuid4())
        self.parent_request_id = parent_request_id
        self.timestamp = datetime.now()
        self.metadata = {}

    def create_child_context(self) -> 'RequestContext':
        """Create a new context for a child request."""
        return RequestContext(
            request_id=str(uuid.uuid4()),
            parent_request_id=self.request_id
        )

    def to_metadata(self) -> Dict[str, Any]:
        """Convert to metadata format for logging."""
        return {
            "request_id": self.request_id,
            "parent_request_id": self.parent_request_id,
            "timestamp": self.timestamp.isoformat(),
            **self.metadata
        }
-----------------
async def handle_request(request: Dict[str, Any], context: RequestContext) -> Dict[str, Any]:
    # Log incoming request
    await log_message(
        content=request["content"],
        metadata=context.to_metadata(),
        sender="orchestrator",
        target="tool"
    )

    # Create child context for tool
    tool_context = context.create_child_context()
    
    # Pass to tool
    result = await tool.execute(request, tool_context)
    
    # Log response
    await log_message(
        content=result["content"],
        metadata=context.to_metadata(),  # Use original context for response
        sender="tool",
        target="orchestrator"
    )
---------------------
# In orchestrator_tools.py
async def execute_tool(tool_name: str, task: Dict[str, Any], context: RequestContext) -> Dict[str, Any]:
    """Execute a tool using the registry."""
    try:
        # Log request
        await log_and_persist_message(
            session_state=context.session_state,
            role=MessageRole.TOOL,
            content=f"Tool request: {task}",
            metadata=context.to_metadata(),
            sender=f"orchestrator.{tool_name}",
            target=f"{tool_name}.system"
        )

        # Create child context for tool
        tool_context = context.create_child_context()
        
        # Execute tool
        result = await tool.execute(task, tool_context)
        
        # Log response
        await log_and_persist_message(
            session_state=context.session_state,
            role=MessageRole.TOOL,
            content=f"Tool response: {result}",
            metadata=context.to_metadata(),
            sender=f"{tool_name}.system",
            target=f"orchestrator.{tool_name}"
        )
        
        return result
    except Exception as e:
        # Log error with context
        await log_and_persist_message(
            session_state=context.session_state,
            role=MessageRole.ERROR,
            content=str(e),
            metadata=context.to_metadata(),
            sender=f"{tool_name}.system",
            target=f"orchestrator.{tool_name}"
        )
        raise
---------------------
class MessageFormat:
    """Standard message format for all system communications."""
    
    @staticmethod
    def create_request(
        method: str,
        params: Dict[str, Any],
        request_id: Optional[str] = None,
        parent_request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        return {
            "request_id": request_id or str(uuid.uuid4()),
            "parent_request_id": parent_request_id,
            "type": "request",
            "method": method,
            "params": params,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def create_response(
        request_id: str,
        result: Dict[str, Any],
        status: str = "success",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return {
            "request_id": request_id,
            "type": "response",
            "status": status,
            "result": result,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
--------------------
class MessageFormat:
    """Standard message format for all system communications."""
    
    @staticmethod
    def create_request(
        method: str,
        params: Dict[str, Any],
        request_id: Optional[str] = None,
        parent_request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a standardized request message."""
        return {
            "request_id": request_id or str(uuid.uuid4()),
            "parent_request_id": parent_request_id,
            "type": "request",
            "method": method,
            "params": params,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def create_response(
        request_id: str,
        result: Dict[str, Any],
        status: str = "success",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a standardized response message."""
        return {
            "request_id": request_id,
            "type": "response",
            "status": status,
            "result": result,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def create_error(
        request_id: str,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a standardized error message."""
        return {
            "request_id": request_id,
            "type": "error",
            "status": "error",
            "error": {
                "code": error_code,
                "message": message,
                "details": details or {}
            },
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def create_status_update(
        request_id: str,
        status: str,
        progress: Optional[float] = None,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a standardized status update message."""
        return {
            "request_id": request_id,
            "type": "status",
            "status": status,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }

### Path A: Rapid Development (After Critical Decisions)
1. [ ] Implement Message Format Standardization
   - [ ] Core Message Format Implementation
     - [ ] Update src/ui/base_interface.py with new MessageFormat class:
     ```python
     class MessageFormat:
         """Standard message format for all system communications."""
         
         @staticmethod
         def create_request(
             method: str,
             params: Dict[str, Any],
             request_id: Optional[str] = None,
             parent_request_id: Optional[str] = None
         ) -> Dict[str, Any]:
             """Create a standardized request message."""
             return {
                 "request_id": request_id or str(uuid.uuid4()),
                 "parent_request_id": parent_request_id,
                 "type": "request",
                 "method": method,
                 "params": params,
                 "timestamp": datetime.now().isoformat()
             }
         
         @staticmethod
         def create_response(
             request_id: str,
             result: Dict[str, Any],
             status: str = "success",
             metadata: Optional[Dict[str, Any]] = None
         ) -> Dict[str, Any]:
             """Create a standardized response message."""
             return {
                 "request_id": request_id,
                 "type": "response",
                 "status": status,
                 "result": result,
                 "metadata": metadata or {},
                 "timestamp": datetime.now().isoformat()
             }
         
         @staticmethod
         def create_error(
             request_id: str,
             error_code: str,
             message: str,
             details: Optional[Dict[str, Any]] = None
         ) -> Dict[str, Any]:
             """Create a standardized error message."""
             return {
                 "request_id": request_id,
                 "type": "error",
                 "status": "error",
                 "error": {
                     "code": error_code,
                     "message": message,
                     "details": details or {}
                 },
                 "timestamp": datetime.now().isoformat()
             }
         
         @staticmethod
         def create_status_update(
             request_id: str,
             status: str,
             progress: Optional[float] = None,
             message: Optional[str] = None
         ) -> Dict[str, Any]:
             """Create a standardized status update message."""
             return {
                 "request_id": request_id,
                 "type": "status",
                 "status": status,
                 "progress": progress,
                 "message": message,
                 "timestamp": datetime.now().isoformat()
             }
     ```

     - [ ] Add RequestContext class for tracking request flow:
     ```python
     class RequestContext:
         """Standard request context for tracking request flow."""
         def __init__(self, request_id: str = None, parent_request_id: str = None):
             self.request_id = request_id or str(uuid.uuid4())
             self.parent_request_id = parent_request_id
             self.timestamp = datetime.now()
             self.metadata = {}

         def create_child_context(self) -> 'RequestContext':
             """Create a new context for a child request."""
             return RequestContext(
                 request_id=str(uuid.uuid4()),
                 parent_request_id=self.request_id
             )

         def to_metadata(self) -> Dict[str, Any]:
             """Convert to metadata format for logging."""
             return {
                 "request_id": self.request_id,
                 "parent_request_id": self.parent_request_id,
                 "timestamp": self.timestamp.isoformat(),
                 **self.metadata
             }
     ```

     - [ ] Add request handling example:
     ```python
     async def handle_request(request: Dict[str, Any], context: RequestContext) -> Dict[str, Any]:
         # Log incoming request
         await log_message(
             content=request["content"],
             metadata=context.to_metadata(),
             sender="orchestrator",
             target="tool"
         )

         # Create child context for tool
         tool_context = context.create_child_context()
         
         # Pass to tool
         result = await tool.execute(request, tool_context)
         
         # Log response
         await log_message(
             content=result["content"],
             metadata=context.to_metadata(),  # Use original context for response
             sender="tool",
             target="orchestrator"
         )
     ```

     - [ ] Add tool execution example:
     ```python
     # In orchestrator_tools.py
     async def execute_tool(tool_name: str, task: Dict[str, Any], context: RequestContext) -> Dict[str, Any]:
         """Execute a tool using the registry."""
         try:
             # Log request
             await log_and_persist_message(
                 session_state=context.session_state,
                 role=MessageRole.TOOL,
                 content=f"Tool request: {task}",
                 metadata=context.to_metadata(),
                 sender=f"orchestrator.{tool_name}",
                 target=f"{tool_name}.system"
             )

             # Create child context for tool
             tool_context = context.create_child_context()
             
             # Execute tool
             result = await tool.execute(task, tool_context)
             
             # Log response
             await log_and_persist_message(
                 session_state=context.session_state,
                 role=MessageRole.TOOL,
                 content=f"Tool response: {result}",
                 metadata=context.to_metadata(),
                 sender=f"{tool_name}.system",
                 target=f"orchestrator.{tool_name}"
             )
             
             return result
         except Exception as e:
             # Log error with context
             await log_and_persist_message(
                 session_state=context.session_state,
                 role=MessageRole.ERROR,
                 content=str(e),
                 metadata=context.to_metadata(),
                 sender=f"{tool_name}.system",
                 target=f"orchestrator.{tool_name}"
             )
             raise
     ```

[Previous sections remain unchanged]

============================

Your assessment is spot-on. The key insight about "serve or subscribe" is particularly valuable - it helps avoid unnecessary message passing overhead while maintaining flexibility. Let me analyze this and propose a solution.
First, let me search for any existing configuration handling in the codebase:
Based on the codebase search and your insights, I agree with your assessment. Let me propose a solution that builds on your "serve or subscribe" concept:
Service Mode Configuration
We should add a service_mode field to each service configuration that can be:
local: Run the service locally
remote: Use a remote service (via URL/API)
parent: Subscribe to parent's service
serve: Serve this service to child graphs
Implementation Location
The code should live in src/config/service_config.py and be used by graph_config.py. Here's a proposed implementation:

    code block
============================

You make an excellent point. You're right that we should separate the service source (local/remote/parent) from the service offering (serve) as they are indeed different concerns. Let me revise the approach to make it cleaner and more aligned with the graph hierarchy principles.
I've revised the configuration inheritance approach to:
Separate service source (LOCAL/REMOTE/PARENT) from service offering (NONE/SERVE)
Make it a base graph feature through BaseGraphServices
Keep each graph focused only on its own services and parent relationship
Use a dictionary-based service configuration for flexibility
Key improvements:
Each graph only needs to know about its parent's services, not its children
Service source and offering are independent decisions
Services are managed at the graph level through BaseGraphServices
Clear separation of concerns between service configuration and service management
The code now lives in the base graph functionality, making it available to all graphs while maintaining clean separation of concerns. 

============================

## Critical Design Decisions and Discussions

### 1. Request ID and Message Flow (CRITICAL) [x]
- [x] Design request ID inheritance system
  - [x] Decision: Implement "Request Context" pattern for distributed systems
  - [x] Benefits:
    - Clean separation of concerns
    - Easy to track request flow
    - Maintains context through async operations
    - Simple to implement and understand
    - Follows standard patterns used in distributed systems
  - [x] Key Advantages:
    - Each level only needs to know about its own request_id
    - Parent-child relationships are preserved in metadata
    - Easy to trace request flow through logs
    - Works well with async operations
    - Maintains context through the entire request lifecycle
  - [x] Implementation Notes:
    - Core functionality required before rapid deployment
    - Will be implemented in base graph functionality
    - Complexity: Medium
    - Risk: Low
    - Time Estimate: 2-3 days
  - [x] Related to: File Review I.A, Message Format V.A

### 2. Message Format Standardization (CRITICAL) [x]
- [x] Define message format requirements
  - [x] Decision: Standardize all messages to JSON format with consistent structure
  - [x] Benefits:
    - Consistent message handling across all components
    - Clear validation rules
    - Standardized error handling
    - Predictable status reporting
  - [x] Key Advantages:
    - Single source of truth for message structure
    - Easy to validate and process messages
    - Clear error handling patterns
    - Consistent status updates
  - [x] Implementation Notes:
    - Will be implemented in base interface
    - Required for all new tools
    - Complexity: Medium
    - Risk: Low
    - Time Estimate: 2-3 days
  - [x] Related to: Message Format V, Documentation Updates VII

### 3. Configuration Inheritance (CRITICAL) [x]
- [x] Define configuration inheritance strategy
  - [x] Decision: Separate service source (LOCAL/REMOTE/PARENT) from service offering (NONE/SERVE)
  - [x] Benefits:
    - Clear separation of service source and offering
    - Each graph manages only its own services
    - No awareness of child graphs
    - Simple parent-child relationship
  - [x] Key Advantages:
    - Clean separation of concerns
    - Flexible service configuration
    - Easy to add new services
    - Clear service lifecycle management
  - [x] Implementation Notes:
    - Will be implemented in base graph functionality
    - Required for service management
    - Complexity: Medium
    - Risk: Low
    - Time Estimate: 2-3 days
  - [x] Related to: File Review I.B, Configuration Updates VII

### 4. RAG Implementation (CRITICAL)
- [ ] Design RAG integration
  - [ ] Decision: TBD
  - [ ] Benefits: TBD
  - [ ] Key Advantages: TBD
  - [ ] Implementation Notes: TBD
  - [ ] Related to: RAG Awareness II.B

### 5. LLM Integration and Selection (IMPORTANT)
- [ ] Design LLM selection and configuration system
  - [ ] Decision: TBD
  - [ ] Benefits: TBD
  - [ ] Key Advantages: TBD
  - [ ] Implementation Notes: TBD
  - [ ] Related to: LLM Integration VI, Technical Debt VIII.E

### 6. Multi-Personality System (DEFERRED)
- [ ] Design personality system
  - [ ] Decision: TBD
  - [ ] Benefits: TBD
  - [ ] Key Advantages: TBD
  - [ ] Implementation Notes: TBD
  - [ ] Related to: Deferred Items I

[Previous sections remain unchanged]

### Path A: Rapid Development (After Critical Decisions)
1. [ ] Implement Message Format Standardization
   [Previous message format implementation remains unchanged]

2. [ ] Implement Configuration Inheritance
   - [ ] Service Source Configuration
     ```python
     from enum import Enum
     from typing import Optional, Dict, Any, List
     from pydantic import BaseModel

     class ServiceSource(str, Enum):
         """Source of service implementation."""
         LOCAL = "local"      # Run service locally
         REMOTE = "remote"    # Use remote service
         PARENT = "parent"    # Use parent's service

     class ServiceOffering(str, Enum):
         """Whether this graph offers the service to child graphs."""
         NONE = "none"        # Don't offer service
         SERVE = "serve"      # Offer service to children

     class ServiceConfig(BaseModel):
         """Base configuration for any service (LLM, DB, Logging, etc)."""
         source: ServiceSource = ServiceSource.LOCAL
         offering: ServiceOffering = ServiceOffering.NONE
         url: Optional[str] = None  # For remote services
         config: Dict[str, Any] = {}  # Service-specific config

     class LLMServiceConfig(ServiceConfig):
         """LLM service configuration."""
         model: str = "default"
         temperature: float = 0.7
         max_tokens: int = 2000

     class DBServiceConfig(ServiceConfig):
         """Database service configuration."""
         provider: str = "sqlite"
         database: str = "default.db"

     class LoggingServiceConfig(ServiceConfig):
         """Logging service configuration."""
         level: str = "INFO"
         format: str = "standard"
     ```

   - [ ] Base Graph Service Management
     ```python
     class BaseGraphServices:
         """Base class for graph service management."""
         def __init__(self, config: Dict[str, ServiceConfig], parent_services: Optional['BaseGraphServices'] = None):
             self.config = config
             self.parent_services = parent_services
             self._service_instances = {}
             self._offered_services = {}

         async def get_service(self, service_name: str) -> Any:
             """Get service instance based on configuration."""
             if service_name not in self._service_instances:
                 service_config = self.config[service_name]
                 
                 if service_config.source == ServiceSource.PARENT and self.parent_services:
                     # Use parent's service
                     self._service_instances[service_name] = await self.parent_services.get_service(service_name)
                 elif service_config.source == ServiceSource.REMOTE:
                     # Create remote connection
                     self._service_instances[service_name] = await self._create_remote_service(service_name)
                 else:
                     # Create local service
                     self._service_instances[service_name] = await self._create_local_service(service_name)

                 # If this graph offers the service, store it
                 if service_config.offering == ServiceOffering.SERVE:
                     self._offered_services[service_name] = self._service_instances[service_name]

             return self._service_instances[service_name]

         async def _create_remote_service(self, service_name: str) -> Any:
             """Create connection to remote service."""
             # Implementation depends on service type
             pass

         async def _create_local_service(self, service_name: str) -> Any:
             """Create local service instance."""
             # Implementation depends on service type
             pass

         def get_offered_services(self) -> Dict[str, Any]:
             """Get services this graph offers to children."""
             return self._offered_services
     ```

   - [ ] Graph Configuration Integration
     ```python
     class GraphConfig(BaseModel):
         """Graph-level configuration with service management."""
         name: str
         services: Dict[str, ServiceConfig] = Field(default_factory=dict)

         def initialize_services(self, parent_services: Optional[BaseGraphServices] = None) -> BaseGraphServices:
             """Initialize service management."""
             return BaseGraphServices(self.services, parent_services)
     ```

   - [ ] Usage Example
     ```python
     # In orchestrator (parent)
     orchestrator_config = GraphConfig(
         name="orchestrator",
         services={
             "llm": LLMServiceConfig(
                 source=ServiceSource.LOCAL,
                 offering=ServiceOffering.SERVE
             ),
             "db": DBServiceConfig(
                 source=ServiceSource.LOCAL,
                 offering=ServiceOffering.SERVE
             ),
             "logging": LoggingServiceConfig(
                 source=ServiceSource.LOCAL,
                 offering=ServiceOffering.SERVE
             )
         }
     )
     orchestrator_services = orchestrator_config.initialize_services()

     # In personal assistant (child)
     pa_config = GraphConfig(
         name="personal_assistant",
         services={
             "llm": LLMServiceConfig(
                 source=ServiceSource.PARENT,  # Use parent's LLM
                 offering=ServiceOffering.NONE  # Don't offer to children
             ),
             "db": DBServiceConfig(
                 source=ServiceSource.PARENT,  # Use parent's DB
                 offering=ServiceOffering.NONE
             ),
             "logging": LoggingServiceConfig(
                 source=ServiceSource.LOCAL,  # Local logging
                 offering=ServiceOffering.NONE
             )
         }
     )
     pa_services = pa_config.initialize_services(orchestrator_services)
     ```

3. [ ] Testing and Validation
   [Previous testing section remains unchanged]

[Previous sections remain unchanged]

============================


Now I moved a section down from the body of the document to the checklist portion. I think it duplicates some checklist tasls but adds or suplements other.  Please roll it into the greater checklist, Risks should be under each decision summary, workarounds are only needed for items that will be after rapid deployment step, and future migrations are below our entire checklist.  If we add it as a section in the checklist, it is no longer future, but planned.  

I'll help reorganize the content to eliminate duplication and improve the structure. Let me analyze the current content and make the necessary changes.
I've reorganized the content to:
Moved risks under each critical decision summary
Removed the separate "Known Risks and Limitations" section
Created a new "Future Migration Needs" section at the end
Eliminated duplication between the checklist and the moved section
Added more detailed migration tasks
The structure is now more logical with:
Risks directly associated with their relevant decisions
Workarounds only listed for items that will be after rapid deployment
Future migrations as a separate section with detailed tasks
No duplication between sections

// ... existing code ...

## Critical Design Decisions and Discussions

### 1. Request ID and Message Flow (CRITICAL) [x]
- [x] Design request ID inheritance system
  - [x] Decision: Implement "Request Context" pattern for distributed systems
  - [x] Benefits:
    - Clean separation of concerns
    - Easy to track request flow
    - Maintains context through async operations
    - Simple to implement and understand
    - Follows standard patterns used in distributed systems
  - [x] Key Advantages:
    - Each level only needs to know about its own request_id
    - Parent-child relationships are preserved in metadata
    - Easy to trace request flow through logs
    - Works well with async operations
    - Maintains context through the entire request lifecycle
  - [x] Implementation Notes:
    - Core functionality required before rapid deployment
    - Will be implemented in base graph functionality
    - Complexity: Medium
    - Risk: Low
    - Time Estimate: 2-3 days
  - [x] Related to: File Review I.A, Message Format V.A
  - [x] Known Risks:
    - Request ID system changes may affect existing tools
    - Current workaround: Use simple UUID for request tracking
    - Future migration: Update request ID handling in all tools

### 2. Message Format Standardization (CRITICAL) [x]
- [x] Define message format requirements
  - [x] Decision: Standardize all messages to JSON format with consistent structure
  - [x] Benefits:
    - Consistent message handling across all components
    - Clear validation rules
    - Standardized error handling
    - Predictable status reporting
  - [x] Key Advantages:
    - Single source of truth for message structure
    - Easy to validate and process messages
    - Clear error handling patterns
    - Consistent status updates
  - [x] Implementation Notes:
    - Will be implemented in base interface
    - Required for all new tools
    - Complexity: Medium
    - Risk: Low
    - Time Estimate: 2-3 days
  - [x] Related to: Message Format V, Documentation Updates VII
  - [x] Known Risks:
    - Message format updates may break existing tools
    - Current workaround: Implement basic message validation
    - Future migration: Migrate to new message formats in all tools

### 3. Services source configuration and serving options (CRITICAL) [x]
- [x] Define configuration inheritance strategy
  - [x] Decision: Separate service source (LOCAL/REMOTE/PARENT) from service offering (NONE/SERVE)
  - [x] Benefits:
    - Clear separation of service source and offering
    - Each graph manages only its own services
    - No awareness of child graphs
    - Simple parent-child relationship
  - [x] Key Advantages:
    - Clean separation of concerns
    - Flexible service configuration
    - Easy to add new services
    - Clear service lifecycle management
  - [x] Implementation Notes:
    - Will be implemented in base graph functionality
    - Required for service management
    - Complexity: Medium
    - Risk: Low
    - Time Estimate: 2-3 days
  - [x] Related to: File Review I.B, Configuration Updates VII
  - [x] Known Risks:
    - Configuration inheritance modifications may affect tool behavior
    - Current workaround: Use local configuration only
    - Future migration: Implement configuration inheritance in all tools

// ... existing code ...

## Implementation Paths

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

### Path A: Rapid Development (After Critical Decisions)
// ... existing code ...

### Path B: Full Implementation
// ... existing code ...

## Future Migration Needs
1. [ ] Request ID System
   - [ ] Update request ID handling in all tools
   - [ ] Migrate to new request context system
   - [ ] Update documentation and examples

2. [ ] Message Format
   - [ ] Migrate all tools to new message formats
   - [ ] Update validation and error handling
   - [ ] Update documentation and examples

3. [ ] Configuration System
   - [ ] Implement configuration inheritance in all tools
   - [ ] Update service management
   - [ ] Update documentation and examples

4. [ ] State Management
   - [ ] Enhance state persistence
   - [ ] Update state tracking
   - [ ] Update documentation and examples

5. [ ] Error Handling
   - [ ] Implement advanced error handling
   - [ ] Add retry strategies
   - [ ] Update documentation and examples

// ... existing code ...

=======================
// ... existing code until Implementation Planning and Checklist ...

# Implementation Planning and Checklist

## I. Foundational Edits
Core features and functionality needed for MVP. High risk changes only if they come with high return.

### A. Request ID and Message Flow [x]
- [x] Design request ID inheritance system
  - [x] Decision: Implement "Request Context" pattern for distributed systems
  - [x] Benefits:
    - Clean separation of concerns
    - Easy to track request flow
    - Maintains context through async operations
    - Simple to implement and understand
    - Follows standard patterns used in distributed systems
  - [x] Key Advantages:
    - Each level only needs to know about its own request_id
    - Parent-child relationships are preserved in metadata
    - Easy to trace request flow through logs
    - Works well with async operations
    - Maintains context through the entire request lifecycle
  - [x] Implementation Notes:
    - Core functionality required before rapid deployment
    - Will be implemented in base graph functionality
    - Complexity: Medium
    - Risk: Low
    - Time Estimate: 2-3 days
  - [x] Known Risks:
    - Request ID system changes may affect existing tools
    - Current workaround: Use simple UUID for request tracking
    - Future migration: Update request ID handling in all tools

### B. Message Format Standardization [x]
- [x] Define message format requirements
  - [x] Decision: Standardize all messages to JSON format with consistent structure
  - [x] Benefits:
    - Consistent message handling across all components
    - Clear validation rules
    - Standardized error handling
    - Predictable status reporting
  - [x] Key Advantages:
    - Single source of truth for message structure
    - Easy to validate and process messages
    - Clear error handling patterns
    - Consistent status updates
  - [x] Implementation Notes:
    - Will be implemented in base interface
    - Required for all new tools
    - Complexity: Medium
    - Risk: Low
    - Time Estimate: 2-3 days
  - [x] Known Risks:
    - Message format updates may break existing tools
    - Current workaround: Implement basic message validation
    - Future migration: Migrate to new message formats in all tools

### C. Services Source Configuration [x]
- [x] Define configuration inheritance strategy
  - [x] Decision: Separate service source (LOCAL/REMOTE/PARENT) from service offering (NONE/SERVE)
  - [x] Benefits:
    - Clear separation of service source and offering
    - Each graph manages only its own services
    - No awareness of child graphs
    - Simple parent-child relationship
  - [x] Key Advantages:
    - Clean separation of concerns
    - Flexible service configuration
    - Easy to add new services
    - Clear service lifecycle management
  - [x] Implementation Notes:
    - Will be implemented in base graph functionality
    - Required for service management
    - Complexity: Medium
    - Risk: Low
    - Time Estimate: 2-3 days
  - [x] Known Risks:
    - Configuration inheritance modifications may affect tool behavior
    - Current workaround: Use local configuration only
    - Future migration: Implement configuration inheritance in all tools

## II. Basic Fast and High Risk Deployment
Minimum functionality with template and initial tools. Minimize time and effort that may be lost due to future changes.

### A. Quick Start Tools and Templates
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

### B. Core Message Format Implementation
1. [ ] Update base_interface.py
   - [ ] Add MessageFormat class
   - [ ] Add RequestContext class
   - [ ] Add request handling examples
   - [ ] Add tool execution examples

2. [ ] Basic Testing
   - [ ] Test message flow
   - [ ] Verify error handling
   - [ ] Validate status reporting
   - [ ] Check backward compatibility

## III. Required Edits
Necessary changes before broad deployment. Medium risk or higher changes that may break existing tools.

### A. RAG Implementation
- [ ] Design RAG integration
  - [ ] Decision: TBD
  - [ ] Benefits: TBD
  - [ ] Key Advantages: TBD
  - [ ] Implementation Notes: TBD
  - [ ] Related to: RAG Awareness II.B

### B. LLM Integration and Selection
- [ ] Design LLM selection and configuration system
  - [ ] Decision: TBD
  - [ ] Benefits: TBD
  - [ ] Key Advantages: TBD
  - [ ] Implementation Notes: TBD
  - [ ] Related to: LLM Integration VI, Technical Debt VIII.E

### C. State Management
- [ ] Implement state persistence
- [ ] Add request tracking
- [ ] Update documentation
- [ ] Test state handling

## IV. Standard Deployment
Create standard deployment template and upgrade existing tools.

### A. Template Development
- [ ] Create standard deployment template
- [ ] Document deployment process
- [ ] Add configuration examples
- [ ] Create upgrade guide

### B. Tool Upgrades
- [ ] Upgrade existing tools to standard
- [ ] Update documentation
- [ ] Add migration scripts
- [ ] Test compatibility

## V. Enhancement Edits
Medium risk changes only if critical to functionality. Repairs and low risk feature additions.

### A. Advanced Features
- [ ] Add advanced error handling
- [ ] Implement retry strategies
- [ ] Add monitoring
- [ ] Update documentation

### B. Performance Optimization
- [ ] Profile critical paths
- [ ] Optimize message handling
- [ ] Improve state management
- [ ] Update documentation

### C. Security Review
- [ ] Review authentication
- [ ] Check authorization
- [ ] Verify privacy controls
- [ ] Update security docs

## VI. Future Migration Needs
Tasks required for future system updates and improvements.

### A. Request ID System
- [ ] Update request ID handling in all tools
- [ ] Migrate to new request context system
- [ ] Update documentation and examples

### B. Message Format
- [ ] Migrate all tools to new message formats
- [ ] Update validation and error handling
- [ ] Update documentation and examples

### C. Configuration System
- [ ] Implement configuration inheritance in all tools
- [ ] Update service management
- [ ] Update documentation and examples

### D. State Management
- [ ] Enhance state persistence
- [ ] Update state tracking
- [ ] Update documentation and examples

### E. Error Handling
- [ ] Implement advanced error handling
- [ ] Add retry strategies
- [ ] Update documentation and examples

// ... rest of existing content ...

============================


// ... existing code until Implementation Planning and Checklist ...

# Implementation Planning and Checklist

## I. Critical Discussion and Decisions
These must be discussed and answered before any code is written. They are the foundation of the project and establish our task order.

### A. Request ID and Message Flow
1. Questions and concerns
   - [ ] How to handle request ID inheritance across multiple levels?
   - [ ] How to maintain context through async operations?
   - [ ] How to track parent-child relationships?

2. Decisions
   - [x] Implement "Request Context" pattern for distributed systems
   - [x] Use UUID for request IDs
   - [x] Store parent-child relationships in metadata

3. Benefits:
   - [x] Clean separation of concerns
   - [x] Easy to track request flow
   - [x] Maintains context through async operations
   - [x] Simple to implement and understand
   - [x] Follows standard patterns used in distributed systems

4. Key Advantages:
   - [x] Each level only needs to know about its own request_id
   - [x] Parent-child relationships are preserved in metadata
   - [x] Easy to trace request flow through logs
   - [x] Works well with async operations
   - [x] Maintains context through the entire request lifecycle

5. Implementation Notes:
   - [x] Core functionality required before rapid deployment
   - [x] Will be implemented in base graph functionality
   - [x] Complexity: Medium
   - [x] Risk: Low
   - [x] Time Estimate: 2-3 days

6. Related to: File Review I.A, Message Format V.A

### B. Message Format Standardization
1. Questions and concerns
   - [ ] How to standardize messages between CLI and LLM?
   - [ ] How to handle validation and error reporting?
   - [ ] How to maintain backward compatibility?

2. Decisions
   - [x] Standardize all messages to JSON format with consistent structure
   - [x] Implement validation at system boundaries
   - [x] Use standardized error handling patterns

3. Benefits:
   - [x] Consistent message handling across all components
   - [x] Clear validation rules
   - [x] Standardized error handling
   - [x] Predictable status reporting

4. Key Advantages:
   - [x] Single source of truth for message structure
   - [x] Easy to validate and process messages
   - [x] Clear error handling patterns
   - [x] Consistent status updates

5. Implementation Notes:
   - [x] Will be implemented in base interface
   - [x] Required for all new tools
   - [x] Complexity: Medium
   - [x] Risk: Low
   - [x] Time Estimate: 2-3 days

6. Related to: Message Format V, Documentation Updates VII

### C. Services Source Configuration
1. Questions and concerns
   - [ ] How to handle service inheritance?
   - [ ] How to manage service lifecycle?
   - [ ] How to handle remote services?

2. Decisions
   - [x] Separate service source (LOCAL/REMOTE/PARENT) from service offering (NONE/SERVE)
   - [x] Each graph manages only its own services
   - [x] No awareness of child graphs

3. Benefits:
   - [x] Clear separation of service source and offering
   - [x] Each graph manages only its own services
   - [x] No awareness of child graphs
   - [x] Simple parent-child relationship

4. Key Advantages:
   - [x] Clean separation of concerns
   - [x] Flexible service configuration
   - [x] Easy to add new services
   - [x] Clear service lifecycle management

5. Implementation Notes:
   - [x] Will be implemented in base graph functionality
   - [x] Required for service management
   - [x] Complexity: Medium
   - [x] Risk: Low
   - [x] Time Estimate: 2-3 days

6. Related to: File Review I.B, Configuration Updates VII

### D. RAG Implementation
1. Questions and concerns
   - [ ] How to integrate RAG with existing message flow?
   - [ ] How to handle vector storage?
   - [ ] How to manage privacy and access control?

2. Decisions
   - [ ] TBD

3. Benefits:
   - [ ] TBD

4. Key Advantages:
   - [ ] TBD

5. Implementation Notes:
   - [ ] TBD

6. Related to: RAG Awareness II.B

### E. LLM Integration and Selection
1. Questions and concerns
   - [ ] How to handle multiple LLM providers?
   - [ ] How to manage model selection?
   - [ ] How to handle fallbacks?

2. Decisions
   - [ ] TBD

3. Benefits:
   - [ ] TBD

4. Key Advantages:
   - [ ] TBD

5. Implementation Notes:
   - [ ] TBD

6. Related to: LLM Integration VI, Technical Debt VIII.E

### F. Multi-Personality System
1. Questions and concerns
   - [ ] How to manage personality switching?
   - [ ] How to maintain context across personalities?
   - [ ] How to handle personality-specific tools?

2. Decisions
   - [ ] DEFERRED

3. Benefits:
   - [ ] TBD

4. Key Advantages:
   - [ ] TBD

5. Implementation Notes:
   - [ ] TBD

6. Related to: Deferred Items I

### G. Graph Database - Memories Mem0 Server
1. Questions and concerns
   - [ ] How to integrate with existing state management?
   - [ ] How to handle synchronization?
   - [ ] How to manage access control?

2. Decisions
   - [ ] TBD

3. Benefits:
   - [ ] TBD

4. Key Advantages:
   - [ ] TBD

5. Implementation Notes:
   - [ ] TBD

6. Related to: State Management III.C

## II. Foundation Edits
Core features needed for MVP. High risk changes with high return.

### A. Request ID and Message Flow Implementation
1. [ ] Core Implementation
   ```python
   class RequestContext:
       """Standard request context for tracking request flow."""
       def __init__(self, request_id: str = None, parent_request_id: str = None):
           self.request_id = request_id or str(uuid.uuid4())
           self.parent_request_id = parent_request_id
           self.timestamp = datetime.now()
           self.metadata = {}

       def create_child_context(self) -> 'RequestContext':
           """Create a new context for a child request."""
           return RequestContext(
               request_id=str(uuid.uuid4()),
               parent_request_id=self.request_id
           )

       def to_metadata(self) -> Dict[str, Any]:
           """Convert to metadata format for logging."""
           return {
               "request_id": self.request_id,
               "parent_request_id": self.parent_request_id,
               "timestamp": self.timestamp.isoformat(),
               **self.metadata
           }
   ```

2. [ ] Message Handling
   ```python
   async def handle_request(request: Dict[str, Any], context: RequestContext) -> Dict[str, Any]:
       # Log incoming request
       await log_message(
           content=request["content"],
           metadata=context.to_metadata(),
           sender="orchestrator",
           target="tool"
       )

       # Create child context for tool
       tool_context = context.create_child_context()
       
       # Pass to tool
       result = await tool.execute(request, tool_context)
       
       # Log response
       await log_message(
           content=result["content"],
           metadata=context.to_metadata(),  # Use original context for response
           sender="tool",
           target="orchestrator"
       )
   ```

3. [ ] Tool Execution
   ```python
   async def execute_tool(tool_name: str, task: Dict[str, Any], context: RequestContext) -> Dict[str, Any]:
       """Execute a tool using the registry."""
       try:
           # Log request
           await log_and_persist_message(
               session_state=context.session_state,
               role=MessageRole.TOOL,
               content=f"Tool request: {task}",
               metadata=context.to_metadata(),
               sender=f"orchestrator.{tool_name}",
               target=f"{tool_name}.system"
           )

           # Create child context for tool
           tool_context = context.create_child_context()
           
           # Execute tool
           result = await tool.execute(task, tool_context)
           
           # Log response
           await log_and_persist_message(
               session_state=context.session_state,
               role=MessageRole.TOOL,
               content=f"Tool response: {result}",
               metadata=context.to_metadata(),
               sender=f"{tool_name}.system",
               target=f"orchestrator.{tool_name}"
           )
           
           return result
       except Exception as e:
           # Log error with context
           await log_and_persist_message(
               session_state=context.session_state,
               role=MessageRole.ERROR,
               content=str(e),
               metadata=context.to_metadata(),
               sender=f"{tool_name}.system",
               target=f"orchestrator.{tool_name}"
           )
           raise
   ```

### G. Message Format Standardization Implementation
1. [ ] Core Message Format
   ```python
   class MessageFormat:
       """Standard message format for all system communications."""
       
       @staticmethod
       def create_request(
           method: str,
           params: Dict[str, Any],
           request_id: Optional[str] = None,
           parent_request_id: Optional[str] = None
       ) -> Dict[str, Any]:
           """Create a standardized request message."""
           return {
               "request_id": request_id or str(uuid.uuid4()),
               "parent_request_id": parent_request_id,
               "type": "request",
               "method": method,
               "params": params,
               "timestamp": datetime.now().isoformat()
           }
       
       @staticmethod
       def create_response(
           request_id: str,
           result: Dict[str, Any],
           status: str = "success",
           metadata: Optional[Dict[str, Any]] = None
       ) -> Dict[str, Any]:
           """Create a standardized response message."""
           return {
               "request_id": request_id,
               "type": "response",
               "status": status,
               "result": result,
               "metadata": metadata or {},
               "timestamp": datetime.now().isoformat()
           }
       
       @staticmethod
       def create_error(
           request_id: str,
           error_code: str,
           message: str,
           details: Optional[Dict[str, Any]] = None
       ) -> Dict[str, Any]:
           """Create a standardized error message."""
           return {
               "request_id": request_id,
               "type": "error",
               "status": "error",
               "error": {
                   "code": error_code,
                   "message": message,
                   "details": details or {}
               },
               "timestamp": datetime.now().isoformat()
           }
       
       @staticmethod
       def create_status_update(
           request_id: str,
           status: str,
           progress: Optional[float] = None,
           message: Optional[str] = None
       ) -> Dict[str, Any]:
           """Create a standardized status update message."""
           return {
               "request_id": request_id,
               "type": "status",
               "status": status,
               "progress": progress,
               "message": message,
               "timestamp": datetime.now().isoformat()
           }
   ```

### H. Services Source Configuration Implementation
1. [ ] Service Configuration
   ```python
   from enum import Enum
   from typing import Optional, Dict, Any, List
   from pydantic import BaseModel

   class ServiceSource(str, Enum):
       """Source of service implementation."""
       LOCAL = "local"      # Run service locally
       REMOTE = "remote"    # Use remote service
       PARENT = "parent"    # Use parent's service

   class ServiceOffering(str, Enum):
       """Whether this graph offers the service to child graphs."""
       NONE = "none"        # Don't offer service
       SERVE = "serve"      # Offer service to children

   class ServiceConfig(BaseModel):
       """Base configuration for any service (LLM, DB, Logging, etc)."""
       source: ServiceSource = ServiceSource.LOCAL
       offering: ServiceOffering = ServiceOffering.NONE
       url: Optional[str] = None  # For remote services
       config: Dict[str, Any] = {}  # Service-specific config

   class LLMServiceConfig(ServiceConfig):
       """LLM service configuration."""
       model: str = "default"
       temperature: float = 0.7
       max_tokens: int = 2000

   class DBServiceConfig(ServiceConfig):
       """Database service configuration."""
       provider: str = "sqlite"
       database: str = "default.db"

   class LoggingServiceConfig(ServiceConfig):
       """Logging service configuration."""
       level: str = "INFO"
       format: str = "standard"
   ```

2. [ ] Service Management
   ```python
   class BaseGraphServices:
       """Base class for graph service management."""
       def __init__(self, config: Dict[str, ServiceConfig], parent_services: Optional['BaseGraphServices'] = None):
           self.config = config
           self.parent_services = parent_services
           self._service_instances = {}
           self._offered_services = {}

       async def get_service(self, service_name: str) -> Any:
           """Get service instance based on configuration."""
           if service_name not in self._service_instances:
               service_config = self.config[service_name]
               
               if service_config.source == ServiceSource.PARENT and self.parent_services:
                   # Use parent's service
                   self._service_instances[service_name] = await self.parent_services.get_service(service_name)
               elif service_config.source == ServiceSource.REMOTE:
                   # Create remote connection
                   self._service_instances[service_name] = await self._create_remote_service(service_name)
               else:
                   # Create local service
                   self._service_instances[service_name] = await self._create_local_service(service_name)

               # If this graph offers the service, store it
               if service_config.offering == ServiceOffering.SERVE:
                   self._offered_services[service_name] = self._service_instances[service_name]

           return self._service_instances[service_name]

       async def _create_remote_service(self, service_name: str) -> Any:
           """Create connection to remote service."""
           # Implementation depends on service type
           pass

       async def _create_local_service(self, service_name: str) -> Any:
           """Create local service instance."""
           # Implementation depends on service type
           pass

       def get_offered_services(self) -> Dict[str, Any]:
           """Get services this graph offers to children."""
           return self._offered_services
   ```

3. [ ] Graph Configuration
   ```python
   class GraphConfig(BaseModel):
       """Graph-level configuration with service management."""
       name: str
       services: Dict[str, ServiceConfig] = Field(default_factory=dict)

       def initialize_services(self, parent_services: Optional[BaseGraphServices] = None) -> BaseGraphServices:
           """Initialize service management."""
           return BaseGraphServices(self.services, parent_services)
   ```

## III. Early Fast and High Risk Deployment
Minimum functionality with templates. Initial tools with minimal effort.



### A. Document known risks
[ ] Document Known Risks
   - [ ] List potential core changes that would affect tools
   - [ ] Document workarounds for current limitations
   - [ ] Create migration guide for future updates
   - [ ] Add version compatibility notes
   
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

### A. Create Basic Template
1. [ ] Extract minimal working template from orchestrator
2. [ ] Create template_agent with basic structure
3. [ ] Document template usage and customization
4. [ ] Add example tool implementation

### B. Create First Tool (Personal Assistant)
1. [ ] Create basic structure
2. [ ] Implement core functionality
3. [ ] Add basic error handling
4. [ ] Test basic operations

### C. Create First Tool for a Tool (Email)
1. [ ] Create email tool structure
2. [ ] Implement basic email operations
3. [ ] Add error handling
4. [ ] Test email functionality

### E. Start Running and Keep Notes on Issues
1. [ ] Set up logging
2. [ ] Create issue tracking
3. [ ] Document workarounds
4. [ ] Plan fixes

## IV. Required Edits
Necessary changes before broad deployment. Medium/high risk changes.

### A. RAG Implementation
1. [ ] Design RAG integration
2. [ ] Implement vector storage
3. [ ] Add search functionality
4. [ ] Test and validate

### B. LLM Integration
1. [ ] Design LLM selection system
2. [ ] Implement provider management
3. [ ] Add fallback handling
4. [ ] Test integration

### C. State Management
1. [ ] Implement state persistence
2. [ ] Add request tracking
3. [ ] Update documentation
4. [ ] Test state handling

## V. Standard Deployment
Create standard deployment template and upgrade existing tools.

### A. Create Standard Deployment Template
1. [ ] Create deployment template
2. [ ] Document deployment process
3. [ ] Add configuration examples
4. [ ] Create upgrade guide

### B. Upgrade Existing Tools
1. [ ] Upgrade personal assistant
2. [ ] Upgrade email tool
3. [ ] Update documentation
4. [ ] Test compatibility

### C. Update Documentation
1. [ ] Update API documentation
2. [ ] Add usage examples
3. [ ] Update configuration guide
4. [ ] Add troubleshooting guide

## VI. Enhancement Edits
Medium risk changes if critical. Repairs and low risk features.

### A. Advanced Features
1. [ ] Add advanced error handling
2. [ ] Implement retry strategies
3. [ ] Add monitoring
4. [ ] Update documentation

### B. Performance Optimization
1. [ ] Profile critical paths
2. [ ] Optimize message handling
3. [ ] Improve state management
4. [ ] Update documentation

### C. Security Review
1. [ ] Review authentication
2. [ ] Check authorization
3. [ ] Verify privacy controls
4. [ ] Update security docs

## VII. Future Migration Needs
Tasks required for future system updates and improvements.

### A. Request ID System
1. [ ] Update request ID handling in all tools
2. [ ] Migrate to new request context system
3. [ ] Update documentation and examples

### B. Message Format
1. [ ] Migrate all tools to new message formats
2. [ ] Update validation and error handling
3. [ ] Update documentation and examples

### C. Configuration System
1. [ ] Implement configuration inheritance in all tools
2. [ ] Update service management
3. [ ] Update documentation and examples

### D. State Management
1. [ ] Enhance state persistence
2. [ ] Update state tracking
3. [ ] Update documentation and examples

### E. Error Handling
1. [ ] Implement advanced error handling
2. [ ] Add retry strategies
3. [ ] Update documentation and examples

## VIII. Technical Debt





### A. [ ] Code Review
   - [ ] Review message passing code
   - [ ] Check request ID handling
   - [ ] Verify error handling
   - [ ] Update tests

### B. [ ] Performance Optimization
   - [ ] Profile critical paths
   - [ ] Optimize message handling
   - [ ] Improve state management
   - [ ] Update documentation

### C. [ ] Security Review
   - [ ] Review authentication
   - [ ] Check authorization
   - [ ] Verify privacy controls
   - [ ] Update security docs

// ... rest of existing content ...

============================
// ... existing code until Message Format Standardization section ...

Bob
### B. Message Format Standardization
1. Questions and concerns
   - [ ] How to standardize messages between CLI and LLM?
   - [ ] How to handle validation and error reporting?
   - [ ] How to maintain backward compatibility?

// ... continue with rest of existing content ...


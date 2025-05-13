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

2. Decisions
   a. [x] Design request ID inheritance system
   b. [x] Review current UUID implementation
   c. [x] Evaluate options for additional IDs (metadata vs separate tracking)
   d. [x] Design parent/child request relationship
   e. [x] Document request chain tracking approach
   f. [x] Related to: File Review I.A, Message Format V.A

3. Benefits:
   a. Clean separation of concerns
   b. Easy to track request flow
   c. Maintains context through async operations
   d. Simple to implement and understand
   e. Follows standard patterns used in distributed systems

4. Key Advantages:
   a. [x] Each level only needs to know about its own request_id
   b. [x] Parent-child relationships are preserved in metadata
   c. [x] Easy to trace request flow through logs
   d. [x] Works well with async operations
   e. [x] Maintains context through the entire request lifecycle

5. Implementation Notes:
   a. [x] Core functionality required before rapid deployment
   b. [x] Will be implemented in base graph functionality
   c. [x] Complexity: Medium
   d. [x] Risk: Low
   e. [x] Time Estimate: 2-3 days

6. Related to: File Review I.A, Message Format V.A

### B. Message Format Standardization (CRITICAL)
1. Questions and concerns
   a. [ ] How to standardize messages between CLI and LLM?
   b. [ ] How to handle validation and error reporting?
   c. [ ] How to maintain backward compatibility?

2. Current Implementation:
   a. The CLI interface (src/ui/cli/interface.py) uses a MessageFormat class from base_interface.py for standardizing messages
   b. Messages are passed through several layers:
      - CLI Interface → Orchestrator Agent → Tools
   c. Each layer has its own message format handling

3. Issues Found:
   a. Inconsistent message formats between layers
   b. Some direct string passing instead of structured JSON
   c. Mixed usage of simple dictionaries and MessageFormat objects
   d. Tool responses not fully standardized

4. Specific Problems:
   a. orchestrator_agent.py sometimes returns simple {"response": message} instead of proper MessageFormat
   b. Tool results are formatted differently from regular messages
   c. CLI display handles multiple message formats
   d. No clear validation of message structure between layers

5. Difficulty to Fix:
   a. Complexity: Medium
   b. Risk: Low (mostly additive changes)
   c. Effort: Moderate (need to update multiple files)

6. Decisions
   a. [x] Define message format requirements
   b. [x] CLI to JSON format transition
   c. [x] Message validation rules
   d. [x] Error handling standards
   e. [x] Status reporting format
   f. [x] Related to: Message Format V, Documentation Updates VII

7. Benefits:
   a. Consistent message handling across all components
   b. Clear validation rules
   c. Standardized error handling
   d. Predictable status reporting
   e. Improved debugging and error tracking
   f. Better integration with monitoring tools

8. Key Advantages:
   a. Single source of truth for message structure
   b. Easy to validate and process messages
   c. Clear error handling patterns
   d. Consistent status updates
   e. Simplified tool integration
   f. Better error tracking and debugging

9. Implementation Tasks:
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

10. Testing and Validation
    - [ ] Test message flow through all components
    - [ ] Verify error handling
    - [ ] Validate status reporting
    - [ ] Check backward compatibility

### C. Services Source Configuration (CRITICAL)
1. Questions and concerns
   a. [ ] How to handle service inheritance?
   b. [ ] How to manage service lifecycle?
   c. [ ] How to handle remote services?

2. Key Discussion Points:
   ```
   # Key Insight: Service Source vs Service Offering
   - Service source (local/remote/parent) and service offering (serve) are different concerns
   - This separation helps avoid unnecessary message passing overhead while maintaining flexibility
   - Each graph only needs to know about its parent's services, not its children
   - Service source and offering are independent decisions
   - Services are managed at the graph level through BaseGraphServices
   - Clear separation of concerns between service configuration and service management
   ```

3. Implementation Approach:
   ```
   # Implementation Strategy
   - Separate service source (LOCAL/REMOTE/PARENT) from service offering (NONE/SERVE)
   - Make it a base graph feature through BaseGraphServices
   - Keep each graph focused only on its own services and parent relationship
   - Use a dictionary-based service configuration for flexibility
   - Code lives in base graph functionality, making it available to all graphs
   - Maintains clean separation of concerns
   ```

4. Decisions
   a. [x] Define configuration inheritance strategy
   b. [x] LLM config inheritance (parent/local/remote)
   c. [x] DB config inheritance (parent/local/remote)
   d. [x] State management (parent/local/standalone)
   e. [x] User config inheritance for line-level security
   f. [x] Logging config inheritance
   g. [x] Related to: File Review I.B, Configuration Updates VII

### D. RAG Implementation (CRITICAL)
1. Questions and concerns
   a. [ ] How to integrate RAG with existing message flow?
   b. [ ] How to handle vector storage?
   c. [ ] How to manage privacy and access control?
   d. [ ] Design RAG integration
   e. [ ] Search method implementation
   f. [ ] Privacy controls
   g. [ ] Cross-conversation reference handling
   h. [ ] Related to: RAG Awareness II.B

2. Decisions
   a. [ ] TBD

3. Benefits:
   a. [ ] TBD

4. Key Advantages:
   a. [ ] TBD

5. Implementation Notes:
   a. [ ] TBD

6. Related to: RAG Awareness II.B

### E. LLM Integration and Selection (IMPORTANT)
1. Questions and concerns
   a. [ ] How to handle multiple LLM providers?
   b. [ ] How to manage model selection?
   c. [ ] How to handle fallbacks?
   d. [ ] Design LLM selection and configuration system
   e. [ ] Graph-level vs global selection
   f. [ ] Task-specific LLM support
   g. [ ] Configuration inheritance rules
   h. [ ] LLM evaluation for request closure
   i. [ ] Related to: LLM Integration VI, Technical Debt VIII.E

2. Decisions
   a. [ ] TBD

3. Benefits:
   a. [ ] TBD

4. Key Advantages:
   a. [ ] TBD

5. Implementation Notes:
   a. [ ] TBD

6. Related to: LLM Integration VI, Technical Debt VIII.E

### F. Multi-Personality System (DEFERRED)
1. Questions and concerns
   a. [ ] How to manage personality switching?
   b. [ ] How to maintain context across personalities?
   c. [ ] How to handle personality-specific tools?

2. Decisions
   a. [ ] DEFERRED

3. Benefits:
   a. [ ] TBD

4. Key Advantages:
   a. [ ] TBD

5. Implementation Notes:
   a. [ ] TBD

6. Related to: Deferred Items I

### G. Graph Database - Memories Mem0 Server (TBD)

### H. State Management (CRITICAL)
1. Questions and concerns
   a. [ ] How to integrate with existing state management?
   b. [ ] How to handle synchronization?
   c. [ ] How to manage access control?

2. Decisions
   a. [ ] TBD

3. Benefits:
   a. [ ] TBD

4. Key Advantages:
   a. [ ] TBD

5. Implementation Notes:
   a. [ ] TBD

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
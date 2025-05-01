## Refactor and Modularize Codebase

To refactor and modularize your codebase for better organization and readability, we can follow a structured plan. This plan will involve moving components into appropriate directories and creating test files to ensure functionality is maintained. Here's a detailed implementation plan:

### Implementation Plan

#### 1. CLI Separation
- Done

#### 2. Tools and Agents as Separate Nodes
- **Objective**: Separate tools and agents into distinct modules.
- **Background**:  This graph has been greatly simplified.  Rather than multiple agents and many choices, there is only one real agent and tools that act like agents but have no LLM access.  Each of them will actually spawn a subgraph with that agents functions and tools.  Standard tools for customizing each agent's graph will be added in the standard way, as will specialized agents for certain specific tasks or testing.  The orchestrator is the template for all graphs but has the added function of interfacing with the user while the other agents are orchestrated by this main or central graph.  
- **Action**:
  - Use the existing directories `src/tools/` and `src/agents/`.
  - Move tool-related code to `src/tools/` and agent-related code to `src/agents/`.
- **Testing**:
  - Create `tests/test_tools.py` and `tests/test_agents.py` with:
    - **Success Case**: Ensure tools and agents perform their intended functions.
    - **Failure Case**: Test with missing or incorrect configurations.
    - **Edge Case**: Test with boundary values or unexpected inputs.

#### 3. LLM, Logging, and DB Services
- **Objective**: Organize LLM, logging, and database code into service modules.
- **Background**:  This is a standard way to organize code.  The LLM, logging, and database will be moved into their own respective services.  Additional LLM and database services will be added but local Ollama and Supabase services will remain primary.  
- **Action**:
  - Use the existing directories `src/services/llm_services/`, `src/services/logging_services/`, and `src/services/db_services/`.
  - Move LLM-related code to `src/services/llm_services/`, logging setup to `src/services/logging_services/`, and database management to `src/services/db_services/`.
- **Testing**:
  - Create `tests/test_llm.py`, `tests/test_logging.py`, and `tests/test_db.py` with:
    - **Success Case**: Verify that each service initializes and operates correctly.
    - **Failure Case**: Test with incorrect configurations or missing dependencies.
    - **Edge Case**: Test with large data sets or high concurrency.

#### 4. State Management and Graph Logic
- **Objective**: Refactor state management and graph logic for clarity.
- **Action**:
  - Create a directory `src/state/` for state management code.
  - Move state-related classes and functions to `src/state/`.
  - Ensure graph logic is clearly separated and resides in `src/graphs/`.
- **Testing**:
  - Create `tests/test_state.py` and `tests/test_graphs.py` with:
    - **Success Case**: Ensure state transitions and graph operations work as expected.
    - **Failure Case**: Test invalid state transitions or graph errors.
    - **Edge Case**: Test with complex state changes or graph cycles.

### General Testing Strategy
- **Continuous Integration**: Set up a CI pipeline to run tests automatically on each commit.
- **Test Coverage**: Aim for high test coverage to ensure all critical paths are tested.
- **Incremental Changes**: Move and test a few components at a time to minimize disruption.

This plan provides a structured approach to refactoring your codebase, ensuring that each component is modularized and tested thoroughly. Let me know if you need further details on any specific part of the plan!



Next steps:
- Key tools to integrate:
  - google tools, especially tasks
  - file system mcp
  - sub-graphs
  - personalities in orchestrator
  - clean up extra stuff in Basic_Orchestrator_Agent_Personality
  - more discrete tool files separation, needs discussion with AI
  - add more memory for prompts for Ollama 
  - implement a real UI - If it has to be event driven, add a dashboard for agent status with lights.
  - test mcp client
  - learn to chain tool and agent tasks for complex workflows and discussions. 
  - implement mem0 memories for me, Julie, Patrick, Rory, and the key agents.  
  - we were trying to implement brave search, but it is not launching the docker container.  The docker container tries to launch with port 8000 but KONG is already using that port.  We need to change the port to something else.  
  - Need to add a list of used ports to the project status.md file.
  

Get rid of dual request tracking system.  

CLI is event driven from the prompt.  We will need to change to use queues.  Otherwise everything stops.





***Build a plan to integrate scrapers into the orchestrator.***

Build a list of folders and files from craw4AI-agent-mod 
Compare that to what we probably need for the current project.  
Copy wholesale any code that we can use.  

## Scraper Integration Plan

### Overview
The plan is to integrate scrapers from the crawl4AI-agent-mod project into our orchestrator, focusing on repository scraping, documentation scraping, and vectorization for RAG operations.

### Required Components

#### 1. Database Schema
- Create the `repo_content` table with vector support for storing repository content
- Implement similarity search functions for querying the vector database
- Set up proper indexes for efficient querying

#### 2. Core Scraping Functionality
- Adapt the GitHub repository crawler for fetching and processing code repositories
- Implement documentation website crawler for technical documentation
- Create a common text processing module for chunking and preparing content

#### 3. Vector Embedding and Storage
- Implement embedding generation for code and documentation content
- Create a system for storing chunks with proper metadata in Supabase
- Build a querying interface for semantic search

#### 4. Integration with Orchestrator
- Connect scrapers as asynchronous tools in the orchestrator framework
- Implement progress tracking and completion notification
- Add error handling and retry mechanisms

### Implementation Steps

1. **Database Setup**
   - Execute the SQL script to create the `repo_content` table
   - Enable the pgvector extension for vector similarity search
   - Set up indexes and access policies

2. **Create Common Modules**
   - Implement text chunking and processing utilities
   - Create embeddings generation functionality
   - Build storage and retrieval mechanisms

3. **Tool Implementation**
   - Update `scrape_repo_tool.py` with GitHub API implementation
   - Enhance `scrape_docs_tool.py` with documentation crawling functionality
   - Improve `vectorize_and_store_tool.py` with actual vector processing

4. **Integration and Testing**
   - Connect tools to the orchestrator
   - Implement asynchronous operation with state tracking
   - Create comprehensive tests for each component

### Environment Requirements
- GitHub API token for repository access
- Supabase instance with pgvector extension enabled
- LLM access for generating embeddings and summaries

### crawl4AI-agent-mod Folder Structure
```
📁 crawl4AI-agent-mod/
│
├── 📄 DATA_STORAGE_STATUS.md     # Database storage documentation
├── 📄 .env                       # Environment configuration
├── 📄 PROJECT_STATUS.md          # Project status tracking
├── 📄 requirements.txt           # Python dependencies
├── 📄 README.md                  # Project documentation
├── 📄 REPOSITORY.md              # Repository documentation
├── 📄 API.md                     # API documentation
├── 📄 openapi.yaml               # OpenAPI specification
├── 📄 nginx.conf                 # Nginx configuration
├── 📄 .env.example               # Example environment configuration
├── 📄 .gitignore                 # Git ignore file
├── 📄 test.py                    # Test script
│
├── 📁 src/                       # Source code
│   ├── 📁 database/              # Database schema and utilities
│   │   ├── 📄 repo_content_table.sql    # Repository content table definition
│   │   ├── 📄 docs_site_pages_table.sql # Documentation pages table definition
│   │   └── 📄 [Other database files]    # Various table definitions
│   │
│   ├── 📁 crawler/               # Web crawling functionality
│   │   ├── 📁 common/            # Shared crawler utilities
│   │   ├── 📁 repos/             # Repository crawling
│   │   │   ├── 📄 __init__.py
│   │   │   └── 📄 github_crawler.py     # GitHub repository crawler
│   │   │
│   │   ├── 📁 docs/              # Documentation crawling
│   │   ├── 📁 social_media/      # Social media crawling
│   │   ├── 📁 media/             # Media content crawling
│   │   └── 📁 api/               # API crawling
│   │
│   ├── 📁 tools/                 # Tool implementations
│   │   ├── 📄 base_tool.py       # Base tool class
│   │   ├── 📄 tool_handler.py    # Tool handling and registration
│   │   └── 📄 pydantic_supabase_rag_tools.py   # RAG tool implementations
│   │
│   ├── 📁 agents/                # Agent implementations
│   ├── 📁 ui/                    # User interfaces
│   └── 📁 api/                   # API endpoints
│
├── 📁 sql/                       # SQL scripts
│   └── 📄 update_embedding_dimension.sql # Vector dimension update script
│
├── 📁 examples/                  # Example implementations
├── 📁 backup/                    # Backup files
├── 📁 .vscode/                   # VS Code configuration
├── 📁 studio-integration/        # Studio integration code
├── 📁 .venv/                     # Virtual environment
└── 📁 tests/                     # Test files
```

### Required Files to Copy/Adapt

1. **Database Schema**
   - `src/database/repo_content_table.sql` - Repository content table definition
   - `sql/update_embedding_dimension.sql` - Vector handling utilities

2. **Core Crawler Components**
   - `src/crawler/repos/github_crawler.py` - GitHub repository crawler
   - `src/crawler/common/text_processing.py` - Text chunking and processing

3. **Tool Implementations**
   - `src/tools/base_tool.py` - Base tool structure
   - `src/tools/tool_handler.py` - Tool registration and handling
   - `src/tools/pydantic_supabase_rag_tools.py` - RAG query tools

4. **Utility Components**
   - Environment configuration patterns from `.env.example`
   - Vector storage and retrieval mechanisms

### Immediate Next Steps

1. Execute SQL scripts to create the necessary tables in Supabase
2. Implement the text processing utilities in our codebase
3. Update our tool implementations with the actual scraping logic
4. Create tests to verify the scraping and vectorization functionality
5. Integrate with our existing orchestrator through the tool interface


| column_name            | data_type                | character_maximum_length | column_default                           | is_nullable |
| ---------------------- | ------------------------ | ------------------------ | ---------------------------------------- | ----------- |
| id                     | bigint                   |                          | nextval('repo_content_id_seq'::regclass) | NO          |
| repo_url               | text                     |                          |                                          | NO          |
| file_path              | text                     |                          |                                          | NO          |
| branch                 | text                     |                          |                                          | NO          |
| content                | text                     |                          |                                          | NO          |
| title                  | text                     |                          |                                          | NO          |
| summary                | text                     |                          |                                          | NO          |
| metadata               | jsonb                    |                          | '{}'::jsonb                              | NO          |
| embedding_nomic        | USER-DEFINED             |                          |                                          | NO          |
| embedding_model        | character varying        |                          |                                          | NO          |
| chunk_number           | integer                  |                          |                                          | NO          |
| document_creation_date | timestamp with time zone |                          |                                          | YES         |
| document_crawl_date    | timestamp with time zone |                          | timezone('utc'::text, now())             | NO          |
| created_at             | timestamp with time zone |                          | timezone('utc'::text, now())             | NO          |
| embedding_openai       | USER-DEFINED             |                          |                                          | YES         |



| column_name            | data_type                | character_maximum_length | column_default                                  | is_nullable |
| ---------------------- | ------------------------ | ------------------------ | ----------------------------------------------- | ----------- |
| id                     | bigint                   |                          | nextval('dev_docs_site_pages_id_seq'::regclass) | NO          |
| url                    | character varying        |                          |                                                 | NO          |
| chunk_number           | integer                  |                          |                                                 | NO          |
| title                  | character varying        |                          |                                                 | NO          |
| summary                | character varying        |                          |                                                 | NO          |
| content                | text                     |                          |                                                 | NO          |
| document_creation_date | timestamp with time zone |                          |                                                 | YES         |
| document_crawl_date    | timestamp with time zone |                          | timezone('utc'::text, now())                    | NO          |
| embedding_model        | character varying        |                          |                                                 | NO          |
| metadata               | jsonb                    |                          | (json_build_object('owner', 'Bob'))::jsonb      | NO          |
| embedding_nomic        | USER-DEFINED             |                          |                                                 | YES         |
| created_at             | timestamp with time zone |                          | timezone('utc'::text, now())                    | NO          |
| embedding_openai       | USER-DEFINED             |                          |                                                 | YES         |



| column_name      | data_type                | character_maximum_length | column_default                         | is_nullable |
| ---------------- | ------------------------ | ------------------------ | -------------------------------------- | ----------- |
| id               | bigint                   |                          | nextval('site_pages_id_seq'::regclass) | NO          |
| url              | character varying        |                          |                                        | NO          |
| chunk_number     | integer                  |                          |                                        | NO          |
| title            | character varying        |                          |                                        | NO          |
| summary          | character varying        |                          |                                        | NO          |
| content          | text                     |                          |                                        | NO          |
| metadata         | jsonb                    |                          | '{}'::jsonb                            | NO          |
| embedding_openai | USER-DEFINED             |                          |                                        | YES         |
| created_at       | timestamp with time zone |                          | timezone('utc'::text, now())           | NO          |
| embedding_nomic  | USER-DEFINED             |                          |                                        | YES         |



## MCP Integration Summary

### Components Implemented

1. **MCP Adapter Layer**:
   - `src/services/mcp_services/mcp_adapter.py`: Core MCPAdapter class for handling communication with MCP endpoints
   - Supports both local and remote MCP endpoints with async processing
   - Implements pending request tracking system

2. **Tool Integration**:
   - `src/tools/mcp_tools.py`: Dynamically registers MCP tools from configuration
   - Extended `execute_tool` and `check_completed_tool_requests` functions
   - Adds MCP tool definitions to the main tool registry

3. **Implementation Examples**:
   - `src/tools/git_tools.py`: Git operations through MCP interface
   - `src/services/db_services/query_service.py`: Database query service for MCP

4. **Package Structure**:
   - `src/services/mcp_services/__init__.py`: Package exports
   - `src/services/__init__.py`: Updated to import MCP services

### Usage

The orchestrator can now use MCP as a tool interface, with capabilities to:
1. Call remote MCP endpoints (like Brave Search) via API
2. Execute local MCP-formatted commands (Git operations and database queries)
3. Register additional MCP endpoints by updating the configuration

Users can interact with these tools through commands like:
- `mcp_brave_search_brave_web_search(task="Search for climate change solutions")`
- `mcp_git_git_status(task="Check the git status of the repository")`
- `mcp_postgres_query(task="SELECT * FROM conversations LIMIT 10")`

The implementation follows the same asynchronous pattern as existing tools, with background processing and status checking for non-blocking operation.

## Implementation of git web scrape and vectorization

Let's implement the text processing utilities for the scraper integration. According to the TODO.md file, we need to create common modules for text chunking, processing, and embedding generation. These utilities will be used by the scraper tools to process content from repositories and documentation sites before storing them in the vector database.
Based on the plan and folder structure, I need to:
- Create a common text processing module
- Implement chunking functionality
- Create utilities for generating titles and summaries
- Add embedding generation functionality

I'll create these in a structure similar to the crawl4AI-agent-mod project but adapted for our current codebase.


I'll implement the text processing utilities needed for the scraper integration. First, let's create the necessary directory structure and files.
Let's check if we already have utils directory contents:
Now I'll create the text processing utilities in the utils directory. First, let's create a text_processing.py file:
- cleans the text
- estimates the token count
- chunks the text
  Has chunking function, but does not use intelligents like otto text_processing.py - split by section function?
- generate chunk title
- generate chunk metadata

Now let's create an embedding utilities file:
  - find_similar_vectors function
  - This is a RAG function, so may not belong here.


Not sure why it went on to MCP, we dont' have docs yet
Let me now look at the MCP implementation:
Now, let's look for existing MCP code to understand the current implementation:
Let's check for utility files that might contain networking or API code:
Based on my investigation, I can now outline the implementation needed for adding MCP support. Let me create the MCP adapter layer:
  Adapter to interface with any (multiple) MCP endpoints.
- check_mcp_status function

Now, let's create a package init file for the MCP services: as described

Next, let's create a MCP tool wrapper to integrate with our existing tool system:
  file specifically for integration of MCP tools to orchestrator.
- register_mcp_tools function
Now, let's integrate the MCP tools with the orchestrator_tools.py file:
  Looked good with the exception of removing large block of previous code for agetnt tools.  Restored with commenting out.

Now let's update the check_completed_tool_requests function to check for MCP tools:
Let's complete the execute_tool function to handle the MCP tools properly:

Finally, let's create the init.py file for the services directory to ensure proper imports:

Let's create a simple example of a git tool using MCP:
  Looks like a complete array of tools, not sure what make it "simple"

Now, let's add a simple database query service for the MCP to use:
  Seems like duplicate functions to what we already have. 

I've now implemented a complete MCP adapter for the orchestrator system. Here's a summary of the changes made:
- MCP Adapter Layer:
  - Created src/services/mcp_services/mcp_adapter.py with an MCPAdapter class that handles communication with MCP endpoints
  - Added support for both local and remote MCP endpoints
  - Implemented asynchronous processing of MCP requests with background threads
  - Created a tracking system for pending MCP requests
- Tool Integration:
  - Created src/tools/mcp_tools.py to register MCP tools dynamically
  - Added support for MCP tool calls in the execute_tool function
  - Extended check_completed_tool_requests to check for completed MCP requests
  - Added MCP tool definitions to the TOOL_DEFINITIONS dictionary
- MCP Implementation Examples:
  - Created src/tools/git_tools.py for Git operations
  - Created src/services/db_services/query_service.py for database queries
  - Configured default MCP endpoints for Brave Search, Git, and Postgres
- Auxiliary Files:
  - Updated package __init__.py files to ensure proper imports
Now, the orchestrator can use MCP as a tool interface, with the ability to:
  - Call remote MCP endpoints (like Brave Search) via API
  - Execute local MCP-formatted commands (Git operations and database queries)
  - Register additional MCP endpoints by updating the configuration

Users can interact with these tools through the existing agent system, with new tool calls like:
  - mcp_brave_search_brave_web_search(task="Search for climate change solutions")
  - mcp_git_git_status(task="Check the git status of the repository")
  - mcp_postgres_query(task="SELECT * FROM conversations LIMIT 10")

The MCP implementation follows the same asynchronous pattern as the existing tools, with background processing and status checking for non-blocking operation.


===========================

## Restart on MCP integration

There will be two key parts to this process.  First is to confirm fully compliant MCP client within the orchestrator.  Second is to create a new MCP client using a template from https://github.com/coleam00/mcp-mem0

References: 
- https://github.com/coleam00/mcp-mem0
- https://modelcontextprotocol.io/introduction

To build servers in cursor:   DOCKER build highly recommended.  See ReadMe.md for details.
- prompt 
  """
  Use the mcp docs @mcp for reference and context.
  Use the Python MCP Server Template below as an example for the MCP server you are about to build.

  <paste in template code here>

  below code
  Now I want to build my own MCP server to integrate with Google Gmail... etc.  LightGraph is for knowledge graph rag and has cole medin video
  """
- Usual imports
- define the lifespan for the server.  This defines the resource like db or memory once for entire server project
    - mem0_lifespan
- define FastMCP Server with client
    - mcp = FastMCP(
      "mcp-name",
      description
      lifespan=name_lifespan,
      client=name_client
      HOST=
      PORT=
      API_KEY=
      API_KEY_NAME=
      API_KEY_IN=
      API_KEY_LOCATION=
      
    )
- define mcp tools
  - @mcp.tool()
    asynch def tool_name(ctx: Context, text: str) -> str:
          """ normal doc string
          One line what tool does

          More detailed description of tool.

          Args
          """
          try:
              blah blah
              return "result"
          except Exception as e:
              return f"Error: {e}"

  - @mcp.tool()
    asynch def tool2_name(ctx: Context, text: str) -> str:


    async def main()
      transport = os.getenv("TRANSPORT", "sse")  # Most technically difficult part of the code
          if transport == "sse":  # VERY FAST when server and client are on same machine.  N8N ONLY supports sse.
              # Run the server with SSE transport
              await mcp.run_stdio_async()
          else:
              # Run the server with stdio transport   
          await transport.run_stdio_async() # runs over network internal or external with http post style comms.



## MCP Integration Plan

### Overview
We will integrate the AI agent building functionality from archon into the orchestrator framework, using MCP for standardized tool communication. This will be done in two phases:

1. **Extract and Adapt Archon Components**
   - Agent building workflow from `archon_graph.py`
   - State management and validation system
   - LLM interaction patterns
   - Advisor and refinement agents

2. **Integration with Orchestrator Infrastructure**
   - State Management
   - LLM Services
   - Database Access
   - Logging System

### Implementation Phases

#### Phase 1: Core Structure
- Set up base graph structure using orchestrator's `StateGraph`
- Implement state models and validators
- Set up basic agent flow

#### Phase 2: Agent Components
- Port advisor agent
- Port refinement agents
- Port coder agent
- Adapt tool management system

#### Phase 3: Integration
- Connect to UI system
- Implement logging and monitoring
- Add error handling and recovery
- Set up state persistence

### Required Files Structure
```
src/
  graphs/
    agent_builder_graph.py      # Main agent building graph
    refinement_graph.py         # Refinement workflow
  agents/
    advisor/
    refiner/
    coder/
  state/
    agent_builder_state.py      # Specific state models for agent building
  tools/
    agent_building/            # Specialized tools for agent creation
```

### MCP Server Implementation

1. **MCP Server Setup**
   - Use template from https://github.com/coleam00/mcp-mem0
   - Follow modelcontextprotocol.io guidelines
   - Implement in Docker container

2. **Core Components**
   - Server lifespan management
   - FastMCP Server configuration
   - Tool definitions
   - Transport layer (SSE/stdio)

3. **Server Configuration**
```python
mcp = FastMCP(
    "agent-builder",
    description="AI Agent Building Service",
    lifespan=agent_builder_lifespan,
    client=agent_builder_client,
    HOST=config.HOST,
    PORT=config.PORT,
    API_KEY=config.API_KEY,
    API_KEY_NAME=config.API_KEY_NAME,
    API_KEY_IN=config.API_KEY_IN,
    API_KEY_LOCATION=config.API_KEY_LOCATION
)
```

4. **Tool Implementation Pattern**
```python
@mcp.tool()
async def build_agent(ctx: Context, spec: str) -> str:
    """
    Build an AI agent from specification.

    Detailed agent building logic using the archon framework.

    Args:
        ctx: Tool context
        spec: Agent specification
    """
    try:
        # Agent building logic
        return "Agent built successfully"
    except Exception as e:
        return f"Error: {e}"
```

5. **Transport Configuration**
- SSE for local/N8N integration
- stdio for network communication


==============================

## Orchestrator to Agent build.

---

## Agent-Orchestrator Modularization Plan & Checklist

### Goal
- The orchestrator should only know about the three agents: `valet`, `librarian`, and `personal_assistant`.
- It should not know about individual tools or their descriptions.
- Each agent manages its own tool registry and prompt section.

### Step 1: Refactor the Orchestrator to Route by Agent, Not Tool

**Checklist:**
- [x] Create/verify agent handler modules: `agent_valet.py`, `agent_librarian.py`, `agent_personal_assistant.py` (or similar).
    - [x] Create backup for @ai_agent.py
    - [x] Create BaseAgent
    - [x] Refactor ai_agent to use BaseAgent
    - [x] TEST - from CLI at least, but maybe from pytest as well.
    - [x] Refactor one of the agents (probably librarian) to use the base class.
    - [x] Add a canned response to librarian_tool and test orchestrator->librarian_tool call
    - [ ] Update librarian_tool to delegate to LibrarianAgent and test
    - [ ] Register RAG/crawl tools in LibrarianAgent and test end-to-end
    - [ ] Give librarian db RAG search tools and existing crawl tools.
    - [ ] TEST.
    - [ ] Refactor valet and personal_assistant
- [ ] Move tool registry and prompt logic into each agent handler.
- [ ] Refactor the orchestrator's main loop to:
    - Only route to agents, not tools.
    - Not include tool descriptions in its own prompt.
- [ ] Test that a user request like "tool librarian: research X" is routed to the librarian agent, which then selects and runs the correct tool.

**Once this is done:**
- Orchestrator: Knows only about agents.
- Each agent: Knows about its own tools and prompt logic.

---

Let's work through this checklist step by step!

## Agentic Orchestration & Tool Request/Response Flow

- [ ] Implement full agentic tool request/response flow:
    - [ ] Orchestrator creates and tracks request IDs and statuses for all tool calls
    - [ ] Orchestrator sends tool requests and updates status to 'pending' after agent acknowledges
    - [ ] Tool/agent acknowledges receipt of task and logs it with request ID
    - [ ] Agent sends its own prompt to the LLM and handles recursive tool requests as needed
    - [ ] All agent/tool messages are logged with metadata and request ID for traceability
    - [ ] When a tool/agent completes, the result is injected into the next LLM prompt with clear instructions to use ONLY that result
    - [ ] LLM can decide to make further tool requests or mark the request as complete
    - [ ] Orchestrator/agent sends the final answer to the user and updates status to 'complete'
    - [ ] Add robust error/timeout handling for long-running or failed tools (not just pending forever)
    - [ ] Provide user feedback/status updates while tools are pending (non-blocking UX)
    - [ ] Ensure agent-to-agent calls are only allowed in controlled, chained workflows (e.g., gather-then-compile), and are always tracked by the controlling agent for transparency
    - [ ] Test each step with canned responses and obvious requests before adding real tool/agent logic
    - [ ] Add comprehensive logging and metadata for all async tool/agent calls and results

# (Rest of your TODO list continues below...)

## AI Agent Refactoring Checklist

### Phase 1: Setup and Structural Preparation
- [x] Create backup of `ai_agent.py` (as `ai_agent0417.py.bak`)
- [x] Identify empty/unused directories to remove (`states/` removed, `db/` retained for database schemas)
- [x] Create necessary new directories:
  - [x] `src/ui/interfaces/` for interface implementations
  - [x] `src/ui/adapters/` for IO adapters

### Phase 2: Code Extraction and Modularization
- [x] Create core agent module (`src/agents/llm_query_agent.py`):
  - [x] Extract core `LLMQueryAgent` class
  - [x] Remove UI-specific code
  - [x] Focus on core orchestration and LLM interaction
  - [x] Simplify to maintain single responsibility
  
- [x] Create interface framework (`src/ui/interface.py`):
  - [x] Define abstract base classes for all interface types
  - [x] Extract common UI utilities
  - [x] Implement standard I/O formatting

- [x] Create interface implementations:
  - [x] `src/ui/cli.py` - Extract CLI-specific code
  - [ ] `src/ui/api_server.py` - For MCP connections
  - [ ] `src/ui/web.py` - For Streamlit/web integration
  - [ ] `src/ui/graph_adapter.py` - For sub-graph integration

- [x] Create I/O adapters (`src/ui/adapters/io_adapter.py`):
  - [x] Abstract non-blocking input (Windows/Unix)
  - [x] Extract terminal display utilities
  - [x] Create platform-specific handlers

- [x] Extract tool processing (`src/tools/tool_processor.py`):
  - [x] Move `process_completed_tool_request()`
  - [x] Create cleaner tool result processing
  - [x] Normalize response formats

### Phase 3: Main Application Entry Points
- [x] Create simple main module (`src/main.py`):
  - [x] Minimal dependencies
  - [x] Configuration loading
  - [x] Service initialization
  - [x] Interface selection
  
- [x] Create specific entry points:
  - [x] `src/run_cli.py` - CLI-specific launcher
  - [ ] `src/run_server.py` - Server mode launcher
  - [ ] `src/run_web.py` - Web UI launcher

### Phase 4: Testing and Documentation
- [x] Create unit tests for extracted components:
  - [x] Test core agent functionality
  - [x] Test each interface implementation
  - [x] Test tool processing
  - [x] Test I/O adapters
  
- [x] Update documentation:
  - [x] Add docstrings to all new modules
  - [x] Create README.md for each new directory
  - [x] Update main README with new structure

### Phase 5: Integration and Cleanup
- [ ] Integrate all components:
  - [ ] Test core agent with each interface
  - [ ] Verify tool processing works with all interfaces
  - [ ] Ensure state is properly maintained
  
- [ ] Clean up codebase:
  - [ ] Remove duplicate code
  - [ ] Standardize naming conventions
  - [ ] Review and update docstrings for consistency and completeness
  - [ ] Delete backup and unused files
  - [ ] Remove empty directories


  Next steps for cleanup might include:
Remove backup files: Files like ai_agent0417.py.bak and ai_agent0412.py.bak can likely be deleted since we've migrated their functionality.
Update documentation: Ensure README and docs reflect the new modular structure.
Update any import statements: Check if any other files are still importing from the old ai_agent.py and update them.
Review TODOs: Check for any TODOs in the code that should be addressed.
Check test coverage: Ensure tests cover the refactored code properly, particularly around the CLI interface and tool processing.

## Code Organization Recommendations

### Testing Infrastructure
- [ ] Move scattered test files (`test_*.py`) into the `tests/` directory
- [ ] Ensure test files mirror the main app structure
- [ ] Add test cases following the pattern: 1 expected use, 1 edge case, 1 failure case

### Documentation Organization
- [ ] Consider consolidating README files or creating a docs directory
- [ ] Update `TODO.md` to match the format specified in `PROJECT_STATUS.md`
- [ ] Review and update all docstrings to follow Google style

### Code Structure
- [ ] Move `models.py` into the `src/models/` directory
- [ ] Review root-level Python files for functionality that should be in `src/`
- [ ] Review `main.py` (201 lines) for potential modularization
- [ ] Consider moving `examples/` to top-level directory
- [ ] Review `services/` directory for potential further subdivision

### Development Environment
- [ ] Add type checking configuration (e.g., `mypy.ini`)
- [ ] Add pre-commit hooks for code formatting with black
- [ ] Review and update `requirements.txt` version constraints
- [ ] Consider adding development requirements file (`requirements-dev.txt`)

# Mem0 changes to meet their standards
## To align our implementation with Mem0's standard functions, we should:
- Update our memory service to use their hybrid storage approach
- Implement their standard memory operations interface
- Add memory extraction using LLMs
- Enhance our vector search with their scoring system
- Add proper metadata handling for better context

## Mem0 Hybrid Storage Upgrade

### Infrastructure Impact Checklist
- [ ] Add Neo4j for graph storage
- [x] ~~Add Redis for key-value storage~~ (Will add later if needed for performance optimization)
- [ ] Update deployment configurations
- [ ] Update documentation
- [ ] Update integration tests

### Required Changes for Hybrid Storage

#### 1. Storage Layer Configuration
- [ ] Update Mem0 configuration to version v1.1
- [ ] Configure vector store (pgvector)
- [ ] Configure graph store (Neo4j)
- [x] ~~Configure key-value store (Redis)~~ (Will use Supabase for now, Redis can be added later for performance)
- [ ] Update environment variables
- [ ] Optimize supabase
```sql
# Use efficient indexing
CREATE INDEX idx_memories_vector ON memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

# Use materialized views for frequently accessed data
CREATE MATERIALIZED VIEW recent_memories AS
SELECT * FROM memories 
WHERE created_at > NOW() - INTERVAL '24 hours';
```

#### 2. Memory Processing Updates
- [ ] Enhance memory addition with fact extraction
- [ ] Implement relationship tracking
- [ ] Update metadata handling
- [ ] Add timestamp tracking
- [ ] Implement memory versioning
- [ ] Implement memory caching in python
```python
from functools import lru_cache

class MemoryService:
    @lru_cache(maxsize=1000)
    def get_memory(self, memory_id: str):
        return self.supabase.table('memories').select('*').eq('id', memory_id).execute()
```

#### 3. Search and Retrieval Updates
- [ ] Implement vector search for semantic similarity
- [ ] Add graph search for related memories
- [ ] Create result merging and ranking system
- [ ] Update context generation
- [ ] Add memory scoring system

#### 4. Database Schema Updates
- [ ] Create new tables/collections for relationships
- [ ] Update existing memory tables
- [ ] Create migration scripts
- [ ] Add indices for performance
- [ ] Update backup procedures

#### 5. Service Integration Updates
- [ ] Update CLI interface
- [ ] Update agent interfaces
- [ ] Update MCP adapters
- [ ] Add new environment variables
- [ ] Update service dependencies

#### 6. Testing Updates
- [ ] Create tests for graph features
- [ ] Create tests for key-value features
- [ ] Update existing memory tests
- [ ] Add integration tests
- [ ] Update CI/CD pipeline

### Dependencies to Add
```requirements
# Add to requirements.txt or equivalent
neo4j-driver==5.x
redis==5.x  # not needed for now
pgvector==0.2.x
```

### Environment Variables to Add
```env
# Neo4j Configuration
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Vector Store Configuration
PGVECTOR_CONNECTION=postgresql://user:pass@localhost:5432/dbname
```

### Docker Services to Add
```yaml
# Add to docker-compose.yml
services:
  neo4j:
    image: neo4j:5
    ports:
      - "7687:7687"
      - "7474:7474"
    environment:
      NEO4J_AUTH: neo4j/your_password
    volumes:
      # Mount external volume for persistent data storage
      - ./data/neo4j:/data  # Store Neo4j data in local ./data/neo4j directory
      - ./logs/neo4j:/logs  # Store Neo4j logs in local ./logs/neo4j directory
    restart: unless-stopped  # Ensure container restarts automatically
```

**Note**: Neo4j data will be stored in an external volume (./data/neo4j) to ensure persistence across container rebuilds, similar to our Supabase implementation. This prevents data loss during container updates or system restarts.



# Mem0 storage layer updates

```python
mem0_config = {
    "version": "v1.1",  # Required for hybrid storage
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "connection_string": os.environ.get('DATABASE_URL'),
            "collection_name": "memories",
            "embedding_model_dims": 1536  # For OpenAI embeddings
        }
    },
    "graph_store": {
        "provider": "neo4j",
        "config": {
            "url": os.environ.get('NEO4J_URL'),
            "username": os.environ.get('NEO4J_USER'),
            "password": os.environ.get('NEO4J_PASSWORD')
        }
    },
    "key_value_store": {
        "provider": "redis",
        "config": {
            "url": os.environ.get('REDIS_URL')
        }
    }
}
```

# Mem0 memory processing updates

```python
def add_memory(self, content: Union[str, List[Dict]], user_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Enhanced memory addition with fact extraction and relationship tracking."""
    try:
        # Extract facts using LLM
        facts = self.memory.extract_facts(content)
        
        # Add metadata
        full_metadata = {
            **(metadata or {}),
            "extracted_facts": facts,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in hybrid system
        result = self.memory.add(
            content,
            user_id=user_id,
            metadata=full_metadata
        )
        
        return {
            "success": True,
            "memory_id": result["id"],
            "extracted_facts": facts
        }
    except Exception as e:
        logger.error(f"Error storing memory: {e}")
        return {"success": False, "error": str(e)}
```

# Mem0 search and retrieval updates

```python
def search_memories(self, query: str, user_id: str, limit: int = 5) -> Dict[str, Any]:
    """Enhanced search across all storage types."""
    try:
        # Vector search for semantic similarity
        vector_results = self.memory.search(
            query,
            user_id=user_id,
            limit=limit
        )
        
        # Graph search for related memories
        graph_results = self.memory.graph_search(
            query,
            user_id=user_id,
            limit=limit
        )
        
        # Combine and rank results
        all_results = self._merge_and_rank_results(
            vector_results,
            graph_results,
            limit=limit
        )
        
        return {
            "success": True,
            "results": all_results
        }
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        return {"success": False, "error": str(e)}



```

## Plug-and-Play Tool Wrapper Architecture

### Checklist for Tool-as-Wrapper Pattern
- [x] For each agent/sub-graph, create a tool wrapper file in `src/tools/` (e.g., `personal_assistant.py`).
- [x] The tool wrapper must:
    - [x] Contain a class (e.g., `PersonalAssistantTool`) with a uniform `execute` method.
    - [x] Contain tool description and prompt as class variables or properties.
    - [x] Import and delegate to the sub-graph/agent as needed.
    - [x] (Optional) Provide a registration function for auto-discovery.
- [x] The orchestrator must only interact with the tool interface, not sub-graph internals.
- [x] To add a new agent:
    - [x] Drop the sub-graph folder in place.
    - [x] Add the tool wrapper file in `src/tools/`.
    - [x] Register the tool (import or via registry).
    - [x] Done.
- [ ] Update documentation and tests to reflect the new pattern.

---

Next step: Update documentation and tests, then prepare to test orchestrator.



## Import & Linter Error Fix Checklist (src/)

### 1. src/agents/orchestrator_agent.py
- [x] Import MessageRole from src.state.state_models (already fixed).
- [x] If you use StateManager or Message, import from src.state.state_manager and src.state.state_models respectively, not from src.graphs.orchestrator_graph.
- [x] Ensure all agent classes referenced in self.agent_classes are defined and imported correctly.

### 2. src/agents/llm_query_agent.py
- [x] Confirm src/services/db_services/db_manager.py exists and exports TaskStatus, MessageRole, etc.
- [x] Confirm all functions imported from src.tools.orchestrator_tools exist.
- [x] Confirm format_completed_tools_prompt exists (in src.tools.orchestrator_tools and src.state.state_manager, not src.graphs.orchestrator_graph).
- [x] Check for any undefined names or missing imports.

### 3. src/managers/db_manager.py
- [x] Change from src.serFvices.llm_services.llm_service import LLMService to the correct path if needed (should be src/services/llm_service.py).
- [x] Change from src.services.db_services.message_manager import MessageManager to the correct path if needed (should be src/services/message_service.py or similar).
- [x] Confirm all functions from src.utils.datetime_utils exist.
- [x] Ensure enums/constants like TaskStatus, MessageRole are not duplicated elsewhere.

### 4. src/managers/session_manager.py
- [x] Change from src.services.db_manager import DatabaseManager to from src.managers.db_manager import DatabaseManager.
- [x] Confirm now exists in src.utils.datetime_utils.
- [x] Use MessageRole from src.state.state_models.

### 5. src/sub_graph_personal_assistant/graphs/personal_assistant_graph.py
- [x] Change from src.services.logging_services.logging_service import get_logger to from src.services.logging_service import get_logger.
- [x] Import MessageRole from src.state.state_models if used.

### 6. src/sub_graph_personal_assistant/tools/google/gmail_tool.py
- [x] Confirm credentials_handler.py, google_tool_base.py, and credentials.py exist in the same directory (credentials_handler.py not needed; credentials.py provides the required logic).
- [x] Remove or fix fallback import (e.g., from tools.credentials_handler import get_credentials)
- [x] Ensure all referenced functions/classes are defined.


### 7. src/tools/graph_integration.py
- [x] If you use StateManager, Message, or MessageRole, import from src.state.state_manager and src.state.state_models instead of src.graphs.orchestrator_graph.

### 8. src/sub_graph_personal_assistant/agents/personal_assistant_agent.py
- [x] Confirm all imports exist and are correct.
- [x] Ensure all referenced classes/functions are defined.

### 9. General
- [x] Remove or update any import paths referencing logging_services, db_services, or other legacy/moved modules.
- [x] Implement all abstract methods in subclasses of ABCs.
- [ ] Remove unused files and dead code. (Move unused files to other_files_future_use, delete unused code.)
- [ ] Run a linter and/or pytest to catch any remaining issues.

# TODO: Refactor CLI Session Management to Use SessionManager

## Checklist

### 1. Identify All Custom Session Logic in CLI
- [x] List all methods in `CLIInterface` (and related code) that:
    - List previous sessions
    - Start new sessions
    - Resume/continue sessions
    - Search sessions
    - Store/retrieve session metadata
- **Notes/Findings:**
    - Custom session logic is implemented in the following methods in `CLIInterface`:
      - `_get_recent_sessions(self)`
      - `_handle_session_start(self)`
      - `_search_sessions(self)`
      - `_continue_session(self, session_id)`
      - `_start_new_session(self)`
    - These methods interact directly with the agent's `db` attribute for session listing, creation, and resumption.
    - Session metadata (name, timestamps, etc.) is managed and displayed in the CLI, not via `SessionManager`.
    - The CLI tracks the current session with `self.current_session_id` and `self.session_name`.
    - User is prompted at startup to select, search, or create sessions.
    - All session state and metadata handling should be migrated to use `SessionManager` methods for:
      - Listing sessions
      - Searching/filtering sessions
      - Creating new sessions
      - Resuming previous sessions
      - Accessing and displaying session metadata

---

### 2. Review `SessionManager` API
- [x] Review the methods provided by `SessionManager` (e.g., `list_sessions`, `start_session`, `restore_session`, `get_session_metadata`, etc.).
- [x] Ensure it provides all the functionality needed for the CLI. If not, extend `SessionManager` as needed.
- **Notes/Findings:**
    - **SessionManager Methods:**
        - `create_session(name)`: Create a new session (async)
        - `restore_session(session_id)`: Restore a previous session (async)
        - `get_recent_sessions(limit)`: List recent sessions (async)
        - `search_sessions(query)`: Search sessions by query (async)
        - `rename_session(new_name)`: Rename the current session (async)
        - `end_session()`: End the current session (async)
        - `has_active_session`: Property to check if a session is active
    - **Features Provided:**
        - All core session management features needed by the CLI are present:
            - Listing sessions
            - Creating new sessions
            - Resuming/restoring sessions
            - Searching sessions
            - Renaming sessions
            - Ending sessions
            - Checking for active session
        - Methods are async, so CLI will need to await them.
    - **Potential Gaps/Needed Changes:**
        - Ensure CLI uses these methods instead of direct DB access.
        - If CLI needs to access session metadata (name, timestamps, etc.), it should use the results from `get_recent_sessions`, `search_sessions`, or `restore_session`.
        - If CLI needs to display more detailed session info, may need to extend the metadata returned by these methods.
        - If CLI needs to handle session selection by index (as in the UI), ensure session lists are ordered and indexed consistently.
    - **No major missing features identified.**

---

### 3. Refactor CLI to Use `SessionManager`
- [x] Replace all direct DB or agent session logic in `CLIInterface` with calls to `SessionManager`.
    - For listing sessions: use `SessionManager.get_recent_sessions()`.
    - For starting a new session: use `SessionManager.create_session()`.
    - For resuming a session: use `SessionManager.restore_session(session_id)`.
    - For searching: use `SessionManager.search_sessions()`.
- **Notes/Findings:**
    - The following methods in `CLIInterface` were refactored to use `SessionManager`:
        - `_get_recent_sessions(self)` now uses `await self.session_manager.get_recent_sessions()`
        - `_handle_session_start(self)` now uses only `SessionManager` for session logic
        - `_search_sessions(self)` now uses `await self.session_manager.search_sessions(query)`
        - `_continue_session(self, session_id)` now uses `await self.session_manager.restore_session(session_id)`
        - `_start_new_session(self)` now uses `await self.session_manager.create_session(name)`
    - All direct use of `self.db` for session management in CLI was removed.
    - All session metadata (name, timestamps, etc.) is now accessed via `SessionManager`.
    - The CLI's session state (`session_name`, `current_session_id`) is now synced with `SessionManager`.
    - The CLI constructor and startup sequence were updated to support this refactor.
    - **Code changes have been made.**

---

### 4. Update CLI Constructor
- [x] Update `CLIInterface.__init__` to accept and store a `session_manager` argument.
- [x] Remove any direct DB/session logic from the CLI that is now handled by `SessionManager`.
- **Notes/Findings:**
    - The CLI constructor now takes `session_manager` as an argument and stores it as an attribute.
    - All session management is now handled through `SessionManager`.
    - No direct DB/session logic remains in the CLI.

---

### 5. Update Startup Sequence
- [x] In `main.py`, ensure `SessionManager` is created and passed to `CLIInterface`.
- [x] Remove any redundant or duplicate session logic from the CLI startup.
- **Notes/Findings:**
    - The startup sequence now creates a `SessionManager` and passes it to the CLI interface.
    - All session management is now handled by `SessionManager`; no direct DB/session logic remains in the CLI.
    - The CLI and SessionManager session state are now always in sync.
    - The codebase is cleaner and more modular, with session logic centralized.

### 5.1. Database Layer Refactoring (DBManager vs DBService)
- [x] Review all database operations in both `DatabaseManager` and `DatabaseService`.
- [x] Clarify DatabaseService is a pure stateless async API for supabase operations
- [x] Clarify DatabaseManager should focus on coordination, using DatabaseService for actual operations
- [x] Update method signatures for consistency (all async in `DatabaseService`).
- [x] Refactor for consistency:
    - [x] Make all DatabaseService methods async
    - [x] Have DatabaseManager use DatabaseService for all core operations
    - [x] Move complex business logic to DatabaseManager
- [x] Consolidate duplicate functionality and clarify which class is used where.
- [x] Document the specific responsibilities of each class.
- [ ] Missing functionality:
    - [ ] Vector search capabilities for semantic search
    - [ ] Graph search capabilities for relationship similarity search
    - [ ] Bulk operations for efficiency
    - [ ] Migration utilities for schema changes
    - [x] Health checks and diagnostics methods
- [x] Implementation plan:
    - [x] Update DatabaseService to be purely stateless with minimal state
    - [x] Refactor DatabaseManager to use DatabaseService for all DB operations
    - [x] Update callers to use the appropriate class based on their needs
- [x] Update README and docs to reflect the new modular structure.
- **Notes/Findings:**
    - Refactored DatabaseManager now follows a clear component-based architecture:
      - DatabaseService: Stateless service for low-level database operations
      - Component Managers: Domain-specific managers (MessageManagerDB, ConversationManagerDB)
      - DatabaseManager: High-level coordinator using composition
    - Created proper documentation in docs/database_architecture.md with architecture diagram
    - Added comprehensive unit tests in tests/test_db_manager_refactored.py
    - Implemented proper error handling at all levels of the architecture
    - Added consistent type conversion (string/int ID handling)
    - Added a search_messages method to the DatabaseManager API
    - Updated error handling in ConversationManagerDB to check existence before updates/deletes
    - Added both operations success verification for delete_conversation
    - Updated README.md with a section about the database architecture
    - The architecture now follows clean code principles:
      - Clear separation of concerns
      - Composition over inheritance
      - Better testability
      - Consistent error handling

### Phase 5.2: Session and State Management Integration
- [ ] Ensure SessionManager properly interacts with both DatabaseManager and agent state
- [ ] Test session persistence across application restarts
- [ ] Verify message history is properly restored in existing sessions

### Phase 5.3: Final Testing and Documentation
- [ ] Test the following flows with the updated architecture:
    - Listing previous sessions
    - Starting a new session
    - Resuming a previous session
    - Searching for sessions
    - Handling session metadata (names, timestamps, etc.)
- [ ] Document the refined architecture in the project documentation

This approach keeps the separation between services and managers while clarifying their roles and reducing duplication.

### 6. Test All Session Features
- [ ] Test the following flows:
    - Listing previous sessions
    - Starting a new session
    - Resuming a previous session
    - Searching for sessions
    - Handling session metadata (names, timestamps, etc.)
- [ ] Ensure all session state is consistent and persists as expected.
- **Test Results:**
    - _Record test results and any issues found._
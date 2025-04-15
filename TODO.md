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
- [ ] Create/verify agent handler modules: `agent_valet.py`, `agent_librarian.py`, `agent_personal_assistant.py` (or similar).
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

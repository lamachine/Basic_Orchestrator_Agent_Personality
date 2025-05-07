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

The system has three main components:

1. **Tool Registry**: Discovers, validates, and loads tools
2. **Tool Interface**: Standardized communication between orchestrator and tools
3. **Tool Implementation**: Individual tool functionality

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
    .env, requirements.txt, README.md, LICENSE, gitignore etc.
    /logs
    /tests
    <toolname>_tool.py  # Pydantic model for parent graph
    /src
        /agents                       # Business logic
        /config                       # Configuration files
            tool_config.yaml          # Tool registry info
            <tool>_config.yaml        # Tool-specific config
        /db
        /graphs
        /managers
        /services
        /state
        /sub_graphs                   # Sub-tools this tool may use
        /tools                        # Tool implementations
        /ui                           # Connection points to user or parent graph
        /utils
        main.py
```

### Key Files

- **Root-Level Tool Interface**: A Pydantic model that parent graphs use to interact with the tool
- **Config Files**: Tool configuration, capabilities, and metadata
- **UI Components**: Connection points for parent graphs to communicate with the tool
- **Tool Implementations**: Actual functionality the tool provides

## Tool Registry System

The Tool Registry provides a simple, file-based system for discovering, loading, and managing tools.

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

## Standard Message Format

Tools use standardized message formats for communication:
- This needs work.  It does not match the messaging format of the orchestrator.

```python
{
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
      "type": "error",
      "error_code": "ERROR_TYPE",
      "message": "human readable error",
      "details": {},  # Detailed error info
      "recoverable": boolean,
      "retry_strategy": "retry_pattern"
  }
  ```

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

## Implementation Checklist (Outline Format)

I. Inventory: What to Review
    A. All files in any `personal_assistant` folders
        1. [x] Main: `src/sub_graphs/personal_assistant_agent/`
        2. [x] Tests: `tests/test_personal_assistant_agent.py`
        3. [x] Old refs: `src/sub_graph_personal_assistant` (commented out)
    B. All files in `src/config/`
        1. [x] `nodes_and_tools_config.yaml`: Lists enabled tools
        2. [x] `user_config.py`: Contains tool configuration
    C. Any tool registration, tool processor, or orchestrator logic that references tools
        1. [x] `src/tools/orchestrator_tools.py`
        2. [x] `src/tools/initialize_tools.py`
        3. [x] `src/tools/graph_integration.py`
        4. [x] (Direct references: nodes_and_tools_config.yaml, user_config.py, graph_integration.py, initialize_tools.py, orchestrator_tools.py)

II. Implementing the First Tool (`personal_assistant`)

    A. Directory Structure & Consolidation
        1. [x] Create proper directory structure in `src/sub_graphs/personal_assistant_agent/`
        2. [x] Move existing files to correct locations
            a. [x] Tool agent main directory with key files
            b. [x] Nested `src` directory with standard folder structure
        3. [x] Clean up any duplicates or stubs during move
        4. [x] Update imports to reflect new structure
        5. [x] Verify no files are left in incorrect locations

    B. Clean Up Orchestrator Tool References
        1. [x] Review and update tool references in `nodes_and_tools_config.yaml`
        2. [x] Update tool references in `user_config.py`
        3. [x] Clean up tool imports and references in `graph_integration.py`
        4. [x] Refactor `initialize_tools.py` to use dynamic tool discovery
        5. [x] Update `orchestrator_tools.py` to use tool registry instead of direct imports

    C. Create Standardized Tool Interface
        1. [x] Create basic tool configuration in `src/sub_graphs/personal_assistant_agent/src/config/tool_config.yaml`
        2. [x] Create simple tool handler in `src/sub_graphs/personal_assistant_agent/src/tools/personal_assistant_tool.py`
        3. [x] Build consistent agent-to-tool communication interface
            a. [x] Create a standard Pydantic model at the root level that functions as the tool interface for the 'parent' graph
            b. [x] Move CLI message passing interface components to appropriate locations
                i. [x] Move sub_graph_interface.py to the CLI folder
                ii. [x] Ensure agent implementation is in sub-graph/src/agents/
                iii. [x] Confirm tool implementation is in sub-graph/src/tools/
            c. [x] Implement simple message passing with standardized format

IIb. CLI and Orchestrator Integration with Tool Registry (missed in above list)
    Note: These steps are required before further testing, as the previous test failed due to missing CLI integration.

    A. Patch CLI to use the tool registry for tool listing
        1. [x] Add 'tools' and 'list tools' commands to CLI to display available/approved tools from the registry
        2. [n] (Optional) Add CLI command to invoke a tool directly by name and task
    B. Review orchestrator entrypoint and agent logic to ensure all tool listing/invocation uses the registry, not hardcoded lists
        1. [x] Confirm orchestrator agent uses registry for tool discovery and invocation
        2. [x] (Optional) Add/expand tests to ensure CLI and orchestrator use the registry and tool listing is DRY
    C. Check the cannonical tool interface
        1. [x] Ensure it is personal_assistant_tool.py, not personal_assistant_api.py
        2. [x] Ensure it is importable and implements the required interface
    D. Check test code
        1. [x]  Ensure it imports and uses the tool via the registry, not by direct import.
        2. [x]  Ensure it is using personal_assistant_tool.py, not personal_assistant_api.py
        3. [x]  Tests should validate that the orchestrator and cli use the registry
        4. [x]  Tests should validate that the tool can be discovered, loaded, and called.

    F. Orchestrator Tool Call Flow
        1. [x] Ensure orchestrator injects tool prompt info and parses/executes tool calls in responses
        2. [x] Ensure orchestrator logs and persists user, system, assistant, and tool messages
        3. [x] Ensure orchestrator handles tool call results, errors, and propagates them to the user
        4. [ ] (Move this step after sub-graph implementation) Ensure orchestrator can handle tool hierarchies (e.g., personal_assistant calling sub-tools)
            - [ ] Complete after first sub-graph is functional and integrated
        5. [ ] (Removed as standalone; see checklist intro note)
        6. [ ] Add the logic for the orchestrator to evaluate tool replies against the original user request.
        7. [ ] Add the logic for the llm to request additional information if an answer is not complete.

    E. Tool Interface and Importability
        1. [x] Ensure the canonical tool interface is personal_assistant_tool.py, not personal_assistant_api.py.
        2. [x] Ensure the tool interface is importable and implements the required async execute method.
        3. [x] Add a test that imports the tool via the registry and checks for the correct interface.

II continued
    D. Test Core Functionality
        1. [ ] Test tool discovery and registration
            a. [x] Verify orchestrator can discover personal_assistant_agent through registry
            b. [x] Confirm configuration is properly loaded
            c. [ ] Test tool approval workflow (auto and manual)
        2. [x] Test minimal communication path
            a. [x] Test basic message routing from orchestrator to tool
            b. [x] Verify simple responses return correctly
            c. [x] Confirm standard message format is maintained
        3. [x] Validate modular structure
            a. [x] Confirm orchestrator is unaware of tool implementation details
            b. [x] Verify tool can respond without full implementation
            c. [x] Test that tool interface abstracts underlying complexity

    E. Expand Implementation
        1. [ ] Complete file structure standardization
            a. [ ] Finalize root-level Pydantic tool interface
            b. [ ] Organize configuration files properly
            c. [ ] Set up proper UI connection points
        2. [ ] Implement state management
            a. [ ] Add proper state persistence
            b. [ ] Implement conversation history tracking
            c. [ ] Test state restoration after restart
        3. [ ] Add error handling and logging
            a. [ ] Implement standardized error responses
            b. [ ] Set up comprehensive logging
            c. [ ] Test recovery from various failure scenarios
        4. [ ] Validate communications
            a. [ ] Confim that the tool passes messages to the sub-graph in the proper json format.
            b. [ ] Try to finalize list of standard messages to pass.  Base on MCP, but modify as needed due to state message efficiency vs. stand-alone complete tool. 

    F. Implement Minimal Real Functionality
        1. [ ] Add one simple but real capability to personal_assistant
            a. [ ] Implement basic task list functionality directly in the tool
            b. [ ] Add task creation, reading, and basic management features
            c. [ ] Focus on minimal viable implementation
            d. [ ] Test end-to-end flow with real data

    G. Expand to Multiple Tools
        1. [ ] Duplicate structure for Librarian agent
            a. [ ] Copy standard file structure from personal_assistant
            b. [ ] Implement one simple search capability
            c. [ ] Verify discovery and communication work identically
        2. [ ] Test dynamic loading/unloading
            a. [ ] Test removing and adding tools at runtime
            b. [ ] Verify correct behavior when tools are unavailable
            c. [ ] Test multiple tools working together

    H. Natural Tool Integration
        1. [ ] Implement natural language tool routing
            a. [ ] Create prompts for orchestrator to recognize tool needs
            b. [ ] Implement standard patterns for tool invocation
            c. [ ] Test with various user requests

    I. Transition to Sub-Agent Structure
        1. [ ] Remove direct task list implementation from personal_assistant
        2. [ ] Create separate task_agent with standard structure
            a. [ ] Implement task functionality in this dedicated agent
            b. [ ] Configure personal_assistant to use task_agent as a sub-tool
        3. [ ] Add email_agent as another sub-tool
            a. [ ] Implement basic email functionality
            b. [ ] Configure personal_assistant to route email requests appropriately
        4. [ ] Verify hierarchical routing works correctly
            a. [ ] Test that orchestrator → personal_assistant → task_agent path works
            b. [ ] Confirm orchestrator remains unaware of sub-agent details
            c. [ ] Verify personal_assistant correctly abstracts its sub-tools

# Discovered During Work
- [ ] Ensure all sender/target values in logging use the <graph_name>.<node> format for all agents and sub-graphs
- [ ] Confirm all tool completions are logged and embedded correctly after async fix
- [ ] Review and refactor any remaining legacy API or UI-named files

## Graph Communication Paradigm

All communications between graphs will come down through tools, and be handled by one of the following interfaces:
- `sub_graph_interface.py`: Uses message passing for graph-to-graph communication (default for initial development)
- `api_interface.py`: Handles web-based interactions (e.g., MCP)
- `cli_interface.py`: Enables direct terminal-based interface for stand-alone tool/graph deployment

Initial development will use the sub_graph paradigm with message passing, leveraging all existing orchestrator infrastructure.
==================



# Key File Mapping: Orchestrator vs. Personal Assistant Agent (One per line)
- Format: Orchestrator (src/)  -->  Personal Assistant Agent (sub_graphs/personal_assistant_agent/src/)
- File review checklist:
  - In master (orchestrator), is the code "as simple as possible, but no simpler?"
  - In master, is the code zen?
  - In master, is there graph-function specific code (i.e. orchestrator_only) that could be moved to another file to make a cleaner master template?
- After satisfactory review, create a clean template file for template_agent
- In personal_assistant_agent, is there graph-function specific code (i.e. personal_assistant_only) that could be moved to another file to make a cleaner match to the template?
- Update to proper file names and reference names for the personal_assistant_agent (variable name?)


agents/orchestrator_agent.py
    --> agents/personal_assistant_agent.py
    1. Simplicity & Zen
    Simplicity: The class is focused: it coordinates user requests, LLM chat, and tool calls. No unnecessary logic.
    Zen: Clear separation of concerns. Tool logic is delegated, not embedded. Personality is optional and modular.
    2. Graph-Function Specific Code
    orchestrator_only:
    The use of self.graph_name and logging with orchestrator-specific sender/target is graph-specific.
    The prompt includes orchestrator-specific context (time, location, system prompt).
    Tool call routing is generic, but the logging and naming are orchestrator-centric.
    What could be moved to a template?
    The base agent logic (history, prompt creation, LLM query) is generic and could be in a template.
    The tool call extraction and async handling are also generic and could be abstracted.
    The only truly orchestrator-specific parts are the default names, logging sender/target, and maybe the system prompt.
    3. Modularity
    The agent is modular: personality, tool logic, and LLM are all pluggable.
    Stubs for future tool/personality logic are present but commented out.
    4. What to Template?
    The following could be moved to a template agent:
    The async message processing pattern (with tool call detection and async execution).
    The conversation history and prompt creation logic.
    The logging pattern, with sender/target as variables.
    The structure for optional personality injection.
    The template should use generic names (e.g., self.graph_name, self.agent_name) and allow subclasses to override context, system prompt, and logging details.
    Conclusion:
    This file is a good candidate for a master template. The only orchestrator-specific code is in naming and logging. The rest is generic and can be parameterized for sub-graph agents.
    Next step suggestion:
    Extract a generic version of this class for template_agent, replacing orchestrator-specific names with placeholders or variables.
    Add a dummy tool call handler for template testing.



config/graph_config.py (created)
    --> config/personal_assistant_config.py renamed to graph_config.py

  working notes
      What make the orchestrator unique? goes in graph_config.py

      LLM configs - conversation Y, reasoning N, tools Y, encoding Y

      Database configs - sql Y, vector Y, state N, knowledge_graph N

      conversation Y,
      personality Y,

      System prompt.

      What do all tool agent graphs have?

      conversation_config or hooks
          personality_config (only if using conversation_config)

      LLM - options are use parent, use local (ollama in our case), or use remote (openrouter.ai) goes in llm_config.py

      Database - options are use parent, use local (supabase in our case), or use remote (supabase web) do we need graph_config.py?

      State - tie into parent, tie into local functions, or stand alone (i.e. MCP)

      Logging config seems unique to me, including db schema.  what do we do with this?
          
      User_config, use parent, or use local  (need this for line level security)

graphs/orchestrator_graph.py
    --> graphs/personal_assistant_graph.py

tools/orchestrator_tools.py
    --> tools/personal_assistant_tool.py

tools/initialize_tools.py
    --> tools/personal_assistant_tool.py (init logic inside class)

config/user_config.py
    --> config/tool_config.yaml

config/nodes_and_tools_config.yaml
    --> config/config.py

state/state_manager.py
    --> state/ (if present, or uses orchestrator's)

state/state_models.py
    --> state/ (if present, or uses orchestrator's)

managers/db_manager.py
    --> managers/ (if present, or uses orchestrator's)

managers/session_manager.py
    --> managers/ (if present, or uses orchestrator's)

services/llm_service.py
    --> services/ (if present, or uses orchestrator's)

services/message_service.py
    --> services/ (if present, or uses orchestrator's)

tools/tool_utils.py
    --> tools/ (if present, or uses orchestrator's)

tools/graph_integration.py
    --> tools/ (if present, or uses orchestrator's)

ui/cli.py
    --> cli/sub_graph_interface.py

ui/base_interface.py
    --> ui/ (if present)

tests/test_orchestrator_tools.py
    --> tests/test_personal_assistant.py

# For any file not present in the sub-graph, the orchestrator's version is used by default.
# As sub-graphs mature, they should implement their own versions as needed for modularity.




1. What Every Graph Needs (Generic/Template)
graph_name: Unique name for the graph/agent (from config).
system_prompt: Default system prompt (from config).
llm_config: How to access LLM (parent, local, remote).
db_config: How to access DB (parent, local, remote).
state_config: State management (parent, local, stand-alone).
logging_config: Logging level, file, etc.
user_config: User/role/line-level security (parent/local).
tool_registry_config: How to discover/approve tools.  --NO.  Tool registry is a core function of all the graphs.
These should be in a generic config class (e.g., GraphConfig), with sensible defaults and the ability to override via env or file.  -- That was my thought, but is this getting too complex?  Perhaps different sections in the same config file?  .i.e. does this graph use this feature?  How is this graph configured to use it?
2. What Makes the Orchestrator Unique
Role: Only the orchestrator talks to the user directly.  -- How is this different than the prompt?
Personality: May inject personality into prompts.
Sub-graph Coordination: Assigns tasks to sub-graphs/tools.  -- Again, core function of all graphs.
Conversation Management: Maintains user-facing conversation state.  -- Not needed.  If it uses conversation, it must use conversation state and persistant memory.  Perhaps add these requirements as a note to the conversation config.
System prompt: More complex, may include instructions for tool/agent routing.  -- Agreed, and I missed this, good catch.
These should be in orchestrator-specific config fields or a subclass (e.g., OrchestratorConfig(GraphConfig)). -- Yes, see above comment for tool registry
3. What Makes a Tool Agent Graph Unique
Specialized tool configs (e.g., Gmail, Calendar, etc.).  --  No, all of these are tool agent graphs.
Sub-tool registry: May have its own sub-graph/tool registry.  -- Already part of the program, or explain to me why it is not.
No direct user conversation (unless acting as a stand-alone agent).  -- No, congured above
These should be in agent-specific config fields or a subclass (e.g., PersonalAssistantConfig(GraphConfig)).
4. Implementation Plan
Step 1: Expand graph_config.py to include all generic config fields (with docstrings).  Great point for doc strings.
Step 2: Move orchestrator-specific fields to a subclass or a separate config (if needed).
Step 3: Update the orchestrator’s graph file to use the new config structure.
Step 4: Do the same for personal_assistant and other agents. -- That is this whole excercise.  





uuid will not handle . appended uuids in the database.  If a message has a request_id, it much move that to metadata as parent request_id, and if it is going to the parent as a response, it should close it's local request and request_id and replace it with the parent request id.



Wrap on Monday 5/6/2025
We are failing to call the dummy email tool
We are failing to authorize anything with google
We are not logging transactions through the personal assistant
We just got the failed to encode error AGAIN

We were adjusting the settings and it was ratholing so we tried to return to testing messages between graphs.  Somewhat successful but with kluge files
We are not sending our messages to or from the UI, rather directly through the personal assistant graph
We I do not believe we are sending the messages to the personal assistant graph llm connection







Multi-Personality Config Migration Checklist
[ ] Update YAML Structure
Add a personality: section with:
default_personality: valet
personalities: dictionary, one entry per agent/personality.
Example:
Apply to user_config....
[ ] Move Existing Personality Configs to YAML
For each agent/personality, move their config from Python or other files into the YAML under personalities:.
[ ] Update/Refactor Agent Loading Logic
Ensure agent/personality selection uses get_personality_config(name, ...) from personality_config.py.
When switching personalities (e.g., “Let me speak with the personal assistant”), pass the correct name to the loader.
[ ] Session/State Management
Ensure each personality/agent can have its own session state (e.g., conversation history, context).
Store session state keyed by both personality_name and session_id if needed.
[ ] Update Documentation
Document the new YAML structure and how to add/edit personalities.
Add usage examples for switching personalities and listing available personalities.
[ ] Test Backward Compatibility
Verify that a single-personality config (old style) still works.
[ ] (Optional) Add CLI/Tooling
Add a script or CLI command to list available personalities and show their config.
File/Location Reference:
YAML: config/developer_user_config.yaml
Loader: src/config/personality_config.py
Agent/session logic: wherever you manage agent state/switching



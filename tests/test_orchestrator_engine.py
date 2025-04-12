"""Tests for the orchestrator engine."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from typing import Dict, Any, List

from src.graphs.orchestrator_engine import (
    OrchestratorEngine, AgentNode, ControlNode, TerminalNode,
    ExecutionError, NodeExecutionError
)
from src.graphs.orchestrator_graph import (
    GraphState, StateManager, Message, MessageRole,
    TaskStatus, create_initial_state
)

@pytest.fixture
def mock_state_manager():
    """Create a mock state manager for testing."""
    state = create_initial_state()
    manager = StateManager(state)
    return manager

@pytest.fixture
def mock_llm_agent():
    """Create a mock LLM agent for testing."""
    agent = MagicMock()
    agent.chat = AsyncMock(return_value="Agent response")
    return agent

@pytest.fixture
def mock_db_manager():
    """Create a mock database manager for testing."""
    db = MagicMock()
    db.add_message = AsyncMock()
    db.get_recent_messages = AsyncMock(return_value=[])
    db.create_conversation = AsyncMock(return_value="conversation-id")
    db.save_graph_state = AsyncMock()
    db.load_graph_state = AsyncMock(return_value=create_initial_state())
    return db

@pytest.fixture
def simple_orchestrator_engine(mock_state_manager, mock_llm_agent, mock_db_manager):
    """Create a simple orchestrator engine for testing."""
    # Create nodes
    agent_node = AgentNode(
        id="agent1",
        name="Test Agent",
        agent=mock_llm_agent
    )
    
    control_node = ControlNode(
        id="control1",
        name="Test Control",
        routing_function=lambda state: "agent1"
    )
    
    terminal_node = TerminalNode(
        id="terminal1",
        name="Terminal Node"
    )
    
    # Create graph with nodes
    graph = {
        "start_node": "control1",
        "nodes": {
            "control1": control_node,
            "agent1": agent_node,
            "terminal1": terminal_node
        },
        "edges": {
            "control1": ["agent1"],
            "agent1": ["terminal1"],
            "terminal1": []
        }
    }
    
    # Create engine with graph
    engine = OrchestratorEngine(
        state_manager=mock_state_manager,
        graph=graph,
        db_manager=mock_db_manager
    )
    
    return engine

@pytest.mark.asyncio
async def test_agent_node_execution(mock_state_manager, mock_llm_agent):
    """Test agent node execution."""
    # Setup
    node = AgentNode(
        id="test_agent",
        name="Test Agent",
        agent=mock_llm_agent
    )
    
    # Set up the state with a user message
    mock_state_manager.update_conversation(MessageRole.USER, "Hello agent")
    
    # Execute node
    result = await node.execute(mock_state_manager)
    
    # Assertions
    assert result == "agent1"  # Default next node is same as agent ID
    mock_llm_agent.chat.assert_called_once()
    mock_state_manager.update_conversation.assert_called_with(
        MessageRole.ASSISTANT, "Agent response", {'agent_id': 'test_agent'}
    )
    mock_state_manager.update_agent_state.assert_called()

@pytest.mark.asyncio
async def test_control_node_execution(mock_state_manager):
    """Test control node execution."""
    # Test routing function
    routing_function = MagicMock(return_value="next_node")
    
    # Setup
    node = ControlNode(
        id="test_control",
        name="Test Control",
        routing_function=routing_function
    )
    
    # Execute node
    result = await node.execute(mock_state_manager)
    
    # Assertions
    assert result == "next_node"
    routing_function.assert_called_once_with(mock_state_manager.state)

@pytest.mark.asyncio
async def test_terminal_node_execution(mock_state_manager):
    """Test terminal node execution."""
    # Setup
    node = TerminalNode(
        id="test_terminal",
        name="Test Terminal"
    )
    
    # Set current task
    mock_state_manager.set_task("test_task")
    
    # Execute node
    result = await node.execute(mock_state_manager)
    
    # Assertions
    assert result is None  # Terminal nodes return None
    assert mock_state_manager.state["conversation_state"].current_task_status == TaskStatus.COMPLETED

@pytest.mark.asyncio
async def test_orchestrator_initialization(simple_orchestrator_engine, mock_db_manager):
    """Test orchestrator engine initialization."""
    engine = simple_orchestrator_engine
    
    # Test graph structure
    assert "start_node" in engine.graph
    assert "nodes" in engine.graph
    assert "edges" in engine.graph
    assert engine.graph["start_node"] == "control1"
    
    # Test node types
    assert isinstance(engine.graph["nodes"]["control1"], ControlNode)
    assert isinstance(engine.graph["nodes"]["agent1"], AgentNode)
    assert isinstance(engine.graph["nodes"]["terminal1"], TerminalNode)
    
    # Test connections
    assert engine.graph["edges"]["control1"] == ["agent1"]
    assert engine.graph["edges"]["agent1"] == ["terminal1"]
    assert engine.graph["edges"]["terminal1"] == []

@pytest.mark.asyncio
async def test_orchestrator_start_conversation(simple_orchestrator_engine, mock_db_manager):
    """Test starting a conversation with the orchestrator."""
    engine = simple_orchestrator_engine
    
    # Start conversation
    await engine.start_conversation()
    
    # Verify database call
    mock_db_manager.create_conversation.assert_called_once()
    mock_db_manager.save_graph_state.assert_called_once()

@pytest.mark.asyncio
async def test_orchestrator_process_message(simple_orchestrator_engine, mock_state_manager):
    """Test processing a message with the orchestrator."""
    engine = simple_orchestrator_engine
    
    # Set up a spy on the _execute_node method
    with patch.object(engine, '_execute_node', AsyncMock()) as mock_execute:
        mock_execute.return_value = None  # Simulate reaching terminal node
        
        # Process a message
        await engine.process_message("Hello orchestrator")
        
        # Verify message added to state
        assert mock_state_manager.update_conversation.called
        last_call_args = mock_state_manager.update_conversation.call_args_list[-1]
        assert last_call_args[0][0] == MessageRole.USER
        assert last_call_args[0][1] == "Hello orchestrator"
        
        # Verify execution started from start node
        mock_execute.assert_called_once_with("control1")

@pytest.mark.asyncio
async def test_orchestrator_execution_path(simple_orchestrator_engine, mock_db_manager):
    """Test a full execution path through the orchestrator."""
    engine = simple_orchestrator_engine
    
    # Start conversation
    await engine.start_conversation()
    
    # Create spies to track node execution
    control_spy = AsyncMock(wraps=engine.graph["nodes"]["control1"].execute)
    agent_spy = AsyncMock(wraps=engine.graph["nodes"]["agent1"].execute)
    terminal_spy = AsyncMock(wraps=engine.graph["nodes"]["terminal1"].execute)
    
    engine.graph["nodes"]["control1"].execute = control_spy
    engine.graph["nodes"]["agent1"].execute = agent_spy
    engine.graph["nodes"]["terminal1"].execute = terminal_spy
    
    # Process a message to trigger execution
    await engine.process_message("Hello orchestrator")
    
    # Verify execution order
    control_spy.assert_called_once()
    agent_spy.assert_called_once()
    terminal_spy.assert_called_once()
    
    # Verify state was saved after execution
    assert mock_db_manager.save_graph_state.call_count >= 2

@pytest.mark.asyncio
async def test_orchestrator_error_handling(simple_orchestrator_engine, mock_state_manager):
    """Test error handling during orchestration."""
    engine = simple_orchestrator_engine
    
    # Set up an agent node that raises an error
    error_agent = MagicMock()
    error_agent.chat = AsyncMock(side_effect=Exception("Agent failure"))
    
    engine.graph["nodes"]["agent1"].agent = error_agent
    
    # Process a message
    with pytest.raises(NodeExecutionError):
        await engine.process_message("This will cause an error")
    
    # Verify task was marked as failed
    assert mock_state_manager.fail_task.called

@pytest.mark.asyncio
async def test_orchestrator_load_state(simple_orchestrator_engine, mock_db_manager):
    """Test loading state from the database."""
    engine = simple_orchestrator_engine
    
    # Mock the loaded state
    test_state = create_initial_state()
    # Add some data to differentiate it
    test_state["conversation_state"].add_message(MessageRole.USER, "Previous message")
    mock_db_manager.load_graph_state.return_value = test_state
    
    # Load state for a conversation
    await engine.load_conversation("test-conversation-id")
    
    # Verify database call
    mock_db_manager.load_graph_state.assert_called_once_with("test-conversation-id")
    
    # Verify state was loaded
    loaded_messages = engine.state_manager.state["conversation_state"].messages
    assert len(loaded_messages) == 1
    assert loaded_messages[0].content == "Previous message"

@pytest.mark.asyncio
async def test_orchestrator_parallel_execution(mock_state_manager, mock_llm_agent, mock_db_manager):
    """Test parallel execution of multiple nodes."""
    # Create parallel agents
    agent1 = MagicMock()
    agent1.chat = AsyncMock(return_value="Agent 1 response")
    
    agent2 = MagicMock()
    agent2.chat = AsyncMock(return_value="Agent 2 response")
    
    # Create nodes
    agent_node1 = AgentNode(id="agent1", name="Agent 1", agent=agent1)
    agent_node2 = AgentNode(id="agent2", name="Agent 2", agent=agent2)
    
    # Create control node that returns multiple next nodes
    control_node = ControlNode(
        id="parallel_control",
        name="Parallel Control",
        routing_function=lambda state: ["agent1", "agent2"]
    )
    
    merger_node = ControlNode(
        id="merger",
        name="Merger Node",
        routing_function=lambda state: "terminal"
    )
    
    terminal_node = TerminalNode(id="terminal", name="Terminal")
    
    # Create graph with parallel execution
    graph = {
        "start_node": "parallel_control",
        "nodes": {
            "parallel_control": control_node,
            "agent1": agent_node1,
            "agent2": agent_node2,
            "merger": merger_node,
            "terminal": terminal_node
        },
        "edges": {
            "parallel_control": ["agent1", "agent2"],
            "agent1": ["merger"],
            "agent2": ["merger"],
            "merger": ["terminal"],
            "terminal": []
        }
    }
    
    # Create engine with graph
    engine = OrchestratorEngine(
        state_manager=mock_state_manager,
        graph=graph,
        db_manager=mock_db_manager
    )
    
    # Process a message (this will trigger parallel execution)
    await engine.process_message("Execute in parallel")
    
    # Verify both agents were called
    agent1.chat.assert_called_once()
    agent2.chat.assert_called_once()
    
    # Verify both agent responses were added to the state
    agent_states = mock_state_manager.state["agent_states"]
    assert "agent1" in agent_states
    assert "agent2" in agent_states

@pytest.mark.asyncio
async def test_orchestrator_custom_routing_logic(mock_state_manager, mock_llm_agent, mock_db_manager):
    """Test orchestrator with custom routing logic."""
    # Create a custom routing function based on message content
    def custom_router(state):
        # Get the last user message
        messages = state["conversation_state"].messages
        user_messages = [m for m in messages if m.role == MessageRole.USER]
        
        if not user_messages:
            return "default_agent"
            
        last_user_msg = user_messages[-1].content.lower()
        
        if "help" in last_user_msg:
            return "help_agent"
        elif "search" in last_user_msg:
            return "search_agent"
        else:
            return "default_agent"
    
    # Create mock agents
    default_agent = MagicMock()
    default_agent.chat = AsyncMock(return_value="Default response")
    
    help_agent = MagicMock()
    help_agent.chat = AsyncMock(return_value="Help response")
    
    search_agent = MagicMock()
    search_agent.chat = AsyncMock(return_value="Search response")
    
    # Create nodes
    router = ControlNode(id="router", name="Router", routing_function=custom_router)
    default_node = AgentNode(id="default_agent", name="Default Agent", agent=default_agent)
    help_node = AgentNode(id="help_agent", name="Help Agent", agent=help_agent)
    search_node = AgentNode(id="search_agent", name="Search Agent", agent=search_agent)
    terminal = TerminalNode(id="terminal", name="Terminal")
    
    # Create graph
    graph = {
        "start_node": "router",
        "nodes": {
            "router": router,
            "default_agent": default_node,
            "help_agent": help_node,
            "search_agent": search_node,
            "terminal": terminal
        },
        "edges": {
            "router": ["default_agent", "help_agent", "search_agent"],
            "default_agent": ["terminal"],
            "help_agent": ["terminal"],
            "search_agent": ["terminal"],
            "terminal": []
        }
    }
    
    # Create engine
    engine = OrchestratorEngine(
        state_manager=mock_state_manager,
        graph=graph,
        db_manager=mock_db_manager
    )
    
    # Test routing to help agent
    await engine.process_message("I need help with something")
    help_agent.chat.assert_called_once()
    
    # Reset mocks
    help_agent.chat.reset_mock()
    search_agent.chat.reset_mock()
    default_agent.chat.reset_mock()
    
    # Test routing to search agent
    await engine.process_message("Can you search for something?")
    search_agent.chat.assert_called_once()
    
    # Reset mocks
    help_agent.chat.reset_mock()
    search_agent.chat.reset_mock()
    default_agent.chat.reset_mock()
    
    # Test routing to default agent
    await engine.process_message("Just a regular message")
    default_agent.chat.assert_called_once()

@pytest.mark.asyncio
async def test_orchestrator_state_persistence(simple_orchestrator_engine, mock_db_manager):
    """Test state persistence between message processing."""
    engine = simple_orchestrator_engine
    
    # First message
    await engine.process_message("First message")
    
    # Verify state was saved
    assert mock_db_manager.save_graph_state.called
    
    # Reset mock to track new calls
    mock_db_manager.save_graph_state.reset_mock()
    
    # Second message
    await engine.process_message("Second message")
    
    # Verify state was saved again
    assert mock_db_manager.save_graph_state.called
    
    # Check that both messages are in the state
    messages = engine.state_manager.state["conversation_state"].messages
    user_messages = [m for m in messages if m.role == MessageRole.USER]
    assert len(user_messages) == 2
    assert user_messages[0].content == "First message"
    assert user_messages[1].content == "Second message" 
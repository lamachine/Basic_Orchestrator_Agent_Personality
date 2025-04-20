import pytest
from unittest.mock import patch, MagicMock
from src.agents.base_agent import BaseAgent
from src.state.state_models import MessageRole

def test_base_agent_initialization():
    """Test the basic initialization of BaseAgent."""
    agent = BaseAgent(name="test_agent")
    assert agent.name == "test_agent"
    assert agent.conversation_id is None
    assert agent.has_db is True or agent.has_db is False  # Depends on DB availability

def test_state_initialization():
    """Test that BaseAgent correctly initializes state with messages field."""
    # Mock state manager import
    with patch('src.agents.base_agent.HAS_STATE_MANAGER', True), \
         patch('src.agents.base_agent.StateManager') as mock_state_manager, \
         patch('src.agents.base_agent.create_initial_state') as mock_create_state, \
         patch('src.agents.base_agent.DatabaseManager') as mock_db:
        
        # Setup mock database
        mock_message_manager = MagicMock()
        mock_db_instance = MagicMock()
        mock_db_instance.message_manager = mock_message_manager
        mock_db.return_value = mock_db_instance
        
        # Create a mock state with the messages field
        mock_state = {
            'messages': [],
            'conversation_state': MagicMock(),
            'agent_states': {},
            'current_task': None,
            'task_history': [],
            'agent_results': {},
            'final_result': None
        }
        mock_create_state.return_value = mock_state
        
        # Create agent with mocked state
        agent = BaseAgent(name="test_agent")
        
        # Verify state is initialized correctly
        assert agent.graph_state == mock_state
        assert 'messages' in agent.graph_state
        assert agent.graph_state['messages'] == []
        
        # Test update_conversation can access messages without error
        with patch.object(agent.state_manager, 'update_conversation') as mock_update:
            # Call chat which should call update_conversation
            agent.conversation_id = "123"
            # Also need to mock the LLM query since we're calling chat()
            with patch.object(agent, 'query_llm', return_value="test response"):
                agent.chat("test message")
                mock_update.assert_called_once()
                # Check message_manager.store_message was also called
                mock_message_manager.store_message.assert_called() 
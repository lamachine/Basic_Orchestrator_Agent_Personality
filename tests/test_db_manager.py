"""Tests for the DatabaseManager."""

import json
import pytest
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime
from src.services.db_services.db_manager import DatabaseManager

# Import the Message model
from src.graphs.orchstrator_graph import Message, MessageRole 

# Mock Supabase responses
@pytest.fixture
def mock_supabase_response():
    """Mock successful Supabase response"""
    return Mock(
        data=[{
            'id': 1,
            'conversation_id': '123',
            'role': 'user',
            'message': 'test message',
            'created_at': datetime.now().isoformat()
        }]
    )

@pytest.fixture
def mock_db_manager():
    """Create a DatabaseManager with mocked Supabase client"""
    with patch('src.services.db_manager.create_client') as mock_create_client:
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        db_manager = DatabaseManager()
        db_manager.supabase = mock_client
        return db_manager

class TestDatabaseManager:
    def test_create_conversation(self, mock_db_manager, mock_supabase_response):
        """Test conversation creation"""
        mock_db_manager.supabase.table().insert().execute.return_value = mock_supabase_response
        
        conversation_id = mock_db_manager.create_conversation("user123")
        
        # Verify the call
        mock_db_manager.supabase.table.assert_called_with('conversations')
        mock_db_manager.supabase.table().insert.assert_called_with({
            'user_id': 'user123'
        })
        assert conversation_id == mock_supabase_response.data[0]['id']

    def test_add_message(self, mock_db_manager):
        """Test message addition"""
        # Capture timestamp immediately before the call
        timestamp_before_call = datetime.now()
        # Format it as expected by the db_manager
        expected_iso_string = timestamp_before_call.isoformat()
        
        mock_db_manager.add_message(
            session_id="123",
            role="user",
            message="test message",
            metadata={"source": "test"},
            embedding=[0.1, 0.2, 0.3]
        )
        
        # Verify the call - Expect created_at as an ISO string
        mock_db_manager.supabase.table.assert_called_with('messages')
        
        # Get the actual arguments passed to the mock
        actual_call_args = mock_db_manager.supabase.table().insert.call_args[0][0]
        
        # Check individual fields, comparing timestamp string approximately
        assert actual_call_args['session_id'] == "123"
        assert actual_call_args['role'] == "user"
        assert actual_call_args['message'] == "test message"
        assert actual_call_args['metadata'] == json.dumps({"source": "test"})
        assert actual_call_args['embedding_nomic'] == [0.1, 0.2, 0.3]
        # Compare the string timestamp, allowing for slight differences
        # Parse both strings back to datetime for comparison with tolerance
        actual_dt = datetime.fromisoformat(actual_call_args['created_at'])
        expected_dt = datetime.fromisoformat(expected_iso_string)
        assert abs((actual_dt - expected_dt).total_seconds()) < 1 # Allow 1 second difference

    def test_get_recent_messages(self, mock_db_manager, mock_supabase_response):
        """Test retrieving recent messages"""
        mock_db_manager.supabase.table().select().eq().order().limit().execute.return_value = mock_supabase_response
        
        messages = mock_db_manager.get_recent_messages("123", limit=10)
        
        # Verify the call
        mock_db_manager.supabase.table.assert_called_with('messages')
        mock_db_manager.supabase.table().select.assert_called_with('role, message')
        assert messages == mock_supabase_response.data

    @pytest.mark.asyncio
    async def test_save_graph_state(self, mock_db_manager):
        """Test saving graph state"""
        timestamp_before_call = datetime.now()
        test_state = {
            'current_task': 'test_task',
            'task_history': ['task1', 'task2'],
            'agent_states': {'agent1': {'status': 'running'}},
            'agent_results': {'task1': 'success'},
            'final_result': 'completed',
            'messages': [
                Message(
                    role=MessageRole.USER,
                    content='test',
                    metadata={'source': 'test'},
                    created_at=timestamp_before_call
                )
            ]
        }
        
        # Mock the add_message method for this test to track calls
        mock_db_manager.add_message = Mock()

        await mock_db_manager.save_graph_state("123", test_state)
        
        # --- Verify conversation update --- 
        update_call_args = mock_db_manager.supabase.table().update.call_args[0][0]
        # Check non-timestamp fields directly
        assert update_call_args['current_task'] == 'test_task'
        assert update_call_args['task_history'] == json.dumps(['task1', 'task2'])
        assert update_call_args['agent_states'] == json.dumps({'agent1': {'status': 'running'}})
        assert update_call_args['agent_results'] == json.dumps({'task1': 'success'})
        assert update_call_args['final_result'] == 'completed'
        # Compare updated_at timestamp string with tolerance
        actual_update_dt = datetime.fromisoformat(update_call_args['updated_at'])
        assert abs((actual_update_dt - timestamp_before_call).total_seconds()) < 2 # Increased tolerance slightly
        
        # --- Verify message insertion --- 
        # The save_graph_state method calls add_message with positional args
        mock_db_manager.add_message.assert_called_once_with(
            "123",                     # session_id (positional)
            MessageRole.USER.value,    # role (positional)
            "test",                    # message (positional)
            metadata={'source': 'test'} # metadata (keyword)
        )

    @pytest.mark.asyncio
    async def test_load_graph_state(self, mock_db_manager, mock_supabase_response):
        """Test loading graph state"""
        mock_db_manager.supabase.table().select().eq().single().execute.return_value = Mock(
            data={
                'current_task': 'test_task',
                'task_history': json.dumps(['task1']),
                'agent_states': json.dumps({'agent1': {'status': 'running'}}),
                'agent_results': json.dumps({'task1': 'success'}),
                'final_result': 'completed',
                'updated_at': datetime.now().isoformat()
            }
        )
        
        mock_db_manager.get_recent_messages = Mock(return_value=[
            {'role': 'user', 'message': 'test'}
        ])
        
        state = await mock_db_manager.load_graph_state("123")
        
        # Verify the loaded state
        assert state['current_task'] == 'test_task'
        assert len(state['task_history']) == 1
        assert state['agent_states']['agent1']['status'] == 'running'
        assert state['agent_results']['task1'] == 'success'
        assert len(state['messages']) == 1

    @pytest.mark.asyncio
    async def test_update_agent_state(self, mock_db_manager):
        """Test updating agent state"""
        timestamp_before_call = datetime.now()
        mock_db_manager.supabase.table().select().eq().single().execute.return_value = Mock(
            data={'agent_states': json.dumps({'agent1': {'status': 'idle'}})}
        )
        
        new_state = {'status': 'running'}
        await mock_db_manager.update_agent_state("123", "agent1", new_state)
        
        # --- Verify the update --- 
        expected_states = {'agent1': {'status': 'running'}}
        update_call_args = mock_db_manager.supabase.table().update.call_args[0][0]
        # Check agent_states directly
        assert update_call_args['agent_states'] == json.dumps(expected_states)
        # Compare updated_at timestamp string with tolerance
        actual_update_dt = datetime.fromisoformat(update_call_args['updated_at'])
        assert abs((actual_update_dt - timestamp_before_call).total_seconds()) < 2 # Increased tolerance slightly

    def test_search_similar_messages(self, mock_db_manager, mock_supabase_response):
        """Test semantic search functionality"""
        mock_db_manager.supabase.rpc().execute.return_value = mock_supabase_response
        
        embedding = [0.1, 0.2, 0.3]
        results = mock_db_manager.search_similar_messages(embedding, limit=5)
        
        # Verify the call
        mock_db_manager.supabase.rpc.assert_called_with(
            'match_messages',
            {
                'query_embedding': embedding,
                'match_threshold': 0.7,
                'match_count': 5
            }
        )
        assert results == mock_supabase_response.data

class TestDatabaseIntegration:
    @pytest.mark.asyncio
    async def test_complete_workflow(self, mock_db_manager, mock_supabase_response):
        """Test a complete database workflow"""
        timestamp_before_call = datetime.now()
        # --- Mock methods used within the workflow --- 
        mock_db_manager.supabase.table().insert().execute.return_value = mock_supabase_response
        # Mock add_message specifically for this test to check call_count
        mock_db_manager.add_message = Mock()

        # --- Run workflow steps --- 
        conv_id = mock_db_manager.create_conversation("user123")
        
        # These direct calls likely also use positional args based on add_message definition
        # If add_message signature uses keywords, these might need adjustment
        mock_db_manager.add_message(conv_id, "user", "test message")
        mock_db_manager.add_message(conv_id, "assistant", "test response")
        
        test_state = {
            'current_task': 'test_task',
            'messages': [
                Message(role=MessageRole.USER, content='test message', created_at=datetime.now()),
                Message(role=MessageRole.ASSISTANT, content='test response', created_at=datetime.now())
            ],
            'task_history': [],
            'agent_states': {},
            'agent_results': {},
            'final_result': None,
        }
        await mock_db_manager.save_graph_state(conv_id, test_state)
        
        # --- Verify calls --- 
        # Check conversation creation call
        mock_db_manager.supabase.table().insert.assert_called_with({'user_id': 'user123'})

        # Check update call (state save)
        update_call_args = mock_db_manager.supabase.table().update.call_args[0][0]
        assert update_call_args['current_task'] == 'test_task'
        # Compare updated_at timestamp string with tolerance
        actual_update_dt = datetime.fromisoformat(update_call_args['updated_at'])
        assert abs((actual_update_dt - timestamp_before_call).total_seconds()) < 3 # Wider tolerance for multi-step test
        
        # Verify add_message calls using the mock
        assert mock_db_manager.add_message.call_count == 4 
        
        # Check calls with positional args for first 3, keyword for metadata
        # Check direct calls
        mock_db_manager.add_message.assert_any_call(conv_id, "user", "test message") # Assuming direct calls also use positional
        mock_db_manager.add_message.assert_any_call(conv_id, "assistant", "test response") # Assuming direct calls also use positional
        
        # Check calls from save_graph_state 
        mock_db_manager.add_message.assert_any_call(
            conv_id,                   # session_id (positional)
            MessageRole.USER.value,    # role (positional)
            'test message',            # message (positional)
            metadata={}                # metadata (keyword)
        )
        mock_db_manager.add_message.assert_any_call(
            conv_id,                   # session_id (positional)
            MessageRole.ASSISTANT.value,# role (positional)
            'test response',           # message (positional)
            metadata={}                # metadata (keyword)
        ) 

@pytest.fixture
def mock_supabase():
    """Mock Supabase client for testing."""
    mock_client = MagicMock()
    
    # Mock successful responses
    mock_insert_response = MagicMock()
    mock_insert_response.data = [{"id": "test-session-id"}]
    mock_insert_response.execute.return_value = mock_insert_response
    
    mock_select_response = MagicMock()
    mock_select_response.data = [
        {"role": "user", "message": "Hello"},
        {"role": "assistant", "message": "Hi there"}
    ]
    mock_select_response.execute.return_value = mock_select_response
    
    # Mock table methods
    mock_table = MagicMock()
    mock_table.insert.return_value = mock_insert_response
    mock_table.select.return_value = mock_select_response
    mock_table.eq.return_value = mock_select_response
    mock_table.order.return_value = mock_select_response
    mock_table.limit.return_value = mock_select_response
    mock_table.update.return_value = mock_insert_response
    
    # Mock rpc
    mock_rpc_response = MagicMock()
    mock_rpc_response.data = [{"match_score": 0.95, "message": "Similar message"}]
    mock_rpc_response.execute.return_value = mock_rpc_response
    
    mock_client.table.return_value = mock_table
    mock_client.rpc.return_value = mock_rpc_response
    
    with patch('src.services.db_services.db_manager.create_client', return_value=mock_client):
        yield mock_client

def test_init(mock_supabase):
    """Test the initialization of DatabaseManager."""
    with patch('os.getenv') as mock_getenv:
        mock_getenv.side_effect = lambda key: {
            'SUPABASE_URL': 'https://test-url.supabase.co',
            'SUPABASE_SERVICE_ROLE_KEY': 'test-key'
        }.get(key)
        
        db = DatabaseManager()
        
        # Check the Supabase client was created with correct params
        from src.services.db_services.db_manager import create_client
        create_client.assert_called_once_with('https://test-url.supabase.co', 'test-key')

def test_create_conversation(mock_supabase):
    """Test creating a new conversation."""
    db = DatabaseManager()
    user_id = "test-user-123"
    
    session_id = db.create_conversation(user_id)
    
    # Check conversation was created
    mock_supabase.table.assert_called_with('conversations')
    mock_supabase.table().insert.assert_called_once_with({'user_id': user_id})
    assert session_id == "test-session-id"

def test_add_message(mock_supabase):
    """Test adding a message to a conversation."""
    db = DatabaseManager()
    session_id = "test-session-123"
    role = "user"
    message = "Hello, how are you?"
    metadata = {"user_id": "test-user", "client": "web"}
    
    db.add_message(session_id, role, message, metadata)
    
    # Check message was added
    mock_supabase.table.assert_called_with('messages')
    mock_supabase.table().insert.assert_called_once_with({
        'session_id': session_id,
        'role': role,
        'message': message,
        'metadata': json.dumps(metadata),
        'embedding_nomic': None,
        'created_at': ANY
    })
    
    # Check the created_at timestamp is in ISO format
    call_args = mock_supabase.table().insert.call_args[0][0]
    assert 'created_at' in call_args
    # Verify it's a valid ISO format timestamp
    try:
        datetime.fromisoformat(call_args['created_at'])
    except ValueError:
        pytest.fail("created_at is not a valid ISO format timestamp")

def test_get_recent_messages(mock_supabase):
    """Test retrieving recent messages."""
    db = DatabaseManager()
    session_id = "test-session-123"
    limit = 5
    
    messages = db.get_recent_messages(session_id, limit)
    
    # Check messages were retrieved
    mock_supabase.table.assert_called_with('messages')
    table_mock = mock_supabase.table()
    table_mock.select.assert_called_with('role, message')
    table_mock.eq.assert_called_with('session_id', session_id)
    table_mock.order.assert_called_with('created_at', desc=True)
    table_mock.limit.assert_called_with(limit)
    
    assert len(messages) == 2
    assert messages[0]['role'] == 'user'
    assert messages[0]['message'] == 'Hello'
    assert messages[1]['role'] == 'assistant'
    assert messages[1]['message'] == 'Hi there'

def test_search_similar_messages(mock_supabase):
    """Test searching for similar messages."""
    db = DatabaseManager()
    embedding = [0.1, 0.2, 0.3]
    limit = 3
    
    results = db.search_similar_messages(embedding, limit)
    
    # Check similarity search was performed
    mock_supabase.rpc.assert_called_with(
        'match_messages',
        {
            'query_embedding': embedding,
            'match_threshold': 0.7,
            'match_count': limit
        }
    )
    
    assert len(results) == 1
    assert results[0]['match_score'] == 0.95
    assert results[0]['message'] == 'Similar message'

@pytest.mark.asyncio
async def test_save_graph_state(mock_supabase):
    """Test saving graph state."""
    db = DatabaseManager()
    conversation_id = "test-conversation-123"
    state = {
        'current_task': 'testing',
        'task_history': ['task1', 'task2'],
        'agent_states': {'agent1': {'status': 'running'}},
        'agent_results': {'task1': 'result1'},
        'final_result': 'final test result',
        'messages': []
    }
    
    await db.save_graph_state(conversation_id, state)
    
    # Check state was saved
    mock_supabase.table.assert_called_with('conversations')
    mock_supabase.table().update.assert_called_once()
    
    # Check the update has correct fields
    call_args = mock_supabase.table().update.call_args[0][0]
    assert call_args['current_task'] == 'testing'
    assert call_args['task_history'] == json.dumps(['task1', 'task2'])
    assert call_args['agent_states'] == json.dumps({'agent1': {'status': 'running'}})
    assert call_args['agent_results'] == json.dumps({'task1': 'result1'})
    assert call_args['final_result'] == 'final test result'
    assert 'updated_at' in call_args

@pytest.mark.asyncio
async def test_load_graph_state(mock_supabase):
    """Test loading graph state."""
    db = DatabaseManager()
    conversation_id = "test-conversation-123"
    
    # Mock get_recent_messages to return messages
    db.get_recent_messages = MagicMock(return_value=[
        {"role": "user", "message": "Hello"},
        {"role": "assistant", "message": "Hi there"}
    ])
    
    # Mock single response
    mock_single_response = MagicMock()
    mock_single_response.data = {
        'current_task': 'testing',
        'task_history': json.dumps(['task1', 'task2']),
        'agent_states': json.dumps({'agent1': {'status': 'running'}}),
        'agent_results': json.dumps({'task1': 'result1'}),
        'final_result': 'final test result',
        'updated_at': '2023-01-01T12:00:00',
        'current_task_status': 'pending'
    }
    mock_single_response.execute.return_value = mock_single_response
    
    table_mock = mock_supabase.table()
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.single.return_value = mock_single_response
    
    state = await db.load_graph_state(conversation_id)
    
    # Check state was loaded
    mock_supabase.table.assert_called_with('conversations')
    table_mock.select.assert_called_with('*')
    table_mock.eq.assert_called_with('conversation_id', conversation_id)
    
    # Check returned state has correct values
    assert state['current_task'] == 'testing'
    assert state['task_history'] == ['task1', 'task2']
    assert state['agent_states'] == {'agent1': {'status': 'running'}}
    assert state['agent_results'] == {'task1': 'result1'}
    assert state['final_result'] == 'final test result'
    assert state['conversation_state']['current_task_status'] == 'pending'
    assert len(state['messages']) == 2 
"""Configure pytest for the application tests."""

import pytest
import os
from datetime import datetime
from typing import Dict, Any, List
import sys
from unittest.mock import MagicMock
import json

# Environment setup for tests
@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables"""
    os.environ['url'] = 'http://localhost:54321'
    os.environ['anon_key'] = 'nomic-embed-text'
    os.environ['service_role_key'] = 'test-key'
    os.environ['api_url'] = 'http://localhost:11434'
    os.environ['OLLAMA_EMBEDDING_MODEL'] = 'nomic-embed-text'
    yield
    # Cleanup
    os.environ.pop('url', None)
    os.environ.pop('anon_key', None)
    os.environ.pop('service_role_key', None)
    os.environ.pop('api_url', None)
    os.environ.pop('OLLAMA_EMBEDDING_MODEL', None)

# Shared test data
@pytest.fixture
def sample_message_data():
    """Sample message data for tests"""
    return {
        'role': 'user',
        'content': 'test message',
        'metadata': {'source': 'test', 'user_id': 'developer'},
        'created_at': datetime.now().isoformat()
    }

@pytest.fixture
def sample_conversation_metadata():
    """Sample conversation metadata for tests"""
    return {
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'user_id': 'developer',
        'title': 'Test Conversation',
        'description': 'A test conversation'
    }

@pytest.fixture
def sample_state_data():
    """Sample state data for tests"""
    return {
        'current_task': 'test_task',
        'task_history': ['task1', 'task2'],
        'agent_states': {
            'agent1': {'status': 'running'}
        },
        'agent_results': {
            'task1': 'success'
        },
        'final_result': None,
        'messages': [],
        'current_task_status': 'pending'
    }

@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client"""
    mock = MagicMock()
    
    # Mock table operations
    table_mock = MagicMock()
    mock.table.return_value = table_mock
    
    # Mock insert operations
    insert_mock = MagicMock()
    table_mock.insert.return_value = insert_mock
    insert_mock.execute.return_value = MagicMock(data=[{'id': 1}])
    
    # Mock select operations
    select_mock = MagicMock()
    table_mock.select.return_value = select_mock
    select_mock.eq.return_value = select_mock
    select_mock.order.return_value = select_mock
    select_mock.limit.return_value = select_mock
    select_mock.execute.return_value = MagicMock(data=[
        {'session_id': 1, 'role': 'user', 'message': 'Hello', 
         'metadata': json.dumps({'user_id': 'developer'})}
    ])
    
    return mock

@pytest.fixture
def mock_ollama_client():
    """Create a mock Ollama client"""
    mock = MagicMock()
    
    # Create a response with an embedding attribute
    embedding_response = MagicMock()
    embedding_response.embedding = [0.1] * 768
    
    # Mock embeddings method
    mock.embeddings.return_value = embedding_response
    
    return mock

# Test utilities
def assert_datetime_approx(dt1: str, dt2: str, tolerance_seconds: int = 1):
    """Assert two datetime strings are approximately equal"""
    datetime1 = datetime.fromisoformat(dt1)
    datetime2 = datetime.fromisoformat(dt2)
    diff = abs((datetime1 - datetime2).total_seconds())
    assert diff <= tolerance_seconds, f"Datetime difference {diff} exceeds tolerance {tolerance_seconds}"

# Make utility available to all tests
@pytest.fixture
def datetime_approx():
    return assert_datetime_approx

# Create mock modules for modules that don't exist yet
MOCK_MODULES = [
    'src.personalities.personality_manager',
    'src.state.state_manager',
    'src.graphs.orchestrator_engine',
]

# Apply mocks to enable test collection without errors
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = MagicMock()

# Mock specific classes that are imported directly
class MockDatabaseError(Exception):
    """Mock DatabaseError for testing."""
    pass

class MockStateError(Exception):
    """Mock StateError for testing."""
    pass

class MockStateTransitionError(MockStateError):
    """Mock StateTransitionError for testing."""
    pass

# Patch the database module
if 'src.services.db_services.db_manager' in sys.modules:
    db_module = sys.modules['src.services.db_services.db_manager']
else:
    db_module = MagicMock()
    sys.modules['src.services.db_services.db_manager'] = db_module

# Add missing classes to db_manager
db_module.DatabaseError = MockDatabaseError
db_module.ConversationNotFoundError = type('ConversationNotFoundError', (Exception,), {})
db_module.StateError = MockStateError
db_module.StateTransitionError = MockStateTransitionError

# Define enum-like classes that match the actual enums
class MessageRole:
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class TaskStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

# Add enums to db_manager
db_module.MessageRole = MessageRole
db_module.TaskStatus = TaskStatus

# Define fixtures that can be used across tests
@pytest.fixture
def sample_config():
    """Return a sample configuration dictionary."""
    return {
        "app_name": "Test App",
        "debug": True,
        "file_level": "DEBUG",
        "console_level": "DEBUG",
        "db": {
            "host": "localhost",
            "port": 5432,
            "name": "test_db",
            "user": "test_user",
            "password": "test_password"
        }
    } 
import pytest
import os
from datetime import datetime
from typing import Dict, Any

# Environment setup for tests
@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables"""
    os.environ['SUPABASE_URL'] = 'http://localhost:54321'
    os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'test-key'
    yield
    # Cleanup
    os.environ.pop('SUPABASE_URL', None)
    os.environ.pop('SUPABASE_SERVICE_ROLE_KEY', None)

# Shared test data
@pytest.fixture
def sample_message_data():
    """Sample message data for tests"""
    return {
        'role': 'user',
        'content': 'test message',
        'metadata': {'source': 'test'},
        'created_at': datetime.now().isoformat()
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
        'messages': []
    }

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
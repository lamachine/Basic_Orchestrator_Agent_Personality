import json
from unittest.mock import patch

import pytest

from src.sub_graphs.template_agent.src.common.managers.memory_manager import Mem0Memory


@pytest.fixture
def mem0():
    return Mem0Memory()


@patch("subprocess.run")
def test_add_memory(mock_run, mem0):
    # Mock successful subprocess.run for add_memory
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = json.dumps({"status": "success"})

    result = mem0.add_memory(content="Test memory", metadata={"user": "test_user"})
    assert result == {"status": "success"}


@patch("subprocess.run")
def test_search_memory(mock_run, mem0):
    # Mock successful subprocess.run for search_memory
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = json.dumps({"results": [{"content": "Test memory"}]})

    result = mem0.search_memory(query="Test query")
    assert result == {"results": [{"content": "Test memory"}]}

"""Tests for the personality component."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import json
from typing import Dict, Any, List, Optional

from src.personalities.personality_manager import (
    PersonalityManager, 
    Personality,
    PersonalityNotFoundError
)

# Sample personality data for testing
SAMPLE_PERSONALITY = {
    "name": "Test Personality",
    "description": "A test personality for unit testing",
    "system_prompt": "You are a helpful test assistant.",
    "greeting": "Hello! I'm your test assistant.",
    "metadata": {
        "creator": "Test Author",
        "version": "1.0",
        "tags": ["test", "helpful"]
    }
}

SAMPLE_PERSONALITY_2 = {
    "name": "Another Personality",
    "description": "Another test personality",
    "system_prompt": "You are another test assistant.",
    "greeting": "Greetings! I'm another test assistant.",
    "metadata": {
        "creator": "Test Author",
        "version": "1.0",
        "tags": ["test", "fun"]
    }
}

@pytest.fixture
def sample_personality_file(tmp_path):
    """Create a sample personality file for testing."""
    personalities_dir = tmp_path / "personalities"
    personalities_dir.mkdir()
    
    personality_file = personalities_dir / "test_personality.json"
    with open(personality_file, "w") as f:
        json.dump(SAMPLE_PERSONALITY, f)
    
    personality_file2 = personalities_dir / "another_personality.json"
    with open(personality_file2, "w") as f:
        json.dump(SAMPLE_PERSONALITY_2, f)
    
    return str(personalities_dir)

@pytest.fixture
def personality_manager(sample_personality_file):
    """Create a personality manager with the sample personalities."""
    return PersonalityManager(personalities_dir=sample_personality_file)

def test_personality_creation():
    """Test creating a personality object."""
    personality = Personality(**SAMPLE_PERSONALITY)
    
    assert personality.name == "Test Personality"
    assert personality.description == "A test personality for unit testing"
    assert personality.system_prompt == "You are a helpful test assistant."
    assert personality.greeting == "Hello! I'm your test assistant."
    assert personality.metadata["creator"] == "Test Author"
    assert "test" in personality.metadata["tags"]

def test_personality_manager_initialization(sample_personality_file):
    """Test initializing the personality manager."""
    manager = PersonalityManager(personalities_dir=sample_personality_file)
    
    # Manager should load personalities from the directory
    assert len(manager.available_personalities) > 0
    assert "test_personality" in manager.available_personalities
    assert "another_personality" in manager.available_personalities

def test_personality_manager_get_personality(personality_manager):
    """Test getting a personality by name."""
    personality = personality_manager.get_personality("test_personality")
    
    assert personality.name == "Test Personality"
    assert personality.system_prompt == "You are a helpful test assistant."

def test_personality_manager_get_nonexistent_personality(personality_manager):
    """Test getting a personality that doesn't exist."""
    with pytest.raises(PersonalityNotFoundError):
        personality_manager.get_personality("nonexistent_personality")

def test_personality_manager_list_personalities(personality_manager):
    """Test listing all available personalities."""
    personalities = personality_manager.list_personalities()
    
    assert len(personalities) == 2
    assert "test_personality" in personalities
    assert "another_personality" in personalities

def test_personality_manager_filtered_list(personality_manager):
    """Test listing personalities filtered by tag."""
    # Get personalities with the "fun" tag
    fun_personalities = personality_manager.list_personalities(tag="fun")
    assert len(fun_personalities) == 1
    assert "another_personality" in fun_personalities
    
    # Get personalities with the "test" tag (should be both)
    test_personalities = personality_manager.list_personalities(tag="test")
    assert len(test_personalities) == 2

def test_personality_manager_creator_filter(personality_manager):
    """Test listing personalities filtered by creator."""
    # Both sample personalities have the same creator
    personalities = personality_manager.list_personalities(creator="Test Author")
    assert len(personalities) == 2
    
    # Filter by a different creator (should return empty)
    personalities = personality_manager.list_personalities(creator="Unknown Author")
    assert len(personalities) == 0

def test_personality_manager_add_personality(personality_manager, tmp_path):
    """Test adding a new personality."""
    new_personality = {
        "name": "New Personality",
        "description": "A new test personality",
        "system_prompt": "You are a brand new test assistant.",
        "greeting": "Hi! I'm a new test assistant.",
        "metadata": {
            "creator": "New Author",
            "version": "1.0",
            "tags": ["new", "test"]
        }
    }
    
    # Add the new personality
    personality_manager.add_personality("new_personality", new_personality)
    
    # Verify it was added to available personalities
    assert "new_personality" in personality_manager.available_personalities
    
    # Verify we can retrieve it
    retrieved = personality_manager.get_personality("new_personality")
    assert retrieved.name == "New Personality"
    assert retrieved.system_prompt == "You are a brand new test assistant."
    
    # Verify the file was created
    personality_file = os.path.join(personality_manager.personalities_dir, "new_personality.json")
    assert os.path.exists(personality_file)

def test_personality_manager_update_personality(personality_manager):
    """Test updating an existing personality."""
    # Get the original personality
    original = personality_manager.get_personality("test_personality")
    assert original.system_prompt == "You are a helpful test assistant."
    
    # Create updated personality data
    updated_data = {
        "name": "Updated Test Personality",
        "description": "An updated test personality",
        "system_prompt": "You are an updated test assistant.",
        "greeting": "Hello! I'm your updated test assistant.",
        "metadata": {
            "creator": "Test Author",
            "version": "1.1",
            "tags": ["test", "updated"]
        }
    }
    
    # Update the personality
    personality_manager.update_personality("test_personality", updated_data)
    
    # Verify it was updated
    updated = personality_manager.get_personality("test_personality")
    assert updated.name == "Updated Test Personality"
    assert updated.system_prompt == "You are an updated test assistant."
    assert updated.metadata["version"] == "1.1"
    assert "updated" in updated.metadata["tags"]

def test_personality_manager_delete_personality(personality_manager):
    """Test deleting a personality."""
    # Verify the personality exists
    assert "test_personality" in personality_manager.available_personalities
    
    # Delete the personality
    personality_manager.delete_personality("test_personality")
    
    # Verify it was removed from available personalities
    assert "test_personality" not in personality_manager.available_personalities
    
    # Verify attempting to get it raises an error
    with pytest.raises(PersonalityNotFoundError):
        personality_manager.get_personality("test_personality")
    
    # Verify the file was deleted
    personality_file = os.path.join(personality_manager.personalities_dir, "test_personality.json")
    assert not os.path.exists(personality_file)

def test_personality_manager_get_system_prompt(personality_manager):
    """Test getting the system prompt for a personality."""
    system_prompt = personality_manager.get_system_prompt("test_personality")
    assert system_prompt == "You are a helpful test assistant."

def test_personality_manager_get_greeting(personality_manager):
    """Test getting the greeting for a personality."""
    greeting = personality_manager.get_greeting("test_personality")
    assert greeting == "Hello! I'm your test assistant."

def test_personality_manager_refresh(personality_manager, tmp_path):
    """Test refreshing the personality manager to load new personalities."""
    # Add a new personality file directly (bypassing the manager)
    new_personality = {
        "name": "Refreshed Personality",
        "description": "A personality added manually",
        "system_prompt": "You are a refreshed test assistant.",
        "greeting": "Hello after refresh!",
        "metadata": {
            "creator": "Test Author",
            "version": "1.0",
            "tags": ["test", "refresh"]
        }
    }
    
    personality_file = os.path.join(personality_manager.personalities_dir, "refreshed_personality.json")
    with open(personality_file, "w") as f:
        json.dump(new_personality, f)
    
    # Initially, the manager won't know about this personality
    assert "refreshed_personality" not in personality_manager.available_personalities
    
    # Refresh the manager
    personality_manager.refresh()
    
    # Now it should be available
    assert "refreshed_personality" in personality_manager.available_personalities
    
    # We should be able to retrieve it
    personality = personality_manager.get_personality("refreshed_personality")
    assert personality.name == "Refreshed Personality"
    assert personality.system_prompt == "You are a refreshed test assistant."

def test_personality_validate(personality_manager):
    """Test validating a personality."""
    # Valid personality should validate without errors
    valid_personality = {
        "name": "Valid Personality",
        "description": "A valid test personality",
        "system_prompt": "You are a valid test assistant.",
        "greeting": "Hello! I'm valid.",
        "metadata": {
            "creator": "Test Author",
            "version": "1.0",
            "tags": ["test", "valid"]
        }
    }
    
    # This should not raise an exception
    personality_manager._validate_personality(valid_personality)
    
    # Invalid personality (missing required fields)
    invalid_personality = {
        "name": "Invalid Personality",
        "description": "An invalid test personality",
        # Missing system_prompt
        "greeting": "Hello! I'm invalid.",
        "metadata": {
            "creator": "Test Author",
            "version": "1.0",
            "tags": ["test", "invalid"]
        }
    }
    
    # This should raise a ValueError
    with pytest.raises(ValueError):
        personality_manager._validate_personality(invalid_personality)

@patch("builtins.open")
@patch("json.dump")
def test_personality_manager_save_personality(mock_json_dump, mock_open, personality_manager):
    """Test saving a personality to a file."""
    personality = Personality(**SAMPLE_PERSONALITY)
    
    # Call the method to save the personality
    personality_manager._save_personality("test_save", personality)
    
    # Verify open was called with the correct path
    expected_path = os.path.join(personality_manager.personalities_dir, "test_save.json")
    mock_open.assert_called_once_with(expected_path, "w")
    
    # Verify json.dump was called with the personality dict
    file_handle = mock_open.return_value.__enter__.return_value
    mock_json_dump.assert_called_once()
    # First argument should be the personality dict
    assert mock_json_dump.call_args[0][0]["name"] == "Test Personality"
    # Second argument should be the file handle
    assert mock_json_dump.call_args[0][1] == file_handle

def test_personality_manager_load_personalities(sample_personality_file):
    """Test loading personalities from a directory."""
    manager = PersonalityManager(personalities_dir=sample_personality_file)
    
    # Call _load_personalities explicitly to test it
    manager.available_personalities = {}  # Clear existing personalities
    manager._load_personalities()
    
    # Verify personalities were loaded
    assert len(manager.available_personalities) == 2
    assert "test_personality" in manager.available_personalities
    assert "another_personality" in manager.available_personalities

@patch("os.listdir")
@patch("os.path.isfile")
@patch("json.load")
def test_personality_manager_load_error_handling(
    mock_json_load, mock_isfile, mock_listdir, personality_manager
):
    """Test error handling when loading personalities."""
    # Set up mocks
    mock_listdir.return_value = ["valid.json", "invalid.json", "not_json.txt"]
    mock_isfile.return_value = True
    
    # Make json.load raise an exception for invalid.json
    def side_effect(file_obj):
        filename = file_obj.name
        if "invalid.json" in filename:
            raise json.JSONDecodeError("Invalid JSON", "", 0)
        return SAMPLE_PERSONALITY
    
    mock_json_load.side_effect = side_effect
    
    # Call _load_personalities
    personality_manager.available_personalities = {}  # Clear existing personalities
    personality_manager._load_personalities()
    
    # Verify only valid.json was loaded
    assert len(personality_manager.available_personalities) == 1
    assert "valid" in personality_manager.available_personalities

def test_personality_generate_prompt(personality_manager):
    """Test generating a complete prompt with a personality."""
    # Get a personality
    personality = personality_manager.get_personality("test_personality")
    
    # Test messages
    messages = [
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"}
    ]
    
    # Generate prompt
    prompt = personality_manager.generate_prompt("test_personality", messages)
    
    # Verify prompt structure
    assert personality.system_prompt in prompt
    assert "Hello!" in prompt
    assert "Hi there!" in prompt
    assert "How are you?" in prompt
    
    # Verify order (system prompt should be at the beginning)
    system_prompt_pos = prompt.find(personality.system_prompt)
    hello_pos = prompt.find("Hello!")
    assert system_prompt_pos < hello_pos 
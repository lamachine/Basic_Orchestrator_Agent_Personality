"""
Tests for the personality creator tool.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.sub_graphs.template_agent.src.tools.personality_creator import (
    PersonalityCreator,
    create_personality,
)


@pytest.fixture
def sample_personality_data() -> Dict[str, Any]:
    """Sample personality data for testing."""
    return {
        "name": "Test Agent",
        "role": "assistant",
        "bio": [
            "Test Agent is a helpful AI assistant.",
            "Test Agent is designed to assist with various tasks.",
        ],
        "knowledge": [
            "Test Agent knows about testing.",
            "Test Agent understands test scenarios.",
        ],
        "limitations": [
            "Test Agent cannot modify its own code.",
            "Test Agent cannot access external systems.",
        ],
        "topics": ["Testing", "Documentation", "Code Review"],
        "style": {
            "all": [
                "Test Agent is professional and precise.",
                "Test Agent uses clear, technical language.",
            ],
            "chat": [
                "In chat, Test Agent is concise and direct.",
                "Test Agent maintains a professional tone.",
            ],
            "post": [
                "In posts, Test Agent is thorough and detailed.",
                "Test Agent includes relevant technical details.",
            ],
        },
        "adjectives": ["precise", "professional", "helpful", "technical"],
        "people": ["Test User", "Test Developer"],
        "aliases": ["TestBot", "TestAssistant"],
    }


def test_create_personality(sample_personality_data: Dict[str, Any], tmp_path: Path):
    """Test creating a personality configuration."""
    # Create personality
    personality = create_personality(
        name=sample_personality_data["name"],
        role=sample_personality_data["role"],
        bio=sample_personality_data["bio"],
        knowledge=sample_personality_data["knowledge"],
        limitations=sample_personality_data["limitations"],
        topics=sample_personality_data["topics"],
        style=sample_personality_data["style"],
        adjectives=sample_personality_data["adjectives"],
        people=sample_personality_data["people"],
        aliases=sample_personality_data["aliases"],
        output_path=str(tmp_path / "test_personality.json"),
    )

    # Verify basic structure
    assert personality["name"] == sample_personality_data["name"]
    assert personality["role"] == sample_personality_data["role"]
    assert personality["bio"] == sample_personality_data["bio"]
    assert personality["knowledge"] == sample_personality_data["knowledge"]
    assert personality["limitations"] == sample_personality_data["limitations"]
    assert personality["topics"] == sample_personality_data["topics"]
    assert personality["style"] == sample_personality_data["style"]
    assert personality["adjectives"] == sample_personality_data["adjectives"]
    assert personality["people"] == sample_personality_data["people"]
    assert personality["aliases"] == sample_personality_data["aliases"]

    # Verify file was created
    assert (tmp_path / "test_personality.json").exists()

    # Verify file contents
    with open(tmp_path / "test_personality.json", "r") as f:
        saved_personality = json.load(f)
    assert saved_personality == personality


def test_validate_personality(sample_personality_data: Dict[str, Any]):
    """Test personality validation."""
    creator = PersonalityCreator()

    # Test valid personality
    personality = creator.create_personality(**sample_personality_data)
    errors = creator.validate_personality(personality)
    assert not errors

    # Test missing required field
    invalid_personality = personality.copy()
    del invalid_personality["name"]
    errors = creator.validate_personality(invalid_personality)
    assert "Missing required field: name" in errors

    # Test empty required field
    invalid_personality = personality.copy()
    invalid_personality["bio"] = []
    errors = creator.validate_personality(invalid_personality)
    assert "Empty required field: bio" in errors

    # Test invalid style structure
    invalid_personality = personality.copy()
    del invalid_personality["style"]["all"]
    errors = creator.validate_personality(invalid_personality)
    assert "Missing required style key: all" in errors


def test_generate_example_interaction(sample_personality_data: Dict[str, Any]):
    """Test generating example interactions."""
    creator = PersonalityCreator()
    personality = creator.create_personality(**sample_personality_data)

    interaction = creator.generate_example_interaction(personality)

    # Verify interaction structure
    assert len(interaction) == 2
    assert interaction[0]["user"] == "{{user1}}"
    assert interaction[1]["user"] == personality["name"]
    assert "content" in interaction[0]
    assert "content" in interaction[1]
    assert "text" in interaction[0]["content"]
    assert "text" in interaction[1]["content"]

    # Verify interaction content
    assert f"Hello {personality['name']}" in interaction[0]["content"]["text"]
    assert f"As your {personality['role']}" in interaction[1]["content"]["text"]


def test_export_personality(sample_personality_data: Dict[str, Any], tmp_path: Path):
    """Test exporting personality configuration."""
    creator = PersonalityCreator()
    personality = creator.create_personality(**sample_personality_data)

    # Test default output path
    output_path = creator.export_personality(personality)
    assert output_path.endswith(
        f"Character_{personality['name'].replace(' ', '_')}_{personality['role']}.json"
    )

    # Test custom output path
    custom_path = str(tmp_path / "custom_personality.json")
    output_path = creator.export_personality(personality, custom_path)
    assert output_path == custom_path
    assert Path(custom_path).exists()

    # Verify exported content
    with open(custom_path, "r") as f:
        exported = json.load(f)
    assert exported["name"] == personality["name"]
    assert exported["role"] == personality["role"]
    assert "_metadata" in exported
    assert "created_at" in exported["_metadata"]
    assert "template_version" in exported["_metadata"]
    assert "exported_at" in exported["_metadata"]

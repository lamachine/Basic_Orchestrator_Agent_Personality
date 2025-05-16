import pytest
import asyncio
from src.sub_graphs.template_agent.template_tool import template_tool

@pytest.mark.asyncio
async def test_create_character():
    # Simulate a request to create a character
    task = "create_character"
    parameters = {
        "name": "Test Character",
        "role": "test_role",
        "bio": ["Test bio"],
        "knowledge": ["Test knowledge"],
        "limitations": ["Test limitation"],
        "topics": ["Test topic"],
        "style": {"all": ["Test style"]},
        "adjectives": ["Test adjective"],
        "people": ["Test person"],
        "aliases": ["Test alias"],
        "output_path": "src/agents/Test_Character.json"
    }
    request_id = "test_request_id"

    # Call the template_tool
    response = await template_tool(task, parameters, request_id)

    # Verify the response
    assert response["status"] == "success"
    assert "Test Character" in response["message"]
    assert response["request_id"] == request_id
    assert "data" in response
    assert response["data"]["name"] == "Test Character" 
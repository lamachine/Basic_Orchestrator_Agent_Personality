"""Tests for the archon_coder advisor agent."""

import pytest
import json
from unittest.mock import AsyncMock, patch

from src.tools.archon_coder.agents.advisor.advisor_agent import AdvisorAgent, AdvisorDeps
from src.tools.archon_coder.state.agent_builder_state import AgentSpec
from src.services.llm_services import LLMService

# Test data
SAMPLE_SPEC = {
    "name": "test_agent",
    "description": "A test agent for unit testing",
    "tools": ["tool1", "tool2"],
    "system_prompt": "You are a test agent",
    "model_name": "gpt-3.5-turbo"
}

SAMPLE_TOOLS = ["tool1", "tool2", "tool3"]

@pytest.fixture
def mock_services():
    """Create mock services for testing."""
    llm = AsyncMock(spec=LLMService)
    llm.generate = AsyncMock()
    db = AsyncMock()
    return llm, db

@pytest.fixture
async def advisor(mock_services):
    """Create an advisor agent with mocked services."""
    llm, db = mock_services
    with patch('src.services.llm_services.get_llm_service', return_value=llm), \
         patch('src.services.db_services.get_db_service', return_value=db):
        agent = AdvisorAgent()
        yield agent

class TestAdvisorBasics:
    """Basic functionality tests for the advisor agent."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, advisor):
        """Test advisor agent initializes correctly."""
        assert isinstance(advisor, AdvisorAgent)
        assert advisor.llm_service is not None
        assert advisor.db is not None

class TestAdvisorAnalysis:
    """Tests for the advisor's analysis capabilities."""
    
    @pytest.mark.asyncio
    async def test_analyze_requirements_success(self, advisor, mock_services):
        """Test successful analysis of user requirements."""
        llm, _ = mock_services
        llm.generate.side_effect = [
            "Initial analysis",
            json.dumps(SAMPLE_SPEC)
        ]
        
        result = await advisor.analyze_requirements("Create a task management agent")
        
        assert isinstance(result, AgentSpec)
        assert result.name == "test_agent"
        assert len(result.tools) == 2
        assert llm.generate.call_count == 2

    @pytest.mark.asyncio
    async def test_analyze_requirements_handles_bad_json(self, advisor, mock_services):
        """Test handling of invalid JSON in analysis."""
        llm, _ = mock_services
        llm.generate.side_effect = [
            "Analysis",
            "Not valid JSON"
        ]
        
        result = await advisor.analyze_requirements("Create an agent")
        
        assert isinstance(result, AgentSpec)
        assert result.name == "unnamed_agent"  # Should use fallback values

class TestAdvisorToolSuggestions:
    """Tests for the advisor's tool suggestion capabilities."""
    
    @pytest.mark.asyncio
    async def test_suggest_tools_success(self, advisor, mock_services):
        """Test successful tool suggestion."""
        llm, _ = mock_services
        llm.generate.return_value = json.dumps(SAMPLE_TOOLS)
        spec = AgentSpec(**SAMPLE_SPEC)
        
        result = await advisor.suggest_tools(spec)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(tool, str) for tool in result)

    @pytest.mark.asyncio
    async def test_suggest_tools_handles_failure(self, advisor, mock_services):
        """Test handling of tool suggestion failures."""
        llm, _ = mock_services
        llm.generate.return_value = "Not a JSON array"
        spec = AgentSpec(**SAMPLE_SPEC)
        
        result = await advisor.suggest_tools(spec)
        
        assert isinstance(result, list)
        assert len(result) == 0  # Should return empty list on failure

class TestAdvisorIntegration:
    """Integration tests for the advisor agent."""
    
    @pytest.mark.asyncio
    async def test_complete_flow(self, advisor, mock_services):
        """Test the complete advisor workflow."""
        llm, _ = mock_services
        llm.generate.side_effect = [
            "Analysis",
            json.dumps(SAMPLE_SPEC),
            json.dumps(SAMPLE_TOOLS),
            "You are a test agent"
        ]
        
        result = await advisor.run("Create a task management agent")
        
        assert result["status"] == "success"
        assert "spec" in result
        assert isinstance(result["spec"], dict)
        assert llm.generate.call_count == 4

    @pytest.mark.asyncio
    async def test_handles_llm_failure(self, advisor, mock_services):
        """Test handling of LLM service failure."""
        llm, _ = mock_services
        llm.generate.side_effect = Exception("LLM unavailable")
        
        result = await advisor.run("Create an agent")
        
        assert result["status"] == "error"
        assert "LLM unavailable" in result["message"]
        assert result["spec"] is None 
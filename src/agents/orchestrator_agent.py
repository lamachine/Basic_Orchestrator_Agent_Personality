"""Orchestrator Agent - Central coordinator for the agent ecosystem (minimal, no tools, no personality)."""

from typing import Dict, Any, Optional, List
from datetime import datetime

from src.agents.base_agent import BaseAgent
from src.config import Configuration
from src.services.logging_service import get_logger
# from src.agents.personality_agent import PersonalityAgent  # (stubbed for future use)
# from src.state.state_models import MessageRole  # (stubbed for future use)
# from src.tools.tool_processor import ToolProcessor  # (stubbed for future use)

# Initialize logger
logger = get_logger(__name__)

class OrchestratorAgent(BaseAgent):
    """
    Minimal orchestrator agent: coordinates user requests, chats via LLM, and logs interactions.
    No tool or personality logic.
    """
    
    def __init__(self, config: Configuration):
        """Initialize the orchestrator agent.
        
        Args:
            config: System configuration
        """
        super().__init__(
            name="orchestrator",
            api_url=config.llm.api_url,
            model=config.llm.default_model,
            config=config
        )
        self.conversation_history: List[Dict[str, Any]] = []
        # --- Personality agent wrapping stub ---
        # self.agent = PersonalityAgent(
        #     base_agent=self,
        #     personality_file="src/agents/Character_Ronan_valet_orchestrator.json"
        # )
    
    async def process_message(self, message: str, session_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process an incoming user message (chat only, no tools).
        
        Args:
            message: The user's message
            session_state: Optional session state for tracking
        Returns:
            Dict containing the response
        """
        # Create prompt (no tool or personality context)
        prompt = self._create_prompt(message)
        
        # Get LLM response
        response = await self.query_llm(prompt)
        
        # Log the interaction
        logger.debug(f"User message: {message}")
        logger.debug(f"LLM response: {response}")
        
        # Format final response (no tool results)
        final_response = response
        
        # Update conversation history
        self._update_history(message, final_response)

        # Log the response being sent to CLI
        logger.info(f"Sending response to CLI: {final_response}")

        return {
            "response": final_response
        }
    
    def _create_prompt(self, message: str) -> str:
        """Create the prompt for the LLM (no tool/personality context)."""
        # Add conversation history context
        context = ""
        if self.conversation_history:
            history = "\n".join([
                f"User: {msg['user']}\nAssistant: {msg['assistant']}"
                for msg in self.conversation_history[-3:]
            ])
            context += f"\n\nRecent conversation:\n{history}"
        prompt = f"{context}\n\nUser: {message}\nAssistant:"
        return prompt
    
    def _update_history(self, user_message: str, assistant_response: str):
        """Update conversation history."""
        self.conversation_history.append({
            "user": user_message,
            "assistant": assistant_response,
            "timestamp": datetime.now().isoformat()
        })
        # Keep only last 10 messages
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

    # --- Tool logic stubs for future re-addition ---
    # def _handle_tool_calls(self, ...):
    #     """Stub for tool call handling (to be re-added)."""
    #     pass
    # def _extract_tool_calls(self, ...):
    #     """Stub for tool call extraction (to be re-added)."""
    #     pass
    # def _format_response(self, ...):
    #     """Stub for tool result formatting (to be re-added)."""
    #     pass
    # --- Personality agent logic stub for future re-addition ---
    # def _inject_personality(self, prompt: str) -> str:
    #     """Stub for personality injection (to be re-added)."""
    #     return self.agent.inject_personality_into_prompt(prompt)

def orchestrator_node(state) -> Dict[str, Any]:
    return {}

# For direct execution testing
if __name__ == "__main__":
    logger.debug("Testing OrchestratorAgent initialization...")
    orchestrator = OrchestratorAgent()
    logger.debug(f"Orchestrator initialized with model: {orchestrator.model}")
    logger.debug("Try running 'python -m src.run_cli' to start the CLI interface.")
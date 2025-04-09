import json
from dotenv import load_dotenv
import requests
import os
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Local imports
from src.services.db_services.db_manager import DatabaseManager
from src.config import Configuration
from src.config.logging_config import setup_logging

# Load environment variables
load_dotenv(override=True)

# Setup basic logging
logger = logging.getLogger(__name__)

# Load common configuration
config = Configuration()

# Setup logging
try:
    # Initialize logging
    file_handler, console_handler = setup_logging(config)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info("Logging initialized successfully")
except Exception as e:
    print(f"Error setting up logging: {e}")
    # Setup basic logging as fallback
    logging.basicConfig(level=logging.INFO)

class LLMQueryAgent:
    def __init__(self, config: Configuration = config):
        """Initialize the LLM Query Agent with configuration."""
        # Configuration
        self.config = config
        self.api_url = config.ollama_api_url + '/api/generate'
        self.model = config.ollama_model
        
        # Initialize database
        try:
            self.db = DatabaseManager()
            self.has_db = True
            logger.info(f"Database initialized successfully")
        except Exception as e:
            error_msg = f"Database initialization failed: {e}"
            logger.error(error_msg)
            print(error_msg)
            self.has_db = False
        
        # Session tracking
        self.session_id = None
        self.user_id = str(uuid.uuid4())
        
        # Print configuration for debugging
        logger.info(f"Initializing LLM Agent with model: {self.model}")
        logger.info(f"API URL: {self.api_url}")
        logger.info(f"Database available: {self.has_db}")
        print(f"Initializing LLM Agent with model: {self.model}")
        print(f"API URL: {self.api_url}")
        print(f"Database available: {self.has_db}")
    
    def generate_prompt(self, user_input: str) -> str:
        """Generate a simple prompt for the LLM."""
        logger.debug(f"Generating prompt for input: {user_input[:50]}...")
        return f"User: {user_input}\nAgent:"

    def start_conversation(self):
        """Start a new conversation if database is available."""
        if self.has_db:
            try:
                self.session_id = self.db.create_conversation(self.user_id)
                logger.info(f"Started conversation with session ID: {self.session_id}")
                print(f"Started conversation with session ID: {self.session_id}")
                return True
            except Exception as e:
                error_msg = f"Failed to start conversation: {e}"
                logger.error(error_msg)
                print(error_msg)
        return False
        
    def get_conversation_context(self) -> str:
        """Get conversation context if database is available."""
        if not self.has_db or not self.session_id:
            return ""
            
        try:
            recent_messages = self.db.get_recent_messages(self.session_id)
            logger.debug(f"Retrieved {len(recent_messages)} messages for context")
            return "\n".join([f"{msg['role']}: {msg['message']}" for msg in recent_messages])
        except Exception as e:
            error_msg = f"Failed to get conversation context: {e}"
            logger.error(error_msg)
            print(error_msg)
            return ""

    def query_llm(self, prompt: str) -> str:
        """Send a query to the LLM via Ollama API and return the response."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            # LLM call via Ollama API
            logger.info(f"Querying LLM model: {self.model}")
            logger.debug(f"Prompt (first 50 chars): {prompt[:50]}...")
            
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            response_text = response.json().get('response', 'No response from LLM')
            
            logger.info(f"Received response from LLM (length: {len(response_text)})")
            logger.debug(f"Response (first 50 chars): {response_text[:50]}...")
            
            return response_text
        except Exception as e:
            error_msg = f"Error querying LLM: {str(e)}"
            logger.error(error_msg)
            return error_msg
            
    def chat(self, user_input: str) -> str:
        """Full chat flow with database integration if available."""
        logger.info(f"Processing chat input (length: {len(user_input)})")
        
        # Start conversation if needed
        if self.has_db and not self.session_id:
            self.start_conversation()
            
        # Store user message if DB available
        if self.has_db and self.session_id:
            try:
                # Always provide metadata to satisfy NOT NULL constraints
                user_metadata = {
                    "type": "user_message", 
                    "timestamp": datetime.now().isoformat(),
                    "agent_id": "llm_query_agent",
                    "session": str(self.session_id)
                }
                self.db.add_message(self.session_id, "user", user_input, metadata=user_metadata)
                logger.info(f"Stored user message in database")
            except Exception as e:
                error_msg = f"Failed to store user message: {e}"
                logger.error(error_msg)
                print(error_msg)
        
        # Get conversation context if available
        context = self.get_conversation_context()
        
        # Generate prompt and query LLM
        prompt = self.generate_prompt(user_input)
        response_text = self.query_llm(prompt)
        
        # Store assistant message if DB available
        if self.has_db and self.session_id:
            try:
                # Always provide metadata to satisfy NOT NULL constraints
                assistant_metadata = {
                    "type": "assistant_response", 
                    "timestamp": datetime.now().isoformat(),
                    "agent_id": "llm_query_agent",
                    "model": self.model,
                    "session": str(self.session_id)
                }
                self.db.add_message(self.session_id, "assistant", response_text, metadata=assistant_metadata)
                logger.info(f"Stored assistant response in database")
            except Exception as e:
                error_msg = f"Failed to store assistant message: {e}"
                logger.error(error_msg)
                print(error_msg)
                
        return response_text

def main():
    """Main function to run the LLM agent in a chat loop."""
    agent = LLMQueryAgent()
    logger.info("Starting LLM Agent CLI")
    print("Initializing LLM Agent...")
    print("You can start chatting with the agent. Type 'exit' to quit.")
    
    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ['exit', 'quit', 'bye']:
            logger.info("User requested exit. Shutting down.")
            print("Goodbye!")
            break
            
        # Use the full chat flow
        logger.info("Processing user input")
        response = agent.chat(user_input)
        logger.info("Received response from agent")
        print(f"\nAgent: {response}")

if __name__ == "__main__":
    main() 
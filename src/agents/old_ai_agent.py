import json
import requests
import random
import os
from typing import Dict, Any, List
from dotenv import load_dotenv
from db_manager import DatabaseManager
import uuid

# Load environment variables
load_dotenv(override=True)

class JarvisAgent:
    def __init__(self):
        self.character = self.load_character()
        self.api_url = os.getenv('OLLAMA_API_URL') + '/api/generate'
        self.model = os.getenv('OLLAMA_MODEL')
        self.db = DatabaseManager()
        self.session_id = None
        self.user_id = str(uuid.uuid4())  # Generate unique user ID
        
    def load_character(self) -> Dict[str, Any]:
        character_file = os.getenv('CHARACTER_FILE')
        with open(character_file, 'r') as f:
            return json.load(f)
    
    def get_random_elements(self, items: List[str], num: int = 2) -> str:
        """Get random elements from a list and join them."""
        return " ".join(random.sample(items, min(num, len(items))))
    
    def generate_prompt(self, user_input: str, context: str = "") -> str:
        # Create a richer context using character attributes
        bio_context = self.get_random_elements(self.character['bio'])
        lore_context = self.get_random_elements(self.character['lore'])
        style_context = self.get_random_elements(self.character['style']['all'])
        chat_style = self.get_random_elements(self.character['style']['chat'], 1)
        
        personality_context = (
            f"You are {self.character['name']}. {bio_context}\n"
            f"Background: {lore_context}\n"
            f"Style instructions: {style_context}\n{chat_style}\n"
            f"Topics of expertise: {', '.join(random.sample(self.character['topics'], 3))}\n"
            f"Personality traits: {', '.join(random.sample(self.character['adjectives'], 3))}"
        )
        return f"{personality_context}\n\nUser: {user_input}\nJarvis:"

    def start_conversation(self):
        self.session_id = self.db.create_conversation(self.user_id)
        
    def get_conversation_context(self) -> str:
        if not self.session_id:
            return ""
        recent_messages = self.db.get_recent_messages(self.session_id)
        return "\n".join([f"{msg['role']}: {msg['message']}" for msg in recent_messages])

    def chat(self, user_input: str) -> str:
        if not self.session_id:
            self.start_conversation()
            
        print("Processing your request, sir...")
        
        # Store user message
        self.db.add_message(self.session_id, "user", user_input)
        
        # Get conversation context
        context = self.get_conversation_context()
        
        payload = {
            "model": self.model,
            "prompt": self.generate_prompt(user_input, context),
            "stream": False
        }
        
        try:
            # LLM call via Ollama API
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            response_text = response.json()['response']
            
            # Store assistant message
            self.db.add_message(self.session_id, "assistant", response_text)
            
            return response_text
        except Exception as e:
            return f"I apologize, sir, but I've encountered an error: {str(e)}"

def main():
    jarvis = JarvisAgent()
    print("Initializing J.A.R.V.I.S...")
    print("At your service, sir. How may I assist you today?")
    
    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("Very well, sir. Do let me know if you require anything further.")
            break
            
        response = jarvis.chat(user_input)
        print(f"\nJarvis: {response}")

if __name__ == "__main__":
    main() 
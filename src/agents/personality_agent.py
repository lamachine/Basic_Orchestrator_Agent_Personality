"""
Personality Agent Module.

Provides personality integration for agents, allowing characters to be defined in JSON files and their traits to be applied to agent interactions.
"""

import json
import os
import random
from typing import Dict, Any, List, Optional, Set

class PersonalityAgent:
    """
    Wraps a base agent and injects personality traits from a JSON file.
    """
    agent: Any
    personality_file: str
    personality: Dict[str, Any]
    used_knowledge: Set[str]
    used_lore: Set[str]
    last_context: Optional[str]

    def __init__(self, base_agent: Any, personality_file: str):
        """
        Args:
            base_agent: The agent to wrap. Can be None if only used for personality info.
            personality_file: Path to the personality JSON file.
        """
        self.agent = base_agent
        self.personality_file = personality_file
        self.personality = self._load_personality(personality_file)
        
        # Only set up passthrough attributes if we have a base agent
        if base_agent is not None:
            self._setup_passthrough_attributes()
            
        self.used_knowledge = set()
        self.used_lore = set()
        self.last_context = None

    def _load_personality(self, file_path: str) -> Dict[str, Any]:
        """
        Load personality data from JSON file, or return default if not found/invalid.
        """
        try:
            if not os.path.exists(file_path):
                return self._create_default_personality()
            with open(file_path, 'r', encoding='utf-8') as f:
                personality = json.load(f)
            for field in ['name', 'bio', 'style']:
                if field not in personality:
                    personality[field] = self._get_default_for_field(field)
            return personality
        except Exception:
            return self._create_default_personality()

    def _create_default_personality(self) -> Dict[str, Any]:
        """Return a default personality."""
        return {
            "name": "Assistant",
            "bio": ["A helpful AI assistant"],
            "style": {"chat": ["Responds in a helpful, accurate manner."]},
            "limitations": ["Cannot access the physical world"],
            "knowledge": [],
            "lore": []
        }

    def _get_default_for_field(self, field: str) -> Any:
        defaults = {
            "name": "Assistant",
            "bio": ["A helpful AI assistant"],
            "style": {"chat": ["Responds in a helpful, accurate manner."]},
            "limitations": ["Cannot access the physical world"],
            "knowledge": [],
            "lore": [],
            "people": []
        }
        return defaults.get(field, [])

    def _setup_passthrough_attributes(self):
        """Pass through key attributes and methods to the base agent."""
        for attr in ['conversation_id', 'session_id', 'user_id', 'orchestrator', 'state_manager']:
            if hasattr(self.agent, attr):
                setattr(self, attr, getattr(self.agent, attr))
        for method in ['set_conversation_id', 'process_user_input']:
            if hasattr(self.agent, method):
                setattr(self, method, getattr(self.agent, method))

    def get_name(self) -> str:
        """Return the personality name."""
        return self.personality.get("name", "Assistant")

    def create_personality_header(self) -> str:
        """Return a formatted string with core personality traits."""
        p = self.personality
        header = f"You are {p.get('name', 'Assistant')}, {' '.join(p.get('bio', []))}"
        if "style" in p and "chat" in p["style"]:
            header += f"\nStyle: {' '.join(p['style']['chat'])}"
        if "limitations" in p and p["limitations"]:
            header += f"\nLimitations: {' '.join(p['limitations'])}"
        return header

    def get_contextual_personality(self, user_input: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Return relevant personality elements based on context.
        """
        context_parts = []
        knowledge = self._select_relevant_items(self.personality.get("knowledge", []), user_input, conversation_history, 2, self.used_knowledge)
        if knowledge:
            self.used_knowledge.update(knowledge)
            context_parts.append(f"Relevant knowledge: {' '.join(knowledge)}")
        lore = self._select_relevant_items(self.personality.get("lore", []), user_input, conversation_history, 1, self.used_lore)
        if lore:
            self.used_lore.update(lore)
            context_parts.append(f"Background: {' '.join(lore)}")
        people = self._get_relevant_people(user_input, conversation_history)
        if people:
            people_items = [p for p in self.personality.get("people", []) if any(person in p for person in people)]
            if people_items:
                context_parts.append(f"People mentioned: {' '.join(people_items[:2])}")
        self.last_context = "\n\n".join(context_parts)
        return self.last_context

    def _select_relevant_items(self, items: List[str], user_input: str, conversation_history: Optional[List[Dict[str, Any]]] = None, max_items: int = 2, exclude: Optional[Set[str]] = None) -> List[str]:
        """
        Select items most relevant to the conversation (simple keyword match).
        """
        if not items:
            return []
        exclude = exclude or set()
        available_items = [item for item in items if item not in exclude]
        if not available_items:
            return []
        conversation_text = user_input.lower()
        if conversation_history:
            for msg in conversation_history[-3:]:
                if isinstance(msg, dict) and "content" in msg:
                    conversation_text += " " + msg["content"].lower()
        scores = [(item, len(set(item.lower().split()).intersection(conversation_text.split()))) for item in available_items]
        scores.sort(key=lambda x: x[1], reverse=True)
        if scores and scores[0][1] == 0:
            selected = [random.choice(available_items)]
        else:
            selected = [item for item, score in scores[:max_items] if score > 0]
        return selected[:max_items]

    def _get_relevant_people(self, user_input: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """
        Return names of people mentioned in the conversation.
        """
        all_people = self.personality.get("people", [])
        if not all_people:
            return []
        first_names = [person.split(',')[0].strip().split()[0].strip() for person in all_people]
        text = user_input.lower()
        if conversation_history:
            for msg in conversation_history[-2:]:
                if isinstance(msg, dict) and "content" in msg:
                    text += " " + msg["content"].lower()
        return [name for name in first_names if name.lower() in text]

    def inject_personality_into_prompt(self, prompt: str) -> str:
        """
        Inject personality elements into a prompt.
        """
        personality_header = self.create_personality_header()
        # Add personality traits after the system prompt but before the conversation
        lines = prompt.split('\n\n')
        if len(lines) > 1:
            # Insert personality after system prompt but before conversation
            return f"{lines[0]}\n\n{personality_header}\n\n{lines[1]}"
        return f"{personality_header}\n\n{prompt}"

    def should_apply_personality(self, prompt: str) -> bool:
        """
        Return True if personality should be applied to this prompt.
        """
        diagnostic_indicators = [
            "debug report",
            "system check",
            "diagnostic mode",
            "internal state"
        ]
        return not any(indicator in prompt.lower() for indicator in diagnostic_indicators) 
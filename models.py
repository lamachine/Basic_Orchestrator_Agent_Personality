from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Character(BaseModel):
    name: str
    bio: List[str]
    lore: List[str]
    message_examples: List[List[Dict[str, Any]]]
    post_examples: List[str]
    adjectives: List[str]
    topics: List[str]
    style: Dict[str, List[str]]
    knowledge: Optional[List[Dict[str, Any]]] = []

class Message(BaseModel):
    role: str
    message: str
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.now)

class Conversation(BaseModel):
    id: Optional[int] = None
    user_id: str
    messages: List[Message] = []
    created_at: datetime = Field(default_factory=datetime.now) 
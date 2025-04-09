from typing import Dict, Any
from pydantic_settings import BaseSettings

class LLMConfig(BaseSettings):
    """LLM Configuration settings."""
    
    # Ollama settings
    OLLAMA_HOST: str = "http://localhost:11434"
    MODEL_NAME: str = "llama3.1:latest"
    
    # API settings
    API_TIMEOUT: int = 300
    MAX_TOKENS: int = 2000
    TEMPERATURE: float = 0.1
    CONTEXT_LENGTH: int = 16384
    
    class Config:
        env_file = ".env"
        case_sensitive = True 
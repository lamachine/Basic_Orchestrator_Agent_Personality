import os
from dotenv import load_dotenv
from typing import Dict, Any
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
import yaml

load_dotenv()

LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama')
LLM_EMBEDDING_PROVIDER = os.getenv('LLM_EMBEDDING_PROVIDER', 'ollama')

if LLM_PROVIDER == 'ollama':
    OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    LLM_MODEL = os.getenv('OLLAMA_PREFERRED_LLM_MODEL', 'llama3.1:latest')
    EMBEDDING_MODEL = os.getenv('OLLAMA_PREFERRED_EMBEDDING_MODEL', 'nomic-embed-text')

DEFAULT_LLM_CONFIG = {
    'provider': LLM_PROVIDER,
    'api_url': OLLAMA_HOST,
    'default_model': LLM_MODEL,
    'temperature': 0.2,
    'max_tokens': 4096,
    'context_window': 16384,
    'models': {
        'conversation': {
            'model': LLM_MODEL,
            'temperature': 0.7,
            'max_tokens': 2048,
            'system_prompt': 'You are a helpful assistant named Rose.'
        },
        'coding': {
            'model': 'codellama:latest',
            'temperature': 0.2,
            'max_tokens': 16384,
            'system_prompt': 'You are an expert programming assistant.'
        },
        'reasoning': {
            'model': 'deepseek-r1',
            'temperature': 0.3,
            'max_tokens': 16384,
            'system_prompt': 'You are a logical reasoning assistant that thinks step by step.'
        },
        'embedding': {
            'model': EMBEDDING_MODEL,
            'dimensions': 768,
            'normalize': True
        }
    }
}

class LLMConfig(BaseSettings):
    """LLM Configuration settings."""
    provider: str = DEFAULT_LLM_CONFIG['provider']
    api_url: str = DEFAULT_LLM_CONFIG['api_url']
    default_model: str = DEFAULT_LLM_CONFIG['default_model']
    temperature: float = DEFAULT_LLM_CONFIG['temperature']
    max_tokens: int = DEFAULT_LLM_CONFIG['max_tokens']
    context_window: int = DEFAULT_LLM_CONFIG['context_window']
    models: Dict[str, Any] = DEFAULT_LLM_CONFIG['models']

    model_config = ConfigDict(extra='allow')

def get_llm_config() -> LLMConfig:
    """Get the consolidated LLM configuration."""
    # Optionally, load overrides from a YAML file or env vars here
    return LLMConfig() 
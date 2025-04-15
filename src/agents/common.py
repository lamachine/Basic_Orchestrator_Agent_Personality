from dataclasses import dataclass
from dotenv import load_dotenv
import os
import ollama
from supabase import Client
from openai import AsyncOpenAI
from pydantic_ai import Agent, ModelRetry
from pydantic_ai.models.openai import OpenAIModel
from typing import List

load_dotenv()

# LLM Configuration from environment
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama')
LLM_EMBEDDING_PROVIDER = os.getenv('LLM_EMBEDDING_PROVIDER', 'ollama')

# Model selection based on provider
if LLM_PROVIDER == 'ollama':
    OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    LLM_MODEL = os.getenv('OLLAMA_PREFERRED_LLM_MODEL', 'llama3.1:latest')
    EMBEDDING_MODEL = os.getenv('OLLAMA_PREFERRED_EMBEDDING_MODEL', 'nomic-embed-text')
else:
    LLM_MODEL = os.getenv('OPENAI_PREFERRED_LLM_MODEL', 'gpt-4o-mini')
    EMBEDDING_MODEL = os.getenv('OPENAI_PREFERRED_EMBEDDING_MODEL', 'text-embedding-3-small')

@dataclass
class PydanticAIDeps:
    supabase: Client
    openai_client: AsyncOpenAI

async def get_embedding(text: str, openai_client: AsyncOpenAI) -> List[float]:
    """Get embedding vector from OpenAI."""
    try:
        response = await openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0] * 768  # Return zero vector on error

# Initialize model based on provider
if LLM_PROVIDER == 'ollama':
    # Configure Ollama
    ollama.host = OLLAMA_HOST
    
    async def get_ollama_response(messages: list, tools: list = None) -> dict:
        """Get response from Ollama."""
        try:
            return ollama.chat(
                model=LLM_MODEL,
                messages=messages,
                tools=tools,
                options={
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            )
        except Exception as e:
            print(f"Error from Ollama: {e}")
            return {"message": {"content": f"Error: {str(e)}"}}
    model = OpenAIModel(LLM_MODEL)  # Create a model even for Ollama
else:
    model = OpenAIModel(LLM_MODEL)

# Initialize agent
agent = Agent(
    model,
    system_prompt="You are a helpful AI assistant.",
    deps_type=PydanticAIDeps,
    retries=2
) 
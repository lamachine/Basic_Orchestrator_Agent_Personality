from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv(override=True)

class DatabaseConfig(BaseModel):
    host: str = os.getenv('SUPABASE_HOST', 'localhost')
    port: int = int(os.getenv('SUPABASE_PORT', '5432'))
    database: str = os.getenv('SUPABASE_DB', 'postgres')
    user: str = os.getenv('SUPABASE_USER', 'postgres')
    password: str = os.getenv('SUPABASE_PASSWORD', '')
    table_name: str = os.getenv('SUPABASE_TABLE', 'dev_docs_site_pages')

class RAGConfig(BaseModel):
    chunk_size: int = int(os.getenv('RAG_CHUNK_SIZE', '1000'))
    chunk_overlap: int = int(os.getenv('RAG_CHUNK_OVERLAP', '200'))
    max_chunks_per_doc: int = int(os.getenv('RAG_MAX_CHUNKS', '100'))
    similarity_threshold: float = float(os.getenv('RAG_SIMILARITY_THRESHOLD', '0.7'))
    max_context_chunks: int = int(os.getenv('RAG_MAX_CONTEXT_CHUNKS', '5'))

class APIConfig(BaseModel):
    database: DatabaseConfig = DatabaseConfig()
    rag: RAGConfig = RAGConfig()
    default_model: str = os.getenv('DEFAULT_LLM_MODEL', 'gpt-3.5-turbo')
    cache_ttl: int = int(os.getenv('CACHE_TTL', '3600'))  # 1 hour
    rate_limit: int = int(os.getenv('RATE_LIMIT', '100'))  # requests per minute

# Global config instance
config = APIConfig() 
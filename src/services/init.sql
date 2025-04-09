-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at created_atTZ DEFAULT NOW()
);

-- Create messages table
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES conversations(id),
    role TEXT NOT NULL,
    message TEXT NOT NULL,
    embedding(768),
    created_at created_atTZ DEFAULT NOW()
);

-- Create vector index
CREATE INDEX IF NOT EXISTS messages_embedding_idx ON messages 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100); 
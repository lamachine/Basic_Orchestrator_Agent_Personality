-- Initial schema for Basic Orchestrator Agent
-- Migration 001: Create sessions and messages tables

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Sessions table
CREATE TABLE IF NOT EXISTS public.sessions (
    id BIGSERIAL PRIMARY KEY,
    name TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    metadata JSONB DEFAULT '{}'::jsonb,
    user_id TEXT,
    status TEXT DEFAULT 'active',
    last_message_at TIMESTAMPTZ DEFAULT now()
);

-- Messages table
CREATE TABLE IF NOT EXISTS public.messages (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT REFERENCES public.sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    user_id TEXT,
    sender TEXT,
    target TEXT
);

-- Tasks table
CREATE TABLE IF NOT EXISTS public.tasks (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT REFERENCES public.sessions(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    result JSONB,
    error TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON public.sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON public.messages(session_id);
CREATE INDEX IF NOT EXISTS idx_tasks_session_id ON public.tasks(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON public.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON public.messages(created_at DESC);

-- Updated at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers
DROP TRIGGER IF EXISTS update_sessions_updated_at ON public.sessions;
CREATE TRIGGER update_sessions_updated_at
    BEFORE UPDATE ON public.sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- RLS Policies
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;

-- Basic read policies
CREATE POLICY "Enable read access for all users" ON public.sessions FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON public.messages FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON public.tasks FOR SELECT USING (true);

-- Insert policies
CREATE POLICY "Enable insert for authenticated users" ON public.sessions 
    FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable insert for authenticated users" ON public.messages 
    FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable insert for authenticated users" ON public.tasks 
    FOR INSERT WITH CHECK (true);

-- Update policies
CREATE POLICY "Enable update for session owners" ON public.sessions 
    FOR UPDATE USING (true);
CREATE POLICY "Enable update for message owners" ON public.messages 
    FOR UPDATE USING (true);
CREATE POLICY "Enable update for task owners" ON public.tasks 
    FOR UPDATE USING (true); 
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncpg
from pgvector.asyncpg import register_vector
import numpy as np
from src.tools.crawler.common.llm_provider import LLMProvider

app = FastAPI()
llm_provider = LLMProvider()

class QueryRequest(BaseModel):
    query: str
    limit: int = 5
    sources: Optional[List[str]] = None
    threshold: float = 0.7

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    sources: Optional[List[str]] = None
    model: Optional[str] = None

class SearchResult(BaseModel):
    url: str
    title: str
    content: str
    similarity: float
    source: str
    metadata: Dict[str, Any]

async def get_db_connection():
    conn = await asyncpg.connect(
        user='postgres',
        password='your-password',  # Move to env
        database='postgres',
        host='localhost'
    )
    await register_vector(conn)
    return conn

@app.get("/query", response_model=List[SearchResult])
async def semantic_search(request: QueryRequest):
    """
    Perform semantic search against stored documentation
    """
    # Get embedding for query
    query_embedding = await llm_provider.get_embedding(request.query)
    
    # Build SQL query
    sql = """
    SELECT 
        url, title, content, metadata,
        1 - (embedding <=> $1) as similarity
    FROM dev_docs_site_pages
    WHERE 1 - (embedding <=> $1) > $2
    """
    params = [query_embedding, request.threshold]
    
    # Add source filter if specified
    if request.sources:
        sql += " AND metadata->>'source' = ANY($3)"
        params.append(request.sources)
    
    sql += f" ORDER BY similarity DESC LIMIT {request.limit}"
    
    # Execute search
    conn = await get_db_connection()
    try:
        results = await conn.fetch(sql, *params)
        return [
            SearchResult(
                url=row['url'],
                title=row['title'],
                content=row['content'],
                similarity=row['similarity'],
                source=row['metadata'].get('source', 'unknown'),
                metadata=row['metadata']
            )
            for row in results
        ]
    finally:
        await conn.close()

@app.post("/chat")
async def chat_with_context(request: ChatRequest):
    """
    Generate chat completion with RAG context
    """
    # Get relevant documents
    query = request.messages[-1]['content']
    context_docs = await semantic_search(
        QueryRequest(query=query, sources=request.sources)
    )
    
    # Format context
    context = "\n\n".join([
        f"Source: {doc.url}\n{doc.content}"
        for doc in context_docs
    ])
    
    # Add context to system message
    messages = [
        {
            "role": "system",
            "content": f"You are a helpful assistant. Use this context to answer questions:\n\n{context}"
        }
    ] + request.messages
    
    # Get completion
    response = await llm_provider.get_completion(
        messages=messages,
        model=request.model
    )
    
    return {
        "response": response,
        "sources": [doc.url for doc in context_docs]
    } 
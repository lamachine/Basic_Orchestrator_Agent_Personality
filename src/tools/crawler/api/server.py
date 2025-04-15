from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .rag_endpoints import app as rag_app
from .config import config

app = FastAPI(title="RAG API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the RAG endpoints
app.mount("/rag", rag_app)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "config": {
            "database": config.database.dict(exclude={'password'}),
            "rag": config.rag.dict(),
            "rate_limit": config.rate_limit,
            "cache_ttl": config.cache_ttl
        }
    }

# If running standalone
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8084,  # Different port for standalone mode
        reload=True
    ) 
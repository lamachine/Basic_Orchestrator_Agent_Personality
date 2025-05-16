"""
Main FastAPI application.

This module initializes and configures the FastAPI application.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .common.routers import mcp_router
from .common.services.db_service import DBService

# Create FastAPI app
app = FastAPI(
    title="Template Agent",
    description="A template agent that can run as a sub-graph, standalone agent, or MCP server.",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
db_service = DBService()

# Include routers
if os.getenv("USE_AS_MCP_SERVER", "").lower() == "true":
    app.include_router(mcp_router.router)
    print("MCP server mode enabled")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Template Agent API",
        "mode": "MCP Server" if os.getenv("USE_AS_MCP_SERVER", "").lower() == "true" else "Standalone Agent"
    } 
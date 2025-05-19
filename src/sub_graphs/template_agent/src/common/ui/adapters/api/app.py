"""
FastAPI application for the template agent.

This module provides both a class-based interface and direct FastAPI app initialization.
It can be used either way:
1. As a class: APIInterface(agent).start()
2. Directly: uvicorn.run(app, host="0.0.0.0", port=8000)
"""

import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ....common.agents.template_agent import TemplateAgent
from ....managers import SessionManager
from ....routers import mcp_router
from ....services import DBService, LoggingService

logger = LoggingService.get_logger(__name__)


# Pydantic models for API
class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    response: str


class StatusResponse(BaseModel):
    """Response model for status endpoint."""

    status: str
    agent_type: str
    session_id: Optional[str] = None


class APIInterface:
    """FastAPI interface for template agent."""

    def __init__(self, agent: TemplateAgent, session_manager: Optional[SessionManager] = None):
        """
        Initialize API interface.

        Args:
            agent: Template agent instance
            session_manager: Optional session manager instance
        """
        self.agent = agent
        self.session_manager = session_manager
        self.app = FastAPI(
            title="Template Agent",
            description="A template agent that can run as a sub-graph, standalone agent, or MCP server.",
            version="0.1.0",
        )
        self._setup_middleware()
        self._setup_routes()

    def _setup_middleware(self):
        """Setup FastAPI middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self):
        """Setup FastAPI routes."""

        @self.app.post("/chat", response_model=ChatResponse)
        async def chat(request: ChatRequest):
            """Handle chat messages."""
            try:
                response = await self.agent.process_message(request.message)
                return ChatResponse(response=response)
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/status", response_model=StatusResponse)
        async def get_status():
            """Get agent status."""
            return StatusResponse(
                status="running",
                agent_type="template",
                session_id=self.agent.graph_state.get("session_id"),
            )

        @self.app.get("/")
        async def root():
            """Root endpoint."""
            return {
                "message": "Template Agent API",
                "mode": (
                    "MCP Server"
                    if os.getenv("USE_AS_MCP_SERVER", "").lower() == "true"
                    else "Standalone Agent"
                ),
            }

    async def start(self):
        """Start the API server."""
        import uvicorn

        uvicorn.run(self.app, host="0.0.0.0", port=8000)


# Create default FastAPI app for direct use
app = FastAPI(
    title="Template Agent",
    description="A template agent that can run as a sub-graph, standalone agent, or MCP server.",
    version="0.1.0",
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
        "mode": (
            "MCP Server"
            if os.getenv("USE_AS_MCP_SERVER", "").lower() == "true"
            else "Standalone Agent"
        ),
    }

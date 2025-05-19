"""
MCP Router

This module provides FastAPI routes for MCP functionality.
The routes are only enabled when USE_AS_MCP_SERVER is set.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..services.db_service import DBService
from ..services.mcp_service import MCPService

# Create router
router = APIRouter(prefix="/mcp", tags=["mcp"])


# Pydantic models for request validation
class MCPRequest(BaseModel):
    """Model for MCP request parameters."""

    endpoint_name: str
    capability: str
    parameters: Dict[str, Any]
    task_id: Optional[str] = None


# Dependency to get MCP service
async def get_mcp_service(db_service: DBService = Depends()) -> MCPService:
    """Get MCP service instance."""
    return MCPService(db_service)


@router.post("/{capability}")
async def mcp_endpoint(
    capability: str,
    request: MCPRequest,
    mcp_service: MCPService = Depends(get_mcp_service),
) -> Dict[str, Any]:
    """
    Handle MCP requests.

    Args:
        capability: The MCP capability to invoke
        request: The MCP request parameters
        mcp_service: MCP service instance

    Returns:
        Response from the MCP endpoint
    """
    # Call MCP service
    response = await mcp_service.call_mcp(
        endpoint_name=request.endpoint_name,
        capability=capability,
        parameters=request.parameters,
        task_id=request.task_id,
    )

    # Check for errors
    if response.get("status") == "error":
        raise HTTPException(status_code=400, detail=response.get("error", "Unknown error"))

    return response


@router.get("/status/{task_id}")
async def check_status(
    task_id: str, mcp_service: MCPService = Depends(get_mcp_service)
) -> Dict[str, Any]:
    """
    Check the status of an MCP request.

    Args:
        task_id: Task ID to check
        mcp_service: MCP service instance

    Returns:
        Status information for the request
    """
    # Check status
    status = await mcp_service.check_status(task_id)

    # Check for errors
    if status.get("status") == "error":
        raise HTTPException(status_code=400, detail=status.get("error", "Unknown error"))

    return status

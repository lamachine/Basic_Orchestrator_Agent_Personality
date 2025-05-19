"""
Template Agent Routers package.

This package contains API route handlers for the template agent.
"""

from .mcp_router import MCPRouter, RouterConfig

__all__ = ["MCPRouter", "RouterConfig"]

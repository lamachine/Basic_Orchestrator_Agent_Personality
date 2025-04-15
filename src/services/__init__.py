"""
Service layer implementations.
"""

# Attempt to import MCP services if available
try:
    from . import mcp_services
except ImportError:
    # MCP services are optional, so we can continue without them
    pass 
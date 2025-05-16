"""
Template Agent Graphs Module.

This module provides the graph implementations for the template agent.
It exposes the main template graph function and any helper functions needed
for graph construction and management.
"""

from .template_graph import template_graph, apply_personality

__all__ = [
    'template_graph',
    'apply_personality'
] 
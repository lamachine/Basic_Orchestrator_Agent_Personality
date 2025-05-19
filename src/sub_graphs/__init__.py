"""
Sub-graphs package.

This package contains sub-graph agent implementations.
"""

from .email_agent import *
from .personal_assistant_agent import *
from .template_agent import *

__all__ = ["template_agent", "personal_assistant_agent", "email_agent"]

"""Sub-graphs package.

Contains specialized sub-graphs that handle different capabilities:
- valet: Household management, daily schedules, and personal affairs
- librarian: Research, documentation, and knowledge management
- personal_assistant: Communications, task lists, calendar, and personal productivity
"""

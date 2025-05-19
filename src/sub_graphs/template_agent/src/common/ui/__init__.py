"""
Template Agent UI package.

This package contains user interface components for the template agent.
"""

from .adapters import APIInterface, CLIInterface
from .base_interface import BaseInterface

__all__ = ["BaseInterface", "APIInterface", "CLIInterface"]

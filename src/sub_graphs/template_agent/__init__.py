"""
Template Agent package.

This package contains the template agent implementation.
"""

from .src.main import run_with_interface
from .src.main_cli import run_with_cli_interface

__all__ = ["run_with_interface", "run_with_cli_interface"]

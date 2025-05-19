"""
Template Agent source package.

This package contains the core implementation of the template agent.
"""

from .main import run_with_interface
from .main_cli import run_with_cli_interface

__all__ = ["run_with_interface", "run_with_cli_interface"]

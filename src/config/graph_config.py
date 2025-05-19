"""
Graph-level configuration for orchestrator and sub-graphs.

# Most common/preferred: graph_name, system_prompt, graph_type, max_recursion_depth, max_pending_tasks, task_timeout_seconds, default_thinking_format, agents, personality

This module manages graph-level settings for all graphs and orchestrator-specific
settings. Each required feature (llm, tool_registry, db, state, logging, user)
is represented by an explicit config dataclass.
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict

from src.config.llm_config import LLMConfig
from src.config.logging_config import LoggingConfig

# Configure LLM in llm_config.py

# tool registry is already in code


@dataclass
class DBConfig:
    """Configuration for database access."""

    provider: str = "local"  # 'local', 'parent', or 'standalone'
    # If parent, you can remove the following files from the sub-graph:
    # - xxx.py


@dataclass
class StateConfig:
    """Configuration for state management."""

    provider: str = "local"  # 'local', 'parent', or 'standalone'
    # If parent, you can remove the following files from the sub-graph:
    # - xxx.py


# configure logging in logging_config.py


@dataclass
class UserConfig:
    """Configuration for user/role/line-level security."""

    provider: str = "local"  # 'parent' or 'local'
    # Typically only local is only for the top level graph.


@dataclass
class AllGraphsConfig:
    """
    Configuration fields required by all graphs.
    Each required feature is an explicit config dataclass.
    """

    graph_name: str = "orchestrator_graph"
    system_prompt: str = (
        "You are a helpful AI agent administering a range of tools. "
        "All messages to and replies from tools to the LLM will be in JSON tool command formats."
    )
    llm: LLMConfig = field(default_factory=LLMConfig)
    # tool_registry: ToolRegistryConfig = field(default_factory=ToolRegistryConfig)  # Removed, handled dynamically
    db: DBConfig = field(default_factory=DBConfig)
    state: StateConfig = field(default_factory=StateConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    user: UserConfig = field(default_factory=UserConfig)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_name": self.graph_name,
            "system_prompt": self.system_prompt,
            "llm": self.llm.__dict__,
            "tool_registry": self.tool_registry.__dict__,
            "db": self.db.__dict__,
            "state": self.state.__dict__,
            "logging": self.logging.__dict__,
            "user": self.user.__dict__,
        }


@dataclass
class OrchestratorConfig(AllGraphsConfig):
    """
    Orchestrator-specific configuration fields and overrides.
    Sets all options and settings as currently functioning in orchestrator.
    """

    graph_name: str = "orchestrator_graph"
    system_prompt: str = (
        "You are the orchestrator for a team of agents arranged in a hierarchy. "
        "Your role is to communicate with the user, assign tasks to tools/sub-agents, "
        "and coordinate the entire stack. "
        "All toolmessages to and from the LLM must be in JSON tool command format."
        "All conversation messages to and from the user must be in natural language."
    )


# --- Example instantiation (commented out) ---
# Template config for a new sub-graph:
# template_config = AllGraphsConfig()
#
# Orchestrator config (as used in the main orchestrator):
# orchestrator_config = OrchestratorConfig()

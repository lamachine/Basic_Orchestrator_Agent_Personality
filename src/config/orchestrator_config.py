"""
Orchestrator and agent configuration for the application.

# Most common/preferred: graph_type, max_recursion_depth, max_pending_tasks, task_timeout_seconds, default_thinking_format, agents
"""

import os
from typing import Any, Dict

import yaml
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    enabled: list = Field(default_factory=lambda: ["librarian", "valet", "personal_assistant"])
    librarian: Dict[str, Any] = Field(
        default_factory=lambda: {"use_web_search": True, "max_references": 5}
    )
    valet: Dict[str, Any] = Field(default_factory=lambda: {"check_frequency_seconds": 300})
    personal_assistant: Dict[str, Any] = Field(default_factory=lambda: {"default_timezone": "UTC"})


class OrchestratorConfig(BaseModel):
    graph_type: str = "standard"
    max_recursion_depth: int = 3
    max_pending_tasks: int = 10
    task_timeout_seconds: int = 300
    default_thinking_format: str = "steps"
    agents: AgentConfig = Field(default_factory=AgentConfig)


def get_orchestrator_config(
    config_path: str = "src/config/developer_user_config.yaml",
) -> OrchestratorConfig:
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
        orchestrator_section = config.get("orchestrator", {})
        agents_section = config.get("agents", {})
        return OrchestratorConfig(**orchestrator_section, agents=AgentConfig(**agents_section))
    return OrchestratorConfig()

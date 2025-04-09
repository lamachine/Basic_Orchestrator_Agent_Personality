# Imports
from __future__ import annotations as _annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict


from devtools import debug
from httpx import AsyncClient

from pydantic_ai import Agent, ModelRetry, RunContext


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ..utils_folder.utils_copy import get_model, get_db

# Cofiguration
model= get_model()
db = get_db()
logger = logging.getLogger(__name__)

# Dependencies
@dataclass
class Agent_Template_Dependencies:
    # Agent properties
    name: str
    api_keys: Dict[str, str]
    database_connections: Dict[str, str]
    custom_properties: Any # i.e. personality, user, etc.

# Agent system prompt
# text about when to use the model
agent_template_system_prompts=( # Rules and tools for the agent
    # who it is, what it is supposed to accomplish,
    # what tools it has to do it
    """
    You are an agent template.  You will help check that new agents
    meet the standard patterns for pydantic agents.

    Use tool 1 to check the agent's deps.

    Use tool 2 to check the agent's tools.

    You are given what you need in context.

    Always explain your reasoning.

    Format your responses clearly and concisely with the needed details.add()

    Always/Never request additional information from the user.
    """
)

# Agent Definition
agent_template_agent = Agent(
    'llm_source:llm_model',
    system_prompt=agent_template_system_prompts,
    deps_type= Agent_Template_Dependencies,
    # Other parameters Pydandic offers for Agent options
    retries=2,
    timeout=10
)

#  Tool definitions
@agent_template_agent.tool
async def tool_1(
    ctx: RunContext[Agent_Template_Dependencies], # spot to add variables 
    other_param: str # other stuff the llm needs when the tool is called
) -> dict[str, float, dict]: # type hinting for the return value
    # Doc String tells when and how to use the tool
    """Basic tool definition, other items as needed.

    Args:
        Arg1: First input argument
        Arg2: Second input argument

    Returns:
        Return1: The string that matches type hint 1
        Return2: The float that matches type hint 2
        Return3: The dictionary that matches type hint 3
    
    Examples:
    """
    # Code goes here
    return {
        'Return1': 'string',
        'Return2': 1.0,
        'Return3': {'key': 'value'}
    }

@agent_template_agent.tool
async def tool_2(
    ctx: RunContext[Agent_Template_Dependencies],
    other_param: str
) -> dict[str, float, dict]:

# You can test and interact with this agent directly from the command line
# with agent_cli.py  The complexity in that file is for streaming the output
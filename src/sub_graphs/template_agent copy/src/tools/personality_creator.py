"""
Personality Creator Tool.

This module provides tools for creating and managing AI personalities
based on the template structure.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base_tool import BaseTool
from .template_tool_mods import (
    template_tool_decorator,
    validate_template_parameters,
    format_template_response,
    handle_template_error
)

from ..services.logging_service import get_logger

logger = get_logger(__name__)

class PersonalityCreator(BaseTool):
    """Tool for creating and managing AI personalities."""
    
    def __init__(self):
        """Initialize the personality creator tool."""
        super().__init__(
            name="personality_creator",
            description="Creates and manages AI personalities based on templates"
        )
    
    @template_tool_decorator
    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute the personality creator tool.
        
        Args:
            parameters: Tool parameters
            context: Optional context information
            
        Returns:
            Dict containing the execution result
        """
        try:
            # Validate parameters
            errors = validate_template_parameters(parameters)
            if errors:
                return handle_template_error(ValueError("\n".join(errors)))
            
            # Create personality
            personality = self.create_personality(**parameters)
            
            # Export if output path provided
            if 'output_path' in parameters:
                self.export_personality(personality, parameters['output_path'])
            
            return personality
            
        except Exception as e:
            return handle_template_error(e)
    
    def create_personality(
        self,
        name: str,
        role: str,
        bio: List[str],
        knowledge: List[str],
        limitations: List[str],
        topics: List[str],
        style: Dict[str, List[str]],
        adjectives: List[str],
        people: List[str],
        aliases: List[str],
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new personality configuration.
        
        Args:
            name: Personality name
            role: Personality role
            bio: List of bio statements
            knowledge: List of knowledge areas
            limitations: List of limitations
            topics: List of topics
            style: Style guidelines
            adjectives: List of adjectives
            people: List of people
            aliases: List of aliases
            output_path: Optional output path
            
        Returns:
            Personality configuration
        """
        import datetime
        now = datetime.datetime.now().isoformat()
        personality = {
            'name': name,
            'role': role,
            'bio': bio,
            'knowledge': knowledge,
            'limitations': limitations,
            'topics': topics,
            'style': style,
            'adjectives': adjectives,
            'people': people,
            'aliases': aliases,
            '_metadata': {
                'created_at': now,
                'exported_at': None
            }
        }
        logger.debug(f"Created personality configuration for {name} at {now}")
        return personality
    
    def export_personality(
        self,
        personality: Dict[str, Any],
        output_path: str
    ) -> None:
        """
        Export personality configuration to file.
        
        Args:
            personality: Personality configuration
            output_path: Output file path
        """
        logger.debug(f"Exporting personality to {output_path}")
        # Create output directory if needed
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Update exported_at metadata
        import datetime
        personality['_metadata']['exported_at'] = datetime.datetime.now().isoformat()
        
        # Write configuration
        with open(output_path, 'w') as f:
            json.dump(personality, f, indent=2)
        
        logger.debug(f"Exported personality configuration to {output_path}")

# Convenience function for direct use
async def create_personality(**kwargs) -> Dict[str, Any]:
    """
    Create a new personality configuration.
    
    Args:
        **kwargs: Personality parameters
        
    Returns:
        Personality configuration
    """
    creator = PersonalityCreator()
    return await creator.execute(kwargs) 
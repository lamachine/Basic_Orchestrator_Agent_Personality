"""
Personality configuration for the application.

Supports multiple personalities, each with their own config.

YAML example (future):
personality:
  default_personality: valet
  personalities:
    valet:
      enabled: true
      file_path: src/agents/Character_Ronan_valet_orchestrator.json
      use_by_default: true
    personal_assistant:
      enabled: true
      file_path: src/agents/Character_Ronan_personal_assistant.json
      use_by_default: false
    librarian:
      enabled: false
      file_path: src/agents/Character_Ronan_librarian.json
      use_by_default: false

Backwards compatible with single-personality config.
"""
import os
from typing import Optional, Dict
from pydantic import BaseModel, ValidationError
import yaml

DEFAULT_PERSONALITY_CONFIG = {
    'enabled': True,
    'file_path': os.path.abspath('src/agents/Character_Ronan_valet_orchestrator.json'),
    'use_by_default': True
}

class PersonalityConfig(BaseModel):
    enabled: bool = True
    file_path: str
    use_by_default: bool = False

class PersonalitiesConfig(BaseModel):
    default_personality: str = 'valet'
    personalities: Dict[str, PersonalityConfig]


def get_personality_config(
    name: Optional[str] = None,
    config_path: str = 'src/config/developer_user_config.yaml'
) -> PersonalityConfig:
    """
    Load and validate personality config for a given personality (or default).
    Args:
        name (str): Personality name (valet, personal_assistant, etc). If None, uses default.
        config_path (str): Path to YAML config file.
    Returns:
        PersonalityConfig: Validated config for the selected personality.
    Raises:
        ValueError: If config is invalid.
    """
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
        section = config.get('personality', {})
        personalities = section.get('personalities', {})
        default_name = section.get('default_personality', 'valet')
        if personalities:
            personalities_cfg = {
                k: PersonalityConfig(**{**DEFAULT_PERSONALITY_CONFIG, **v})
                for k, v in personalities.items()
            }
            name_ = name or default_name
            if name_ in personalities_cfg:
                return personalities_cfg[name_]
            # fallback to first available
            return list(personalities_cfg.values())[0]
        # fallback: single config for backward compatibility
        try:
            return PersonalityConfig(**{**DEFAULT_PERSONALITY_CONFIG, **section})
        except ValidationError as e:
            raise ValueError(f"Invalid personality config: {e}")
    return PersonalityConfig(**DEFAULT_PERSONALITY_CONFIG)

def list_personalities(config_path: str = 'src/config/developer_user_config.yaml') -> Dict[str, PersonalityConfig]:
    """
    List all available personalities from config.
    Returns:
        Dict[str, PersonalityConfig]
    """
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
        section = config.get('personality', {})
        personalities = section.get('personalities', {})
        if personalities:
            return {
                k: PersonalityConfig(**{**DEFAULT_PERSONALITY_CONFIG, **v})
                for k, v in personalities.items()
            }
        # fallback: single config
        return {'default': PersonalityConfig(**{**DEFAULT_PERSONALITY_CONFIG, **section})}
    return {'default': PersonalityConfig(**DEFAULT_PERSONALITY_CONFIG)} 
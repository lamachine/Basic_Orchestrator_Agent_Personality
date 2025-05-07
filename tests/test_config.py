"""Tests for the Configuration module."""

import os
import pytest
from unittest.mock import patch
from src.config import Configuration
import tempfile
from src.config.llm_config import get_llm_config, LLMConfig, LLMProvidersConfig, OllamaConfig, OpenAIConfig
from pydantic import ValidationError

def test_configuration_defaults():
    """Test that configuration uses default values when env vars are not set."""
    with patch.dict(os.environ, {}, clear=True):
        config = Configuration()
        
        # Check default logging values
        assert config.file_level == 'INFO'
        assert config.console_level == 'INFO'
        
        # Check default LLM values
        assert config.llm.providers.ollama.api_url == 'http://localhost:11434'
        assert config.llm.providers.ollama.default_model == 'llama3.1:latest'
        
        # Check debug mode default
        assert config.debug_mode is False

def test_configuration_from_env():
    """Test that configuration loads values from environment variables."""
    env_vars = {
        'file_level': 'DEBUG',
        'console_level': 'WARNING',
        'api_url': 'http://test-ollama:11434',
        'default_model': 'test-model',
        'url': 'https://test-supabase.com',
        'anon_key': 'test-anon-key',
        'service_role_key': 'test-service-key',
        'debug_mode': 'true'
    }
    
    with patch.dict(os.environ, env_vars, clear=True):
        config = Configuration()
        
        # Check logging values from env
        assert config.file_level == 'DEBUG'
        assert config.console_level == 'WARNING'
        
        # Check LLM values from env
        assert config.llm.providers.ollama.api_url == 'http://test-ollama:11434'
        assert config.llm.providers.ollama.default_model == 'test-model'
        
        # Check database values from env
        assert config.url == 'https://test-supabase.com'
        assert config.anon_key == 'test-anon-key'
        assert config.service_role_key == 'test-service-key'
        
        # Check debug mode from env
        assert config.debug_mode is True

def test_configuration_from_kwargs():
    """Test that configuration can be created with keyword arguments."""
    kwargs = {
        'file_level': 'ERROR',
        'console_level': 'CRITICAL',
        'api_url': 'http://custom-ollama:11434',
        'default_model': 'custom-model',
        'url': 'https://test-supabase.com',
        'anon_key': 'custom-anon-key',
        'service_role_key': 'custom-service-key',
        'debug_mode': True
    }
    
    config = Configuration(**kwargs)
    
    # Check values from kwargs
    assert config.file_level == 'ERROR'
    assert config.console_level == 'CRITICAL'
    assert config.llm.providers.ollama.api_url == 'http://custom-ollama:11434'
    assert config.llm.providers.ollama.default_model == 'custom-model'
    assert config.url == 'https://test-supabase.com'
    assert config.anon_key == 'custom-anon-key'
    assert config.service_role_key == 'custom-service-key'
    assert config.debug_mode is True
    
def test_to_dict_method():
    """Test that to_dict method returns all configuration values."""
    config = Configuration(file_level='DEBUG', default_model='test-model')
    config_dict = config.to_dict()
    
    # Check dict contains expected keys
    assert 'file_level' in config_dict
    assert 'console_level' in config_dict
    assert 'api_url' in config_dict
    assert 'default_model' in config_dict
    assert 'debug_mode' in config_dict
    
    # Check values
    assert config_dict['file_level'] == 'DEBUG'
    assert config_dict['default_model'] == 'test-model'

def test_repr_method():
    """Test that __repr__ method masks sensitive values."""
    config = Configuration(
        anon_key='secret-anon-key',
        service_role_key='secret-service-key'
    )
    
    repr_str = repr(config)
    
    # Sensitive values should be masked
    assert 'secret-anon-key' not in repr_str
    assert 'secret-service-key' not in repr_str
    assert '***REDACTED***' in repr_str 

def write_temp_yaml(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix='.yaml')
    with os.fdopen(fd, 'w') as tmp:
        tmp.write(content)
    return path

def test_ollama_enabled_only():
    yaml = '''
llm:
  preferred: ollama
  providers:
    ollama:
      enabled: true
    openai:
      enabled: false
'''
    path = write_temp_yaml(yaml)
    config = get_llm_config(path)
    assert config.providers.ollama is not None
    assert config.providers.openai is None or not hasattr(config.providers.openai, 'enabled') or not config.providers.openai.enabled
    assert config.providers.ollama.api_url.startswith('http')
    os.remove(path)

def test_openai_enabled_only():
    yaml = '''
llm:
  preferred: openai
  providers:
    ollama:
      enabled: false
    openai:
      enabled: true
      api_key: test-key
'''
    path = write_temp_yaml(yaml)
    config = get_llm_config(path)
    assert config.providers.openai is not None
    assert config.providers.ollama is None or not hasattr(config.providers.ollama, 'enabled') or not config.providers.ollama.enabled
    assert config.providers.openai.api_key == 'test-key'
    os.remove(path)

def test_both_enabled():
    yaml = '''
llm:
  preferred: ollama
  providers:
    ollama:
      enabled: true
    openai:
      enabled: true
      api_key: test-key
'''
    path = write_temp_yaml(yaml)
    config = get_llm_config(path)
    assert config.providers.ollama is not None
    assert config.providers.openai is not None
    os.remove(path)

def test_none_enabled_raises():
    yaml = '''
llm:
  preferred: ollama
  providers:
    ollama:
      enabled: false
    openai:
      enabled: false
'''
    path = write_temp_yaml(yaml)
    with pytest.raises(ValueError):
        get_llm_config(path)
    os.remove(path)

def test_extra_provider_enabled():
    yaml = '''
llm:
  preferred: ollama
  providers:
    ollama:
      enabled: true
    openai:
      enabled: false
    anthropic:
      enabled: true
'''
    path = write_temp_yaml(yaml)
    config = get_llm_config(path)
    assert config.providers.ollama is not None
    # Should ignore anthropic (not implemented)
    assert not hasattr(config.providers, 'anthropic') or getattr(config.providers, 'anthropic') is None
    os.remove(path) 
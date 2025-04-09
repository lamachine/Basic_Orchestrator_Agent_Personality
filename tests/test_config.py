"""Tests for the Configuration module."""

import os
import pytest
from unittest.mock import patch
from src.config import Configuration

def test_configuration_defaults():
    """Test that configuration uses default values when env vars are not set."""
    with patch.dict(os.environ, {}, clear=True):
        config = Configuration()
        
        # Check default logging values
        assert config.file_level == 'INFO'
        assert config.console_level == 'INFO'
        
        # Check default LLM values
        assert config.ollama_api_url == 'http://localhost:11434'
        assert config.ollama_model == 'llama3.1:latest'
        
        # Check debug mode default
        assert config.debug_mode is False

def test_configuration_from_env():
    """Test that configuration loads values from environment variables."""
    env_vars = {
        'FILE_LOG_LEVEL': 'DEBUG',
        'CONSOLE_LOG_LEVEL': 'WARNING',
        'OLLAMA_API_URL': 'http://test-ollama:11434',
        'OLLAMA_MODEL': 'test-model',
        'SUPABASE_URL': 'https://test-supabase.com',
        'SUPABASE_ANON_KEY': 'test-anon-key',
        'SUPABASE_SERVICE_ROLE_KEY': 'test-service-key',
        'DEBUG_MODE': 'true'
    }
    
    with patch.dict(os.environ, env_vars, clear=True):
        config = Configuration()
        
        # Check logging values from env
        assert config.file_level == 'DEBUG'
        assert config.console_level == 'WARNING'
        
        # Check LLM values from env
        assert config.ollama_api_url == 'http://test-ollama:11434'
        assert config.ollama_model == 'test-model'
        
        # Check database values from env
        assert config.supabase_url == 'https://test-supabase.com'
        assert config.supabase_anon_key == 'test-anon-key'
        assert config.supabase_service_role_key == 'test-service-key'
        
        # Check debug mode from env
        assert config.debug_mode is True

def test_configuration_from_kwargs():
    """Test that configuration can be created with keyword arguments."""
    kwargs = {
        'file_level': 'ERROR',
        'console_level': 'CRITICAL',
        'ollama_api_url': 'http://custom-ollama:11434',
        'ollama_model': 'custom-model',
        'debug_mode': True
    }
    
    config = Configuration(**kwargs)
    
    # Check values from kwargs
    assert config.file_level == 'ERROR'
    assert config.console_level == 'CRITICAL'
    assert config.ollama_api_url == 'http://custom-ollama:11434'
    assert config.ollama_model == 'custom-model'
    assert config.debug_mode is True
    
def test_to_dict_method():
    """Test that to_dict method returns all configuration values."""
    config = Configuration(file_level='DEBUG', ollama_model='test-model')
    config_dict = config.to_dict()
    
    # Check dict contains expected keys
    assert 'file_level' in config_dict
    assert 'console_level' in config_dict
    assert 'ollama_api_url' in config_dict
    assert 'ollama_model' in config_dict
    assert 'debug_mode' in config_dict
    
    # Check values
    assert config_dict['file_level'] == 'DEBUG'
    assert config_dict['ollama_model'] == 'test-model'

def test_repr_method():
    """Test that __repr__ method masks sensitive values."""
    config = Configuration(
        supabase_anon_key='secret-anon-key',
        supabase_service_role_key='secret-service-key'
    )
    
    repr_str = repr(config)
    
    # Sensitive values should be masked
    assert 'secret-anon-key' not in repr_str
    assert 'secret-service-key' not in repr_str
    assert '***REDACTED***' in repr_str 
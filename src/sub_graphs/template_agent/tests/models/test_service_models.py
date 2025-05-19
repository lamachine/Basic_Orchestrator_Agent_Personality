"""
Tests for service_models.py

This module tests the service models, including:
1. ServiceCapability model validation
2. ServiceConfig model validation
3. LLMConfig model validation
4. PoolConfig model validation
5. SessionConfig model validation
6. Service-specific configurations
"""

from typing import Any, Dict, List, Optional

import pytest
from pydantic import ValidationError

from ...src.common.config import (
    DBServiceConfig,
    LLMServiceConfig,
    LoggingServiceConfig,
    ServiceCapability,
    ServiceConfig,
    SessionServiceConfig,
    StateServiceConfig,
)
from ...src.common.models.service_models import (
    DBServiceConfig,
    LLMConfig,
    LLMServiceConfig,
    PoolConfig,
    ServiceCapability,
    ServiceConfig,
    SessionConfig,
    SessionServiceConfig,
)


def test_service_capability_validation():
    """Test ServiceCapability model validation."""
    # Test case: Normal operation - should pass
    capability = ServiceCapability(
        name="test_capability", description="Test capability description"
    )

    assert capability.name == "test_capability"
    assert capability.description == "Test capability description"
    assert capability.parameters == {}
    assert capability.required is False
    assert capability.enabled is True

    # Test with custom values
    capability = ServiceCapability(
        name="custom_capability",
        description="Custom capability description",
        parameters={"param1": "value1", "param2": 42},
        required=True,
        enabled=False,
    )

    assert capability.name == "custom_capability"
    assert capability.description == "Custom capability description"
    assert capability.parameters["param1"] == "value1"
    assert capability.parameters["param2"] == 42
    assert capability.required is True
    assert capability.enabled is False


def test_service_capability_validation_error():
    """Test ServiceCapability validation errors."""
    # Test case: Error condition - missing required fields
    with pytest.raises(ValidationError):
        ServiceCapability(name="test_capability")  # Missing description

    with pytest.raises(ValidationError):
        ServiceCapability(description="Test description")  # Missing name


def test_service_capability_edge_cases():
    """Test ServiceCapability edge cases."""
    # Test case: Edge case - empty description
    capability = ServiceCapability(name="empty_desc", description="")  # Empty but valid
    assert capability.description == ""

    # Test case: Edge case - complex parameters
    complex_params = {
        "string_param": "value",
        "int_param": 123,
        "bool_param": True,
        "list_param": [1, 2, 3],
        "dict_param": {"key": "value"},
        "nested_param": {"nested_key": {"deeply_nested": "value"}},
    }

    capability = ServiceCapability(
        name="complex_params",
        description="Capability with complex parameters",
        parameters=complex_params,
    )

    assert capability.parameters["string_param"] == "value"
    assert capability.parameters["int_param"] == 123
    assert capability.parameters["list_param"] == [1, 2, 3]
    assert capability.parameters["nested_param"]["nested_key"]["deeply_nested"] == "value"


def test_service_config_validation():
    """Test ServiceConfig model validation."""
    # Test case: Normal operation - should pass
    service_config = ServiceConfig(service_name="test_service")

    assert service_config.service_name == "test_service"
    assert service_config.enabled is True
    assert service_config.capabilities == []
    assert service_config.config == {}
    assert service_config.parent_config is None

    # Test with custom values including capabilities
    capability1 = ServiceCapability(name="capability1", description="First capability")

    capability2 = ServiceCapability(
        name="capability2", description="Second capability", required=True
    )

    service_config = ServiceConfig(
        service_name="custom_service",
        enabled=False,
        capabilities=[capability1, capability2],
        config={"setting1": "value1", "setting2": 42},
        parent_config={"parent_setting": "parent_value"},
    )

    assert service_config.service_name == "custom_service"
    assert service_config.enabled is False
    assert len(service_config.capabilities) == 2
    assert service_config.capabilities[0].name == "capability1"
    assert service_config.capabilities[1].name == "capability2"
    assert service_config.config["setting1"] == "value1"
    assert service_config.config["setting2"] == 42
    assert service_config.parent_config["parent_setting"] == "parent_value"


def test_service_config_methods():
    """Test ServiceConfig methods."""
    # Test get_merged_config method
    service_config = ServiceConfig(
        service_name="test_service",
        config={"local1": "local_value1", "shared": "local_shared"},
        parent_config={"parent1": "parent_value1", "shared": "parent_shared"},
    )

    merged_config = service_config.get_merged_config()
    assert merged_config["local1"] == "local_value1"
    assert merged_config["parent1"] == "parent_value1"
    assert merged_config["shared"] == "local_shared"  # Local overrides parent

    # Test without parent config
    service_config = ServiceConfig(service_name="test_service", config={"local1": "local_value1"})

    merged_config = service_config.get_merged_config()
    assert merged_config == {"local1": "local_value1"}

    # Test get_capability and is_capability_enabled methods
    capability1 = ServiceCapability(
        name="enabled_cap", description="Enabled capability", enabled=True
    )

    capability2 = ServiceCapability(
        name="disabled_cap", description="Disabled capability", enabled=False
    )

    service_config = ServiceConfig(
        service_name="test_service", capabilities=[capability1, capability2]
    )

    # Test get_capability
    assert service_config.get_capability("enabled_cap") == capability1
    assert service_config.get_capability("disabled_cap") == capability2
    assert service_config.get_capability("nonexistent_cap") is None

    # Test is_capability_enabled
    assert service_config.is_capability_enabled("enabled_cap") is True
    assert service_config.is_capability_enabled("disabled_cap") is False
    assert service_config.is_capability_enabled("nonexistent_cap") is False


def test_service_config_validation_error():
    """Test ServiceConfig validation errors."""
    # Test case: Error condition - missing required fields
    with pytest.raises(ValidationError):
        ServiceConfig()  # Missing service_name


def test_service_config_edge_cases():
    """Test ServiceConfig edge cases."""
    # Test case: Edge case - empty service name
    service_config = ServiceConfig(service_name="")
    assert service_config.service_name == ""

    # Test case: Edge case - empty config but with parent config
    service_config = ServiceConfig(
        service_name="test_service",
        config={},
        parent_config={"parent_setting": "parent_value"},
    )

    merged_config = service_config.get_merged_config()
    assert merged_config == {"parent_setting": "parent_value"}

    # Test case: Edge case - empty capabilities list
    service_config = ServiceConfig(service_name="test_service", capabilities=[])

    assert service_config.capabilities == []
    assert service_config.get_capability("any_cap") is None
    assert service_config.is_capability_enabled("any_cap") is False


def test_llm_config_validation():
    """Test LLMConfig model validation."""
    # Test case: Normal operation - should pass
    llm_config = LLMConfig(model_name="test_model")

    assert llm_config.model_name == "test_model"
    assert llm_config.temperature == 0.7
    assert llm_config.max_tokens == 2000
    assert llm_config.top_p == 1.0
    assert llm_config.frequency_penalty == 0.0
    assert llm_config.presence_penalty == 0.0
    assert llm_config.stop is None

    # Test with custom values
    llm_config = LLMConfig(
        model_name="custom_model",
        temperature=0.5,
        max_tokens=1000,
        top_p=0.9,
        frequency_penalty=0.2,
        presence_penalty=0.3,
        stop=["stop1", "stop2"],
    )

    assert llm_config.model_name == "custom_model"
    assert llm_config.temperature == 0.5
    assert llm_config.max_tokens == 1000
    assert llm_config.top_p == 0.9
    assert llm_config.frequency_penalty == 0.2
    assert llm_config.presence_penalty == 0.3
    assert llm_config.stop == ["stop1", "stop2"]


def test_llm_config_validation_error():
    """Test LLMConfig validation errors."""
    # Test case: Error condition - missing required fields
    with pytest.raises(ValidationError):
        LLMConfig()  # Missing model_name

    # Test case: Error condition - invalid temperature
    with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
        LLMConfig(model_name="test_model", temperature=2.5)

    with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
        LLMConfig(model_name="test_model", temperature=-0.1)

    # Test case: Error condition - invalid max_tokens
    with pytest.raises(ValueError, match="Max tokens must be at least 1"):
        LLMConfig(model_name="test_model", max_tokens=0)

    with pytest.raises(ValueError, match="Max tokens must be at least 1"):
        LLMConfig(model_name="test_model", max_tokens=-10)


def test_llm_config_edge_cases():
    """Test LLMConfig edge cases."""
    # Test case: Edge case - boundary temperature values
    llm_config = LLMConfig(model_name="test_model", temperature=0)
    assert llm_config.temperature == 0

    llm_config = LLMConfig(model_name="test_model", temperature=2)
    assert llm_config.temperature == 2

    # Test case: Edge case - minimum max_tokens
    llm_config = LLMConfig(model_name="test_model", max_tokens=1)
    assert llm_config.max_tokens == 1

    # Test case: Edge case - empty stop list
    llm_config = LLMConfig(model_name="test_model", stop=[])
    assert llm_config.stop == []


def test_pool_config_validation():
    """Test PoolConfig model validation."""
    # Test case: Normal operation - should pass
    pool_config = PoolConfig()

    assert pool_config.pool_size == 5
    assert pool_config.timeout == 30.0
    assert pool_config.retry_count == 3
    assert pool_config.retry_delay == 1.0

    # Test with custom values
    pool_config = PoolConfig(pool_size=10, timeout=60.0, retry_count=5, retry_delay=2.0)

    assert pool_config.pool_size == 10
    assert pool_config.timeout == 60.0
    assert pool_config.retry_count == 5
    assert pool_config.retry_delay == 2.0


def test_pool_config_validation_error():
    """Test PoolConfig validation errors."""
    # Test case: Error condition - invalid pool_size
    with pytest.raises(ValueError, match="Pool size must be at least 1"):
        PoolConfig(pool_size=0)

    with pytest.raises(ValueError, match="Pool size must be at least 1"):
        PoolConfig(pool_size=-5)

    # Test case: Error condition - invalid timeout
    with pytest.raises(ValueError, match="Timeout must be positive"):
        PoolConfig(timeout=0)

    with pytest.raises(ValueError, match="Timeout must be positive"):
        PoolConfig(timeout=-10.0)

    # Test case: Error condition - invalid retry_count
    with pytest.raises(ValueError, match="Retry count cannot be negative"):
        PoolConfig(retry_count=-1)


def test_pool_config_edge_cases():
    """Test PoolConfig edge cases."""
    # Test case: Edge case - minimum valid values
    pool_config = PoolConfig(pool_size=1, timeout=0.1, retry_count=0, retry_delay=0.1)

    assert pool_config.pool_size == 1
    assert pool_config.timeout == 0.1
    assert pool_config.retry_count == 0
    assert pool_config.retry_delay == 0.1

    # Test case: Edge case - very large values
    pool_config = PoolConfig(pool_size=1000, timeout=3600.0, retry_count=100, retry_delay=60.0)

    assert pool_config.pool_size == 1000
    assert pool_config.timeout == 3600.0
    assert pool_config.retry_count == 100
    assert pool_config.retry_delay == 60.0


def test_session_config_validation():
    """Test SessionConfig model validation."""
    # Test case: Normal operation - should pass
    session_config = SessionConfig()

    assert session_config.session_timeout == 3600.0
    assert session_config.max_sessions == 100
    assert session_config.cleanup_interval == 300.0

    # Test with custom values
    session_config = SessionConfig(session_timeout=7200.0, max_sessions=200, cleanup_interval=600.0)

    assert session_config.session_timeout == 7200.0
    assert session_config.max_sessions == 200
    assert session_config.cleanup_interval == 600.0


def test_session_config_validation_error():
    """Test SessionConfig validation errors."""
    # Test case: Error condition - invalid session_timeout
    with pytest.raises(ValueError, match="Session timeout must be positive"):
        SessionConfig(session_timeout=0)

    with pytest.raises(ValueError, match="Session timeout must be positive"):
        SessionConfig(session_timeout=-3600.0)

    # Test case: Error condition - invalid max_sessions
    with pytest.raises(ValueError, match="Max sessions must be at least 1"):
        SessionConfig(max_sessions=0)

    with pytest.raises(ValueError, match="Max sessions must be at least 1"):
        SessionConfig(max_sessions=-10)

    # Test case: Error condition - invalid cleanup_interval
    with pytest.raises(ValueError, match="Cleanup interval must be positive"):
        SessionConfig(cleanup_interval=0)

    with pytest.raises(ValueError, match="Cleanup interval must be positive"):
        SessionConfig(cleanup_interval=-300.0)


def test_session_config_edge_cases():
    """Test SessionConfig edge cases."""
    # Test case: Edge case - minimum valid values
    session_config = SessionConfig(session_timeout=0.1, max_sessions=1, cleanup_interval=0.1)

    assert session_config.session_timeout == 0.1
    assert session_config.max_sessions == 1
    assert session_config.cleanup_interval == 0.1

    # Test case: Edge case - very large values
    session_config = SessionConfig(
        session_timeout=86400.0,  # 24 hours
        max_sessions=10000,
        cleanup_interval=3600.0,  # 1 hour
    )

    assert session_config.session_timeout == 86400.0
    assert session_config.max_sessions == 10000
    assert session_config.cleanup_interval == 3600.0


def test_service_specific_configs():
    """Test service-specific configuration classes."""
    # Test LLMServiceConfig
    llm_service_config = LLMServiceConfig(name="llm_service", model_name="gpt-4")

    assert llm_service_config.name == "llm_service"
    assert llm_service_config.model_name == "gpt-4"
    assert llm_service_config.temperature == 0.7
    assert llm_service_config.max_tokens == 2000
    assert llm_service_config.stop_sequences == []

    # Test with custom values
    llm_service_config = LLMServiceConfig(
        name="custom_llm",
        model_name="llama-3",
        temperature=0.5,
        max_tokens=1000,
        stop_sequences=["stop1", "stop2"],
    )

    assert llm_service_config.name == "custom_llm"
    assert llm_service_config.model_name == "llama-3"
    assert llm_service_config.temperature == 0.5
    assert llm_service_config.max_tokens == 1000
    assert llm_service_config.stop_sequences == ["stop1", "stop2"]

    # Test DBServiceConfig
    db_service_config = DBServiceConfig(
        name="db_service", connection_string="postgresql://user:pass@localhost/db"
    )

    assert db_service_config.name == "db_service"
    assert db_service_config.connection_string == "postgresql://user:pass@localhost/db"
    assert db_service_config.pool_size == 5
    assert db_service_config.timeout == 30
    assert db_service_config.retry_count == 3

    # Test with custom values
    db_service_config = DBServiceConfig(
        name="custom_db",
        connection_string="mysql://user:pass@localhost/db",
        pool_size=10,
        timeout=60,
        retry_count=5,
    )

    assert db_service_config.name == "custom_db"
    assert db_service_config.connection_string == "mysql://user:pass@localhost/db"
    assert db_service_config.pool_size == 10
    assert db_service_config.timeout == 60
    assert db_service_config.retry_count == 5

    # Test SessionServiceConfig
    session_service_config = SessionServiceConfig(name="session_service")

    assert session_service_config.name == "session_service"
    assert session_service_config.session_timeout == 3600
    assert session_service_config.max_sessions == 100
    assert session_service_config.cleanup_interval == 300

    # Test with custom values
    session_service_config = SessionServiceConfig(
        name="custom_session",
        session_timeout=7200,
        max_sessions=200,
        cleanup_interval=600,
    )

    assert session_service_config.name == "custom_session"
    assert session_service_config.session_timeout == 7200
    assert session_service_config.max_sessions == 200
    assert session_service_config.cleanup_interval == 600


def test_service_specific_configs_validation_error():
    """Test validation errors for service-specific configuration classes."""
    # Test LLMServiceConfig validation errors
    with pytest.raises(ValidationError):
        LLMServiceConfig(name="test")  # Missing model_name

    with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
        LLMServiceConfig(name="test", model_name="gpt-4", temperature=3.0)

    with pytest.raises(ValueError, match="Max tokens must be at least 1"):
        LLMServiceConfig(name="test", model_name="gpt-4", max_tokens=0)

    # Test DBServiceConfig validation errors
    with pytest.raises(ValidationError):
        DBServiceConfig(name="test")  # Missing connection_string

    with pytest.raises(ValueError, match="Pool size must be at least 1"):
        DBServiceConfig(name="test", connection_string="test", pool_size=0)

    with pytest.raises(ValueError, match="Timeout must be at least 1 second"):
        DBServiceConfig(name="test", connection_string="test", timeout=0)

    with pytest.raises(ValueError, match="Retry count must be non-negative"):
        DBServiceConfig(name="test", connection_string="test", retry_count=-1)

    # Test SessionServiceConfig validation errors
    with pytest.raises(ValueError, match="Session timeout must be at least 60 seconds"):
        SessionServiceConfig(name="test", session_timeout=59)

    with pytest.raises(ValueError, match="Max sessions must be at least 1"):
        SessionServiceConfig(name="test", max_sessions=0)

    with pytest.raises(ValueError, match="Cleanup interval must be at least 60 seconds"):
        SessionServiceConfig(name="test", cleanup_interval=59)

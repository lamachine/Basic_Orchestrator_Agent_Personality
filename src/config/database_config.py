"""
Original YAML (for traceability):
database:
  provider: supabase_local  # or supabase_web, or postgres
  providers:
    supabase_local:
      url: http://localhost:54321
      anon_key: local-anon-key
      service_role_key: local-service-role-key
    supabase_web:
      url: https://yourproject.supabase.co
      anon_key: web-anon-key
      service_role_key: web-service-role-key
    postgres:
      url: postgresql://user:password@localhost:5432/dbname

# Additional database config names found in the codebase (for consolidation):
# provider, url, anon_key, service_role_key
# Most common/preferred: provider, url, anon_key, service_role_key
"""
from pydantic import BaseModel, ValidationError
from typing import Optional, Dict
import yaml
import os

class SupabaseConfig(BaseModel):
    url: str
    anon_key: str
    service_role_key: str

class PostgresConfig(BaseModel):
    url: str

class DatabaseProvidersConfig(BaseModel):
    supabase_local: Optional[SupabaseConfig]
    supabase_web: Optional[SupabaseConfig]
    postgres: Optional[PostgresConfig]

class DatabaseConfig(BaseModel):
    provider: str = "supabase_local"
    providers: DatabaseProvidersConfig

def get_database_config(config_path: str = 'src/config/developer_user_config.yaml') -> DatabaseConfig:
    """
    Load and validate database config from YAML using Pydantic.
    Args:
        config_path (str): Path to YAML config file.
    Returns:
        DatabaseConfig: Validated database config.
    Raises:
        ValueError: If config is invalid.
    """
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
        section = config.get('database', {})
        providers = section.get('providers', {})
        validated_providers = {}
        if 'supabase_local' in providers:
            validated_providers['supabase_local'] = SupabaseConfig(**providers['supabase_local'])
        if 'supabase_web' in providers:
            validated_providers['supabase_web'] = SupabaseConfig(**providers['supabase_web'])
        if 'postgres' in providers:
            validated_providers['postgres'] = PostgresConfig(**providers['postgres'])
        section['providers'] = DatabaseProvidersConfig(**validated_providers)
        try:
            return DatabaseConfig(**section)
        except ValidationError as e:
            raise ValueError(f"Invalid database config: {e}")
    # Default: only supabase_local
    return DatabaseConfig(provider="supabase_local", providers=DatabaseProvidersConfig(supabase_local=SupabaseConfig(url="", anon_key="", service_role_key=""))) 
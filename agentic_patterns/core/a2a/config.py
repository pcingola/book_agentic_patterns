"""Configuration for A2A clients with YAML loading."""

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from agentic_patterns.core.config.config import AGENTIC_PATTERNS_PROJECT_DIR


class A2AClientConfig(BaseModel):
    """Configuration for an A2A client."""
    url: str
    timeout: int = Field(default=300)
    poll_interval: float = Field(default=1.0)
    max_retries: int = Field(default=3)
    retry_delay: float = Field(default=1.0)


class A2ASettings(BaseModel):
    """Container for A2A client configurations."""
    clients: dict[str, A2AClientConfig]

    def get(self, name: str) -> A2AClientConfig:
        if name not in self.clients:
            raise ValueError(f"A2A client config '{name}' not found. Available: {list(self.clients.keys())}")
        return self.clients[name]

    def list_clients(self) -> list[str]:
        return list(self.clients.keys())


def _expand_env_vars(value: str) -> str:
    """Expand ${VAR} patterns in string values."""
    pattern = r'\$\{(\w+)\}'
    def replace(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    return re.sub(pattern, replace, value)


def _expand_config_vars(config: dict) -> dict:
    """Recursively expand environment variables in config dict."""
    result = {}
    for key, value in config.items():
        if isinstance(value, str):
            result[key] = _expand_env_vars(value)
        elif isinstance(value, dict):
            result[key] = _expand_config_vars(value)
        else:
            result[key] = value
    return result


_settings: A2ASettings | None = None


def load_a2a_settings(config_path: Path | str | None = None) -> A2ASettings:
    """Load A2A client configurations from YAML file."""
    global _settings
    if _settings is not None:
        return _settings

    if config_path is None:
        config_path = AGENTIC_PATTERNS_PROJECT_DIR / "config.yaml"
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    clients: dict[str, A2AClientConfig] = {}
    if "a2a" in data and "clients" in data["a2a"]:
        for name, config_data in data["a2a"]["clients"].items():
            config_data = _expand_config_vars(config_data)
            clients[name] = A2AClientConfig(**config_data)

    _settings = A2ASettings(clients=clients)
    return _settings


def get_client_config(name: str) -> A2AClientConfig:
    """Get a named A2A client configuration."""
    settings = load_a2a_settings()
    return settings.get(name)


def list_client_configs() -> list[str]:
    """List available A2A client configuration names."""
    settings = load_a2a_settings()
    return settings.list_clients()

"""MCP configuration models and YAML loading."""

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from agentic_patterns.core.config.config import MAIN_PROJECT_DIR


class MCPClientConfig(BaseModel):
    """Configuration for connecting to an external MCP server."""

    type: str = Field(default="client")
    url: str
    url_isolated: str | None = None
    read_timeout: int = Field(default=60)


class MCPServerConfig(BaseModel):
    """Configuration for exposing an MCP server."""

    type: str = Field(default="server")
    name: str
    instructions: str | None = None
    port: int = Field(default=8000)


MCPConfig = MCPClientConfig | MCPServerConfig


class MCPSettings(BaseModel):
    """Container for MCP configurations."""

    mcp_servers: dict[str, MCPConfig]

    def get(self, name: str) -> MCPConfig:
        if name not in self.mcp_servers:
            raise ValueError(
                f"MCP config '{name}' not found. Available: {list(self.mcp_servers.keys())}"
            )
        return self.mcp_servers[name]


def _expand_env_vars(value: str) -> str:
    """Expand ${VAR} patterns in string values."""
    pattern = r"\$\{(\w+)\}"

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


def load_mcp_settings(config_path: Path | str | None = None) -> MCPSettings:
    """Load MCP configurations from YAML file."""
    if config_path is None:
        config_path = MAIN_PROJECT_DIR / "config.yaml"

    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    mcp_servers: dict[str, MCPConfig] = {}

    if "mcp_servers" in data:
        for name, config_data in data["mcp_servers"].items():
            config_data = _expand_config_vars(config_data)
            config_type = config_data.get("type", "client")
            match config_type:
                case "client":
                    mcp_servers[name] = MCPClientConfig(**config_data)
                case "server":
                    mcp_servers[name] = MCPServerConfig(**config_data)
                case _:
                    raise ValueError(f"Unsupported MCP type: {config_type}")

    return MCPSettings(mcp_servers=mcp_servers)

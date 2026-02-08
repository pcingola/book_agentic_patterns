"""MCP client and server factory functions.

Provides:
- Config models for MCP clients and servers (YAML-based with env var expansion)
- Error classification: ToolRetryError (LLM retries) vs ToolFatalError (run aborts)
- MCPServerStreamableHTTPStrict: client that aborts on fatal tool errors
- MCPClientPrivateData: dual-instance wrapper for network isolation switching
- create_mcp_server(): factory with AuthSessionMiddleware pre-wired
- get_mcp_client(): returns isolation-aware or strict client from config
"""

import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.mcp import MCPServerStreamableHTTP

from agentic_patterns.core.compliance.private_data import session_has_private_data
from agentic_patterns.core.config.config import DEFAULT_SESSION_ID, MAIN_PROJECT_DIR
from agentic_patterns.core.user_session import set_user_session


# -- Error classification ------------------------------------------------

FATAL_PREFIX = "[FATAL] "


class ToolRetryError(ToolError):
    """Retryable: the LLM picked bad arguments, let it try again."""
    pass


class ToolFatalError(ToolError):
    """Fatal: infrastructure failure, abort the agent run."""
    def __init__(self, message: str):
        super().__init__(f"{FATAL_PREFIX}{message}")


# -- Config models -------------------------------------------------------

class MCPClientConfig(BaseModel):
    """Configuration for MCP client (connecting to external MCP servers)."""
    type: str = Field(default="client")
    url: str
    url_isolated: str | None = None
    read_timeout: int = Field(default=60)


class MCPServerConfig(BaseModel):
    """Configuration for MCP server (exposing tools)."""
    type: str = Field(default="server")
    name: str
    instructions: str | None = None
    port: int = Field(default=8000)


MCPConfig = MCPClientConfig | MCPServerConfig


class MCPSettings(BaseModel):
    """Container for MCP server configurations."""
    mcp_servers: dict[str, MCPConfig]

    def get(self, name: str) -> MCPConfig:
        if name not in self.mcp_servers:
            raise ValueError(f"MCP config '{name}' not found. Available: {list(self.mcp_servers.keys())}")
        return self.mcp_servers[name]


# -- YAML config loading -------------------------------------------------

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


def _load_mcp_settings(config_path: Path | str | None = None) -> MCPSettings:
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


# -- Client classes ------------------------------------------------------

class MCPServerStreamableHTTPStrict(MCPServerStreamableHTTP):
    """MCP client that aborts the agent run on fatal tool errors.

    Overrides direct_call_tool to intercept errors with the [FATAL] prefix.
    Fatal errors raise RuntimeError (agent run aborts) instead of ModelRetry
    (agent retries with different arguments).
    """

    async def direct_call_tool(self, name: str, args: dict[str, Any], metadata: dict[str, Any] | None = None):
        try:
            return await super().direct_call_tool(name, args, metadata)
        except ModelRetry as e:
            msg = str(e)
            if msg.startswith(FATAL_PREFIX):
                raise RuntimeError(msg[len(FATAL_PREFIX):]) from e
            raise


class MCPClientPrivateData:
    """Dual-instance MCP client for private-data-aware network isolation.

    Holds two MCPServerStreamableHTTPStrict instances -- normal and isolated --
    both opened at context entry. Every call delegates through _target(), which
    checks session_has_private_data(). Once private data appears, all subsequent
    calls route to the isolated instance. The switch is a one-way ratchet.
    """

    def __init__(self, url: str, url_isolated: str, **kwargs):
        self._normal = MCPServerStreamableHTTPStrict(url=url, **kwargs)
        self._isolated = MCPServerStreamableHTTPStrict(url=url_isolated, **kwargs)
        self._is_isolated = False

    def _target(self) -> MCPServerStreamableHTTPStrict:
        if not self._is_isolated:
            self._is_isolated = session_has_private_data()
        return self._isolated if self._is_isolated else self._normal

    async def __aenter__(self):
        await self._normal.__aenter__()
        await self._isolated.__aenter__()
        return self

    async def __aexit__(self, *args):
        await self._isolated.__aexit__(*args)
        await self._normal.__aexit__(*args)

    async def call_tool(self, name, tool_args, ctx, tool):
        return await self._target().call_tool(name, tool_args, ctx, tool)

    async def direct_call_tool(self, name: str, args: dict[str, Any], metadata: dict[str, Any] | None = None):
        return await self._target().direct_call_tool(name, args, metadata)

    async def get_tools(self, ctx):
        return await self._target().get_tools(ctx)

    async def list_tools(self):
        return await self._target().list_tools()


# -- Server factory ------------------------------------------------------

def create_mcp_server(name: str, instructions: str | None = None) -> FastMCP:
    """Create a FastMCP server with AuthSessionMiddleware pre-wired."""
    return FastMCP(name=name, instructions=instructions, middleware=[AuthSessionMiddleware()])


# -- Client factories ----------------------------------------------------

def create_process_tool_call(get_token: Callable[[], str | None]):
    """Factory that returns a process_tool_call callback injecting a Bearer token into MCP calls."""
    async def process_tool_call(ctx, tool_name, args):
        token = get_token()
        if token:
            args.setdefault("_metadata", {})["authorization"] = f"Bearer {token}"
        return args
    return process_tool_call


def get_mcp_client(name: str, config_path: Path | str | None = None, bearer_token: str | None = None) -> MCPServerStreamableHTTPStrict | MCPClientPrivateData:
    """Create MCP client from config.yaml by name.

    Returns MCPClientPrivateData when url_isolated is configured,
    MCPServerStreamableHTTPStrict otherwise.
    """
    settings = _load_mcp_settings(config_path)
    config = settings.get(name)

    if not isinstance(config, MCPClientConfig):
        raise ValueError(f"MCP config '{name}' is not a client config (type={config.type})")

    headers = {"Authorization": f"Bearer {bearer_token}"} if bearer_token else None
    if config.url_isolated:
        return MCPClientPrivateData(url=config.url, url_isolated=config.url_isolated, timeout=config.read_timeout, headers=headers)
    return MCPServerStreamableHTTPStrict(url=config.url, timeout=config.read_timeout, headers=headers)


def get_mcp_clients(names: list[str], config_path: Path | str | None = None) -> list[MCPServerStreamableHTTPStrict | MCPClientPrivateData]:
    """Create multiple MCP clients from config.yaml."""
    return [get_mcp_client(name, config_path) for name in names]


def get_mcp_server(name: str, config_path: Path | str | None = None) -> FastMCP:
    """Create FastMCP server instance from config.yaml by name."""
    settings = _load_mcp_settings(config_path)
    config = settings.get(name)

    if not isinstance(config, MCPServerConfig):
        raise ValueError(f"MCP config '{name}' is not a server config (type={config.type})")

    return FastMCP(name=config.name, instructions=config.instructions)


# -- Middleware -----------------------------------------------------------

class AuthSessionMiddleware(Middleware):
    """FastMCP middleware that sets user session from the access token claims."""

    async def on_request(self, context, call_next):
        token = get_access_token()
        if token:
            set_user_session(token.claims["sub"], token.claims.get("session_id", DEFAULT_SESSION_ID))
        return await call_next(context)

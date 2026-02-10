"""Factory functions for creating MCP servers and clients."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from agentic_patterns.core.mcp.config import (
    MCPClientConfig,
    MCPServerConfig,
    load_mcp_settings,
)
from agentic_patterns.core.mcp.middleware import AuthSessionMiddleware
from agentic_patterns.core.mcp.servers import (
    MCPServerPrivateData,
    MCPServerStrict,
    default_mcp_log_handler,
)


def create_mcp_server(name: str, instructions: str | None = None) -> FastMCP:
    """Create a FastMCP server with AuthSessionMiddleware pre-wired."""
    return FastMCP(
        name=name, instructions=instructions, middleware=[AuthSessionMiddleware()]
    )


def create_process_tool_call(get_token: Callable[[], str | None]):
    """Factory that returns a process_tool_call callback injecting a Bearer token into MCP calls."""

    async def process_tool_call(ctx, tool_name, args):
        token = get_token()
        if token:
            args.setdefault("_metadata", {})["authorization"] = f"Bearer {token}"
        return args

    return process_tool_call


def get_mcp_client(
    name: str, config_path: Path | str | None = None, bearer_token: str | None = None
) -> MCPServerStrict | MCPServerPrivateData:
    """Create MCP server toolset from config.yaml by name.

    Returns MCPServerPrivateData when url_isolated is configured,
    MCPServerStrict otherwise.
    """
    settings = load_mcp_settings(config_path)
    config = settings.get(name)

    if not isinstance(config, MCPClientConfig):
        raise ValueError(
            f"MCP config '{name}' is not a client config (type={config.type})"
        )

    headers = {"Authorization": f"Bearer {bearer_token}"} if bearer_token else None
    common: dict[str, Any] = dict(
        timeout=config.read_timeout,
        headers=headers,
        log_handler=default_mcp_log_handler,
    )
    if config.url_isolated:
        return MCPServerPrivateData(
            url=config.url, url_isolated=config.url_isolated, **common
        )
    return MCPServerStrict(url=config.url, **common)


def get_mcp_clients(
    names: list[str], config_path: Path | str | None = None
) -> list[MCPServerStrict | MCPServerPrivateData]:
    """Create multiple MCP server toolsets from config.yaml."""
    return [get_mcp_client(name, config_path) for name in names]


def get_mcp_server(name: str, config_path: Path | str | None = None) -> FastMCP:
    """Create FastMCP server instance from config.yaml by name."""
    settings = load_mcp_settings(config_path)
    config = settings.get(name)

    if not isinstance(config, MCPServerConfig):
        raise ValueError(
            f"MCP config '{name}' is not a server config (type={config.type})"
        )

    return FastMCP(name=config.name, instructions=config.instructions)

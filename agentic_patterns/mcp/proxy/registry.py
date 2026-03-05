"""Server registry: discovers backend MCP servers and aggregates their tools."""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import Tool

from agentic_patterns.mcp.proxy.config import ProxyBackendConfig

logger = logging.getLogger(__name__)


class ServerStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class BackendServer:
    """Tracks a backend MCP server's state and tools."""

    config: ProxyBackendConfig
    status: ServerStatus = ServerStatus.UNKNOWN
    tools: list[Tool] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.config.name

    def __str__(self) -> str:
        return f"BackendServer({self.name}, status={self.status.value}, tools={len(self.tools)})"


class ServerRegistry:
    """Registry of backend MCP servers. Discovers tools and tracks health."""

    def __init__(self, backends: list[ProxyBackendConfig]) -> None:
        self._servers: dict[str, BackendServer] = {
            b.name: BackendServer(config=b) for b in backends if b.enabled
        }
        self._tool_to_server: dict[str, str] = {}

    @property
    def servers(self) -> dict[str, BackendServer]:
        return dict(self._servers)

    def add_server(self, config: ProxyBackendConfig) -> None:
        """Register a new backend server."""
        self._servers[config.name] = BackendServer(config=config)

    async def discover_all(self) -> None:
        """Connect to all backends and discover their tools."""
        tasks = [self._discover_server(s) for s in self._servers.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
        self._rebuild_tool_index()

    def get_all_tools(self) -> list[tuple[str, Tool]]:
        """Return all tools as (namespaced_name, tool) pairs from healthy servers."""
        result = []
        for server in self._servers.values():
            if server.status != ServerStatus.HEALTHY:
                continue
            for tool in server.tools:
                result.append((f"{server.name}.{tool.name}", tool))
        return result

    async def health_check(self, server_name: str) -> ServerStatus:
        """Probe a single server's health."""
        server = self._servers.get(server_name)
        if not server:
            return ServerStatus.UNKNOWN
        try:
            async with streamablehttp_client(server.config.url) as (r, w, _):
                async with ClientSession(r, w) as session:
                    await session.initialize()
                    server.status = ServerStatus.HEALTHY
        except Exception:
            server.status = ServerStatus.UNHEALTHY
        return server.status

    def remove_server(self, name: str) -> None:
        """Unregister a backend server."""
        self._servers.pop(name, None)
        self._rebuild_tool_index()

    def resolve_tool(self, namespaced_tool: str) -> tuple[str, str] | None:
        """Resolve 'server.tool' to (server_name, tool_name). Returns None if not found."""
        if "." not in namespaced_tool:
            return None
        server_name, tool_name = namespaced_tool.split(".", 1)
        if server_name in self._servers:
            return server_name, tool_name
        return None

    async def _discover_server(self, server: BackendServer) -> None:
        """Connect to a single backend, list its tools, update status."""
        try:
            async with streamablehttp_client(server.config.url) as (r, w, _):
                async with ClientSession(r, w) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    server.tools = list(result.tools)
                    server.status = ServerStatus.HEALTHY
                    logger.info("Discovered %d tools from %s", len(server.tools), server.name)
        except Exception:
            server.status = ServerStatus.UNHEALTHY
            server.tools = []
            logger.warning("Failed to discover tools from %s", server.name, exc_info=True)

    def _rebuild_tool_index(self) -> None:
        self._tool_to_server = {}
        for server in self._servers.values():
            for tool in server.tools:
                self._tool_to_server[f"{server.name}.{tool.name}"] = server.name

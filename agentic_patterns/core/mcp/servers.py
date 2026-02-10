"""MCP server toolsets: strict error handling and private-data isolation."""

import logging
from typing import Any

from mcp import types as mcp_types
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.mcp import MCPServerStreamableHTTP

from agentic_patterns.core.compliance.private_data import session_has_private_data
from agentic_patterns.core.mcp.errors import FATAL_PREFIX

logger = logging.getLogger(__name__)


MCP_LOG_LEVEL_MAP: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "notice": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
    "alert": logging.CRITICAL,
    "emergency": logging.CRITICAL,
}


async def default_mcp_log_handler(
    params: mcp_types.LoggingMessageNotificationParams,
) -> None:
    """Forward MCP server log messages to Python logging."""
    data = params.data
    msg = data.get("msg", str(data)) if isinstance(data, dict) else str(data)
    name = params.logger or "mcp"
    level = MCP_LOG_LEVEL_MAP.get(params.level, logging.INFO)
    logger.log(level, "[%s] %s", name, msg)


class MCPServerStrict(MCPServerStreamableHTTP):
    """MCP server toolset that aborts the agent run on fatal tool errors.

    Overrides direct_call_tool to intercept errors with the [FATAL] prefix.
    Fatal errors raise RuntimeError (agent run aborts) instead of ModelRetry
    (agent retries with different arguments).
    """

    async def direct_call_tool(
        self, name: str, args: dict[str, Any], metadata: dict[str, Any] | None = None
    ):
        try:
            return await super().direct_call_tool(name, args, metadata)
        except ModelRetry as e:
            msg = str(e)
            if msg.startswith(FATAL_PREFIX):
                raise RuntimeError(msg[len(FATAL_PREFIX) :]) from e
            raise


class MCPServerPrivateData(MCPServerStrict):
    """Dual-instance MCP server toolset for private-data-aware network isolation.

    Holds two MCPServerStrict instances -- normal and isolated --
    both opened at context entry. Every call delegates through _target(), which
    checks session_has_private_data(). Once private data appears, all subsequent
    calls route to the isolated instance. The switch is a one-way ratchet.
    """

    def __init__(self, url: str, url_isolated: str, **kwargs):
        super().__init__(url=url, **kwargs)
        self._normal = MCPServerStrict(url=url, **kwargs)
        self._isolated = MCPServerStrict(url=url_isolated, **kwargs)
        self._is_isolated = False

    @property
    def is_isolated(self) -> bool:
        return self._is_isolated

    def _target(self) -> MCPServerStrict:
        if not self._is_isolated:
            self._is_isolated = session_has_private_data()
            if self._is_isolated:
                logger.info("Private data detected -- switching to isolated instance")
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

    async def direct_call_tool(
        self, name: str, args: dict[str, Any], metadata: dict[str, Any] | None = None
    ):
        return await self._target().direct_call_tool(name, args, metadata)

    async def get_tools(self, ctx):
        return await self._target().get_tools(ctx)

    async def list_tools(self):
        return await self._target().list_tools()

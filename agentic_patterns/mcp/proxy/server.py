"""Entry point for running the MCP proxy as a standalone server."""

import logging
from pathlib import Path

import yaml

from agentic_patterns.mcp.proxy.config import ProxyConfig
from agentic_patterns.mcp.proxy.proxy_server import MCPProxyServer

logger = logging.getLogger(__name__)


def load_proxy_config(config_path: Path | None = None) -> ProxyConfig:
    """Load proxy configuration from config.yaml."""
    if config_path is None:
        config_path = Path("config.yaml")
    with open(config_path) as f:
        data = yaml.safe_load(f)
    proxy_data = data.get("mcp_proxy", {})
    return ProxyConfig(**proxy_data)


async def run_proxy(config_path: Path | None = None) -> MCPProxyServer:
    """Start the MCP proxy server."""
    config = load_proxy_config(config_path)
    proxy = MCPProxyServer(config)
    await proxy.start()
    logger.info("Proxy ready on port %d", config.port)
    # The FastMCP server handles the actual HTTP serving
    return proxy

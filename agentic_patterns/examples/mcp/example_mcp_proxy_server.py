"""Example MCP proxy server. Run with: fastmcp run example_mcp_proxy_server.py --port 8200"""

from agentic_patterns.mcp.proxy import MCPProxyServer, ProxyConfig
from agentic_patterns.mcp.proxy.config import PolicyRule, ProxyBackendConfig, RateLimitConfig

config = ProxyConfig(
    backends=[
        ProxyBackendConfig(name="demo", url="http://127.0.0.1:8301/mcp/"),
        ProxyBackendConfig(name="demo_v2", url="http://127.0.0.1:8302/mcp/"),
    ],
    policies=[
        PolicyRule(role="admin", allow=["*"]),
        PolicyRule(role="default", allow=["demo_*", "proxy_*"], deny=["demo_v2_*"]),
    ],
    rate_limit=RateLimitConfig(requests_per_second=5.0, burst_capacity=10),
)

proxy = MCPProxyServer(config)
mcp = proxy.mcp

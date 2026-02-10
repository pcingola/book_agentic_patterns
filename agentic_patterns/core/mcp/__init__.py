from agentic_patterns.core.mcp.config import (
    MCPClientConfig,
    MCPServerConfig,
    MCPSettings,
    load_mcp_settings,
)
from agentic_patterns.core.mcp.errors import (
    FATAL_PREFIX,
    ToolFatalError,
    ToolRetryError,
)
from agentic_patterns.core.mcp.factories import (
    create_mcp_server,
    create_process_tool_call,
    get_mcp_client,
    get_mcp_clients,
    get_mcp_server,
)
from agentic_patterns.core.mcp.middleware import AuthSessionMiddleware
from agentic_patterns.core.mcp.servers import MCPServerPrivateData, MCPServerStrict

# Backward compatibility
_load_mcp_settings = load_mcp_settings

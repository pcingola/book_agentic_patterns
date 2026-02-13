"""MCP OpenAPI tools wrapping OpenApiConnector.

Connector methods are async and raise standard Python exceptions. The _call()
wrapper converts them to ToolRetryError (user-correctable) or ToolFatalError
(infrastructure).
"""

from fastmcp import Context, FastMCP

from agentic_patterns.core.connectors.openapi.connector import OpenApiConnector
from agentic_patterns.core.mcp import ToolFatalError, ToolRetryError
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission

_openapi = OpenApiConnector()

_RETRYABLE = (ValueError, KeyError)


async def _call(coro) -> str:
    """Await a connector coroutine, converting exceptions to MCP errors."""
    try:
        return await coro
    except _RETRYABLE as e:
        raise ToolRetryError(str(e)) from e
    except (OSError, RuntimeError) as e:
        raise ToolFatalError(str(e)) from e


def register_tools(mcp: FastMCP) -> None:
    """Register all OpenAPI tools on the given MCP server instance."""

    @mcp.tool()
    @tool_permission(ToolPermission.CONNECT)
    async def openapi_list_apis(ctx: Context) -> str:
        """List all available APIs with metadata and endpoint counts."""
        await ctx.info("openapi_list_apis")
        return await _call(_openapi.list_apis())

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def openapi_list_endpoints(
        api_id: str, category: str | None = None, ctx: Context = None
    ) -> str:
        """List endpoints in an API, optionally filtered by category."""
        await ctx.info(f"openapi_list_endpoints: {api_id}")
        return await _call(_openapi.list_endpoints(api_id, category))

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def openapi_show_api_summary(api_id: str, ctx: Context = None) -> str:
        """Show API summary with categorized endpoints."""
        await ctx.info(f"openapi_show_api_summary: {api_id}")
        return await _call(_openapi.show_api_summary(api_id))

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def openapi_show_endpoint_details(
        api_id: str, method: str, path: str, ctx: Context = None
    ) -> str:
        """Show detailed information for a specific endpoint including parameters, request body, and responses."""
        await ctx.info(f"openapi_show_endpoint_details: {api_id} {method} {path}")
        return await _call(_openapi.show_endpoint_details(api_id, method, path))

    @mcp.tool()
    @tool_permission(ToolPermission.CONNECT)
    async def openapi_call_endpoint(
        api_id: str,
        method: str,
        path: str,
        parameters: dict | None = None,
        body: dict | None = None,
        output_file: str | None = None,
        ctx: Context = None,
    ) -> str:
        """Call an API endpoint with specified parameters and body. Results are saved to JSON automatically."""
        await ctx.info(f"openapi_call_endpoint: {api_id} {method} {path}")
        return await _call(
            _openapi.call_endpoint(api_id, method, path, parameters, body, output_file)
        )

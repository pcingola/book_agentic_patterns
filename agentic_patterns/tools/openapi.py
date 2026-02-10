"""Agent tools for OpenAPI operations -- wraps OpenApiConnector."""

from agentic_patterns.core.connectors.openapi.connector import OpenApiConnector
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission


def get_all_tools() -> list:
    """Get all OpenAPI operation tools."""
    connector = OpenApiConnector()

    @tool_permission(ToolPermission.CONNECT)
    async def openapi_list_apis() -> str:
        """List all available APIs with metadata and endpoint counts."""
        return await connector.list_apis()

    @tool_permission(ToolPermission.READ)
    async def openapi_list_endpoints(api_id: str, category: str | None = None) -> str:
        """List endpoints in an API, optionally filtered by category."""
        return await connector.list_endpoints(api_id, category)

    @tool_permission(ToolPermission.READ)
    async def openapi_show_api_summary(api_id: str) -> str:
        """Show API summary with categorized endpoints."""
        return await connector.show_api_summary(api_id)

    @tool_permission(ToolPermission.READ)
    async def openapi_show_endpoint_details(api_id: str, method: str, path: str) -> str:
        """Show detailed information for a specific endpoint including parameters, request body, and responses."""
        return await connector.show_endpoint_details(api_id, method, path)

    @tool_permission(ToolPermission.CONNECT)
    async def openapi_call_endpoint(
        api_id: str,
        method: str,
        path: str,
        parameters: dict | None = None,
        body: dict | None = None,
        output_file: str | None = None,
    ) -> str:
        """Call an API endpoint with specified parameters and body. Results are saved to JSON automatically."""
        return await connector.call_endpoint(api_id, method, path, parameters, body, output_file)

    return [
        openapi_list_apis,
        openapi_list_endpoints,
        openapi_show_api_summary,
        openapi_show_endpoint_details,
        openapi_call_endpoint,
    ]

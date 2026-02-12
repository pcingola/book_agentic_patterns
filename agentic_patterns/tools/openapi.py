"""Agent tools for OpenAPI operations -- wraps OpenApiConnector."""

from pydantic_ai import ModelRetry

from agentic_patterns.core.connectors.openapi.connector import OpenApiConnector
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission


def get_all_tools() -> list:
    """Get all OpenAPI operation tools."""
    connector = OpenApiConnector()

    @tool_permission(ToolPermission.CONNECT)
    async def openapi_list_apis() -> str:
        """List all available APIs with metadata and endpoint counts."""
        try:
            return await connector.list_apis()
        except (ValueError, KeyError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    async def openapi_list_endpoints(api_id: str, category: str | None = None) -> str:
        """List endpoints in an API, optionally filtered by category."""
        try:
            return await connector.list_endpoints(api_id, category)
        except (ValueError, KeyError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    async def openapi_show_api_summary(api_id: str) -> str:
        """Show API summary with categorized endpoints."""
        try:
            return await connector.show_api_summary(api_id)
        except (ValueError, KeyError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    async def openapi_show_endpoint_details(api_id: str, method: str, path: str) -> str:
        """Show detailed information for a specific endpoint including parameters, request body, and responses."""
        try:
            return await connector.show_endpoint_details(api_id, method, path)
        except (ValueError, KeyError) as e:
            raise ModelRetry(str(e)) from e

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
        try:
            return await connector.call_endpoint(
                api_id, method, path, parameters, body, output_file
            )
        except (ValueError, KeyError) as e:
            raise ModelRetry(str(e)) from e

    return [
        openapi_list_apis,
        openapi_list_endpoints,
        openapi_show_api_summary,
        openapi_show_endpoint_details,
        openapi_call_endpoint,
    ]

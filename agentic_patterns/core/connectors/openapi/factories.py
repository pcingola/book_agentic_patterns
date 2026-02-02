"""Factory functions for creating parsers and clients."""

from agentic_patterns.core.connectors.openapi.client.http_client import ApiHttpClient
from agentic_patterns.core.connectors.openapi.client.requests_client import RequestsApiClient
from agentic_patterns.core.connectors.openapi.extraction.openapi_v3_parser import OpenApiV3Parser
from agentic_patterns.core.connectors.openapi.extraction.spec_parser import ApiSpecParser


def create_http_client(api_id: str, base_url: str) -> ApiHttpClient:
    """Create HTTP client for API requests."""
    return RequestsApiClient(api_id, base_url)


def create_spec_parser(spec_dict: dict, api_id: str, base_url: str | None = None) -> ApiSpecParser:
    """Create appropriate parser based on spec format.

    Args:
        spec_dict: Parsed OpenAPI specification
        api_id: API identifier
        base_url: Optional base URL from config to override spec's servers section
    """
    # Detect OpenAPI version
    if "openapi" in spec_dict:
        version = spec_dict["openapi"]
        match version:
            case v if v.startswith("3."):
                return OpenApiV3Parser(spec_dict, api_id, base_url)
            case _:
                raise ValueError(f"Unsupported OpenAPI version: {version}. Only OpenAPI 3.x is supported.")
    elif "swagger" in spec_dict:
        swagger_version = spec_dict["swagger"]
        raise ValueError(f"Swagger {swagger_version} is not supported. Only OpenAPI 3.x is supported.")
    else:
        raise ValueError("Unable to determine API spec format. Missing 'openapi' or 'swagger' field.")

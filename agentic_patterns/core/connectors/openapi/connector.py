"""OpenApiConnector: unified connector for OpenAPI operations."""

import hashlib
import json
from datetime import datetime
from pathlib import PurePosixPath

from agentic_patterns.core.compliance.private_data import DataSensitivity, PrivateData
from agentic_patterns.core.connectors.base import Connector
from agentic_patterns.core.connectors.openapi.api_connection_config import ApiConnectionConfigs
from agentic_patterns.core.connectors.openapi.api_infos import ApiInfos
from agentic_patterns.core.context.decorators import context_result
from agentic_patterns.core.workspace import workspace_to_host_path, write_to_workspace


class OpenApiConnector(Connector):
    """OpenAPI operations."""

    @context_result()
    async def call_endpoint(
        self,
        api_id: str,
        method: str,
        path: str,
        parameters: dict | None = None,
        body: dict | None = None,
        output_file: str | None = None,
    ) -> str:
        """Call API endpoint and return response."""
        try:
            api_infos = ApiInfos.get()
            api_info = api_infos.get_api_info(api_id)
            client = api_infos.get_client(api_id)

            # Verify endpoint exists
            endpoint = api_info.get_endpoint(method, path)
            if endpoint is None:
                return f"[Error] Endpoint not found: {method} {path}"

            # Split parameters by location
            query_params = {}
            headers = {}
            path_params = {}

            if parameters:
                for param_name, param_value in parameters.items():
                    # Find parameter definition
                    param_info = None
                    for p in endpoint.parameters:
                        if p.name == param_name:
                            param_info = p
                            break

                    if param_info:
                        match param_info.location:
                            case "query":
                                query_params[param_name] = param_value
                            case "header":
                                headers[param_name] = param_value
                            case "path":
                                path_params[param_name] = param_value

            # Replace path parameters
            final_path = path
            for param_name, param_value in path_params.items():
                final_path = final_path.replace(f"{{{param_name}}}", str(param_value))

            # Make request
            response = await client.request_async(
                method=method,
                path=final_path,
                params=query_params if query_params else None,
                headers=headers if headers else None,
                json=body,
            )

            # Tag session when reading from sensitive sources
            api_config = ApiConnectionConfigs.get().get_config(api_id)
            if api_config.sensitivity != DataSensitivity.PUBLIC:
                pd = PrivateData()
                pd.add_private_dataset(f"api:{api_id}", api_config.sensitivity)

            # Format response
            status_code = response["status_code"]
            response_body = response["body"]

            # Save full response if output_file specified or response is large
            if not output_file:
                request_hash = hashlib.md5(f"{method}{path}".encode()).hexdigest()[:8]
                output_file = f"/workspace/results/api_{request_hash}.json"

            # Prepare full response data
            full_response = {
                "status_code": status_code,
                "headers": response["headers"],
                "body": response_body,
                "request": {
                    "method": method,
                    "path": path,
                    "parameters": parameters,
                    "body": body,
                },
                "metadata": {
                    "api_id": api_id,
                    "timestamp": datetime.now().isoformat(),
                },
            }

            # Write to workspace
            write_to_workspace(output_file, json.dumps(full_response, indent=2))
            host_path = workspace_to_host_path(PurePosixPath(output_file))

            # Return formatted response
            if status_code >= 400:
                return f"[Error] HTTP {status_code}\nFull response saved to: {output_file}\n\nResponse body:\n{json.dumps(response_body, indent=2)}"

            # Truncate response body for preview
            body_str = json.dumps(response_body, indent=2) if isinstance(response_body, dict) else str(response_body)
            if len(body_str) > 500:
                body_str = body_str[:500] + f"...\n\n[Full response ({len(body_str)} chars) saved to: {output_file}]"

            return f"HTTP {status_code}\nFull response saved to: {output_file}\n\nResponse body (preview):\n{body_str}"

        except Exception as e:
            return f"[Error] {str(e)}"

    async def list_apis(self) -> str:
        """List all available APIs with metadata."""
        try:
            api_infos = ApiInfos.get()
            apis = []
            for api_id in api_infos.list_api_ids():
                api_info = api_infos.get_api_info(api_id)
                apis.append(
                    {
                        "api_id": api_id,
                        "title": api_info.title,
                        "version": api_info.version,
                        "description": api_info.description,
                        "endpoint_count": len(api_info.endpoints),
                        "base_url": api_info.base_url,
                    }
                )
            return json.dumps(apis, indent=2)
        except Exception as e:
            return f"[Error] {str(e)}"

    @context_result()
    async def list_endpoints(self, api_id: str, category: str | None = None) -> str:
        """List endpoints, optionally filtered by category."""
        try:
            api_infos = ApiInfos.get()
            api_info = api_infos.get_api_info(api_id)

            endpoints = []
            for endpoint in api_info.endpoints:
                if category and endpoint.category != category:
                    continue

                endpoints.append(
                    {
                        "method": endpoint.method,
                        "path": endpoint.path,
                        "operation_id": endpoint.operation_id,
                        "summary": endpoint.summary,
                        "category": endpoint.category,
                        "deprecated": endpoint.deprecated,
                        "parameter_count": len(endpoint.parameters),
                        "has_request_body": endpoint.request_body is not None,
                    }
                )

            result = {
                "api_id": api_id,
                "title": api_info.title,
                "endpoint_count": len(endpoints),
                "endpoints": endpoints,
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"[Error] {str(e)}"

    async def show_api_summary(self, api_id: str) -> str:
        """Show API summary with categorized endpoints."""
        try:
            api_infos = ApiInfos.get()
            api_info = api_infos.get_api_info(api_id)
            return api_info.format_summary()
        except Exception as e:
            return f"[Error] {str(e)}"

    async def show_endpoint_details(self, api_id: str, method: str, path: str) -> str:
        """Show detailed endpoint information."""
        try:
            api_infos = ApiInfos.get()
            api_info = api_infos.get_api_info(api_id)
            endpoint = api_info.get_endpoint(method, path)

            if endpoint is None:
                return f"[Error] Endpoint not found: {method} {path}"

            details = {
                "method": endpoint.method,
                "path": endpoint.path,
                "operation_id": endpoint.operation_id,
                "summary": endpoint.summary,
                "description": endpoint.description,
                "category": endpoint.category,
                "deprecated": endpoint.deprecated,
                "tags": endpoint.tags,
                "parameters": [
                    {
                        "name": p.name,
                        "location": p.location,
                        "required": p.required,
                        "type": p.schema_type,
                        "description": p.description,
                        "default": p.default,
                        "enum": p.enum_values,
                        "example": p.example,
                    }
                    for p in endpoint.parameters
                ],
                "request_body": None,
                "responses": [
                    {
                        "status_code": r.status_code,
                        "content_type": r.content_type,
                        "description": r.description,
                        "schema": json.loads(r.schema_json) if r.schema_json else None,
                        "example": r.example,
                    }
                    for r in endpoint.responses
                ],
                "example_request": endpoint.example_request,
            }

            if endpoint.request_body:
                details["request_body"] = {
                    "content_type": endpoint.request_body.content_type,
                    "description": endpoint.request_body.description,
                    "schema": json.loads(endpoint.request_body.schema_json),
                    "example": endpoint.request_body.example,
                }

            return json.dumps(details, indent=2)
        except Exception as e:
            return f"[Error] {str(e)}"

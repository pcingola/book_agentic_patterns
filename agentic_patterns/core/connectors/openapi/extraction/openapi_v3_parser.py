"""OpenAPI 3.x specification parser."""

import json

from agentic_patterns.core.connectors.openapi.extraction.spec_parser import (
    ApiSpecParser,
)
from agentic_patterns.core.connectors.openapi.models import (
    ApiInfo,
    EndpointInfo,
    ParameterInfo,
    RequestSchemaInfo,
    ResponseSchemaInfo,
)


class OpenApiV3Parser(ApiSpecParser):
    """Parser for OpenAPI 3.x specifications."""

    def parse(self) -> ApiInfo:
        """Parse OpenAPI 3.x spec into ApiInfo.

        Uses base_url from constructor if provided (from config), otherwise falls back
        to the spec's servers section. This allows config to override the spec's base URL
        for environment-specific deployments (dev/staging/prod) or local testing.
        """
        info = self.spec_dict.get("info", {})

        # Use config's base_url if provided, otherwise fall back to spec's servers section
        if self.base_url:
            base_url = self.base_url
        else:
            servers = self.spec_dict.get("servers", [])
            base_url = servers[0]["url"] if servers else ""

        api_info = ApiInfo(
            api_id=self.api_id,
            title=info.get("title", "Untitled API"),
            version=info.get("version", "1.0.0"),
            description=info.get("description", ""),
            base_url=base_url,
        )

        # Parse paths and operations
        paths = self.spec_dict.get("paths", {})
        for path, path_item in paths.items():
            # Extract parameters defined at path level
            path_parameters = self._parse_parameters(path_item.get("parameters", []))

            # Parse each HTTP method
            for method in [
                "get",
                "post",
                "put",
                "delete",
                "patch",
                "head",
                "options",
                "trace",
            ]:
                if method not in path_item:
                    continue

                operation = path_item[method]
                endpoint = self._parse_operation(
                    path, method.upper(), operation, path_parameters
                )
                api_info.add_endpoint(endpoint)

        return api_info

    def _parse_operation(
        self,
        path: str,
        method: str,
        operation: dict,
        path_parameters: list[ParameterInfo],
    ) -> EndpointInfo:
        """Parse a single operation (endpoint)."""
        operation_id = operation.get(
            "operationId", f"{method.lower()}_{path.replace('/', '_')}"
        )
        summary = operation.get("summary", "")
        description = operation.get("description", "")
        tags = operation.get("tags", [])
        deprecated = operation.get("deprecated", False)

        # Combine path-level and operation-level parameters
        parameters = path_parameters.copy()
        parameters.extend(self._parse_parameters(operation.get("parameters", [])))

        # Parse request body
        request_body = None
        if "requestBody" in operation:
            request_body = self._parse_request_body(operation["requestBody"])

        # Parse responses
        responses = []
        for status_code, response_spec in operation.get("responses", {}).items():
            responses.extend(self._parse_response(status_code, response_spec))

        return EndpointInfo(
            path=path,
            method=method,
            operation_id=operation_id,
            summary=summary,
            description=description,
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            tags=tags,
            deprecated=deprecated,
        )

    def _parse_parameters(self, parameters: list) -> list[ParameterInfo]:
        """Parse parameter definitions."""
        result = []
        for param in parameters:
            # Handle $ref
            if "$ref" in param:
                param = self._resolve_ref(param["$ref"])

            schema = param.get("schema", {})
            param_info = ParameterInfo(
                name=param["name"],
                location=param["in"],
                required=param.get("required", False),
                schema_type=schema.get("type", "string"),
                description=param.get("description", ""),
                default=schema.get("default"),
                enum_values=schema.get("enum"),
                example=param.get("example") or schema.get("example"),
            )
            result.append(param_info)
        return result

    def _parse_request_body(self, request_body: dict) -> RequestSchemaInfo | None:
        """Parse request body definition."""
        # Handle $ref
        if "$ref" in request_body:
            request_body = self._resolve_ref(request_body["$ref"])

        content = request_body.get("content", {})
        if not content:
            return None

        # Take the first content type (typically application/json)
        content_type = list(content.keys())[0]
        media_type = content[content_type]
        schema = media_type.get("schema", {})

        # Handle $ref in schema
        if "$ref" in schema:
            schema = self._resolve_ref(schema["$ref"])

        return RequestSchemaInfo(
            content_type=content_type,
            schema_json=json.dumps(schema, indent=2),
            description=request_body.get("description", ""),
            example=json.dumps(media_type.get("example"))
            if "example" in media_type
            else None,
        )

    def _parse_response(
        self, status_code: str, response_spec: dict
    ) -> list[ResponseSchemaInfo]:
        """Parse response definitions."""
        # Handle $ref
        if "$ref" in response_spec:
            response_spec = self._resolve_ref(response_spec["$ref"])

        result = []
        content = response_spec.get("content", {})

        if not content:
            # Response with no content (e.g., 204 No Content)
            result.append(
                ResponseSchemaInfo(
                    status_code=status_code,
                    content_type="",
                    schema_json="{}",
                    description=response_spec.get("description", ""),
                )
            )
        else:
            # Parse each content type
            for content_type, media_type in content.items():
                schema = media_type.get("schema", {})

                # Handle $ref in schema
                if "$ref" in schema:
                    schema = self._resolve_ref(schema["$ref"])

                result.append(
                    ResponseSchemaInfo(
                        status_code=status_code,
                        content_type=content_type,
                        schema_json=json.dumps(schema, indent=2),
                        description=response_spec.get("description", ""),
                        example=json.dumps(media_type.get("example"))
                        if "example" in media_type
                        else None,
                    )
                )

        return result

    def _resolve_ref(self, ref: str) -> dict:
        """Resolve a $ref reference (supports #/components/... format)."""
        if not ref.startswith("#/"):
            raise ValueError(f"Unsupported $ref format: {ref}")

        # Split the reference path
        parts = ref[2:].split("/")  # Remove leading '#/'

        # Navigate through the spec dict
        result = self.spec_dict
        for part in parts:
            if part not in result:
                raise ValueError(f"Cannot resolve $ref: {ref}")
            result = result[part]

        return result

"""OpenAPI data models for API specifications."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class ParameterInfo:
    """Information about an API endpoint parameter."""

    name: str
    location: str  # query, header, path, cookie
    required: bool
    schema_type: str
    description: str = ""
    default: str | None = None
    enum_values: list[str] | None = None
    example: str | None = None

    def __str__(self) -> str:
        flags = []
        if self.required:
            flags.append("required")
        if self.enum_values:
            flags.append(f"enum({len(self.enum_values)} values)")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        return f"ParameterInfo({self.name!r}, {self.location}, {self.schema_type}{flag_str})"

    @classmethod
    def from_dict(cls, data: dict) -> "ParameterInfo":
        return cls(
            name=data["name"],
            location=data["location"],
            required=data["required"],
            schema_type=data["schema_type"],
            description=data.get("description", ""),
            default=data.get("default"),
            enum_values=data.get("enum_values"),
            example=data.get("example"),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "location": self.location,
            "required": self.required,
            "schema_type": self.schema_type,
            "description": self.description,
            "default": self.default,
            "enum_values": self.enum_values,
            "example": self.example,
        }


@dataclass
class RequestSchemaInfo:
    """Information about request body schema."""

    content_type: str
    schema_json: str  # JSON schema as string
    description: str = ""
    example: str | None = None

    def __str__(self) -> str:
        schema_preview = (
            self.schema_json[:50] + "..."
            if len(self.schema_json) > 50
            else self.schema_json
        )
        return f"RequestSchemaInfo({self.content_type!r}, schema={schema_preview!r})"

    @classmethod
    def from_dict(cls, data: dict) -> "RequestSchemaInfo":
        return cls(
            content_type=data["content_type"],
            schema_json=data["schema_json"],
            description=data.get("description", ""),
            example=data.get("example"),
        )

    def to_dict(self) -> dict:
        return {
            "content_type": self.content_type,
            "schema_json": self.schema_json,
            "description": self.description,
            "example": self.example,
        }


@dataclass
class ResponseSchemaInfo:
    """Information about response schema."""

    status_code: str
    content_type: str
    schema_json: str  # JSON schema as string
    description: str = ""
    example: str | None = None

    def __str__(self) -> str:
        schema_preview = (
            self.schema_json[:50] + "..."
            if len(self.schema_json) > 50
            else self.schema_json
        )
        return f"ResponseSchemaInfo({self.status_code}, {self.content_type!r}, schema={schema_preview!r})"

    @classmethod
    def from_dict(cls, data: dict) -> "ResponseSchemaInfo":
        return cls(
            status_code=data["status_code"],
            content_type=data["content_type"],
            schema_json=data["schema_json"],
            description=data.get("description", ""),
            example=data.get("example"),
        )

    def to_dict(self) -> dict:
        return {
            "status_code": self.status_code,
            "content_type": self.content_type,
            "schema_json": self.schema_json,
            "description": self.description,
            "example": self.example,
        }


@dataclass
class EndpointInfo:
    """Information about an API endpoint."""

    path: str
    method: str
    operation_id: str
    summary: str = ""
    description: str = ""
    parameters: list[ParameterInfo] = field(default_factory=list)
    request_body: RequestSchemaInfo | None = None
    responses: list[ResponseSchemaInfo] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    deprecated: bool = False
    category: str = ""  # LLM-generated category
    example_request: str = ""  # LLM-generated example
    api: "ApiInfo | None" = field(default=None, repr=False, compare=False)

    def __str__(self) -> str:
        params_str = f", {len(self.parameters)} params" if self.parameters else ""
        category_str = f", category={self.category!r}" if self.category else ""
        return f"EndpointInfo({self.method} {self.path}{params_str}{category_str})"

    @classmethod
    def from_dict(cls, data: dict, api: "ApiInfo | None" = None) -> "EndpointInfo":
        return cls(
            path=data["path"],
            method=data["method"],
            operation_id=data["operation_id"],
            summary=data.get("summary", ""),
            description=data.get("description", ""),
            parameters=[ParameterInfo.from_dict(p) for p in data.get("parameters", [])],
            request_body=RequestSchemaInfo.from_dict(data["request_body"])
            if data.get("request_body")
            else None,
            responses=[
                ResponseSchemaInfo.from_dict(r) for r in data.get("responses", [])
            ],
            tags=data.get("tags", []),
            deprecated=data.get("deprecated", False),
            category=data.get("category", ""),
            example_request=data.get("example_request", ""),
            api=api,
        )

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "method": self.method,
            "operation_id": self.operation_id,
            "summary": self.summary,
            "description": self.description,
            "parameters": [p.to_dict() for p in self.parameters],
            "request_body": self.request_body.to_dict() if self.request_body else None,
            "responses": [r.to_dict() for r in self.responses],
            "tags": self.tags,
            "deprecated": self.deprecated,
            "category": self.category,
            "example_request": self.example_request,
        }


@dataclass
class ApiInfo:
    """Complete API specification information."""

    api_id: str
    title: str
    version: str
    description: str = ""
    base_url: str = ""
    endpoints: list[EndpointInfo] = field(default_factory=list)
    example_use_cases: list[str] = field(default_factory=list)
    cache_file_path: Path | None = field(default=None, repr=False, compare=False)

    def __str__(self) -> str:
        desc_preview = (
            self.description[:50] + "..."
            if len(self.description) > 50
            else self.description
        )
        return f"ApiInfo(api_id={self.api_id!r}, title={self.title!r}, endpoints={len(self.endpoints)}, description={desc_preview!r})"

    def __iter__(self):
        return iter(self.endpoints)

    def __len__(self) -> int:
        return len(self.endpoints)

    def add_endpoint(self, endpoint: EndpointInfo) -> None:
        endpoint.api = self
        self.endpoints.append(endpoint)

    def format_summary(self) -> str:
        """Format API summary with categorized endpoints."""
        lines = [f"API: {self.title} (v{self.version})"]
        if self.description:
            lines.append(f"Description: {self.description}")
        lines.append(f"Base URL: {self.base_url}")
        lines.append(f"Total Endpoints: {len(self.endpoints)}")

        categories = self.get_endpoints_by_category()
        if categories:
            lines.append("\nEndpoints by Category:")
            for category, endpoints in sorted(categories.items()):
                lines.append(f"  {category}: {len(endpoints)} endpoints")
                for endpoint in sorted(endpoints, key=lambda e: e.path):
                    lines.append(f"    {endpoint.method:6} {endpoint.path}")

        return "\n".join(lines)

    def get_endpoint(self, method: str, path: str) -> EndpointInfo | None:
        for endpoint in self.endpoints:
            if endpoint.method.upper() == method.upper() and endpoint.path == path:
                return endpoint
        return None

    def get_endpoints_by_category(self) -> dict[str, list[EndpointInfo]]:
        categories: dict[str, list[EndpointInfo]] = {}
        for endpoint in self.endpoints:
            category = endpoint.category or "Uncategorized"
            if category not in categories:
                categories[category] = []
            categories[category].append(endpoint)
        return categories

    @classmethod
    def from_dict(cls, data: dict, cache_file_path: Path | None = None) -> "ApiInfo":
        api_info = cls(
            api_id=data["api_id"],
            title=data["title"],
            version=data["version"],
            description=data.get("description", ""),
            base_url=data.get("base_url", ""),
            endpoints=[],
            example_use_cases=data.get("example_use_cases", []),
            cache_file_path=cache_file_path,
        )
        api_info.endpoints = [
            EndpointInfo.from_dict(e, api=api_info) for e in data.get("endpoints", [])
        ]
        return api_info

    @classmethod
    def load(
        cls, api_id: str | None = None, input_path: Path | None = None
    ) -> "ApiInfo":
        """Load API info from JSON file."""
        if input_path is None:
            if api_id is None:
                raise ValueError("Either api_id or input_path must be provided")
            from agentic_patterns.core.connectors.openapi.config import (
                API_CACHE_DIR,
                API_INFO_EXT,
            )

            input_path = API_CACHE_DIR / api_id / f"{api_id}{API_INFO_EXT}"
        data = json.loads(input_path.read_text())
        return cls.from_dict(data, cache_file_path=input_path)

    def save(self, output_path: Path | None = None) -> Path:
        """Save API info to JSON file."""
        if output_path is None:
            if self.cache_file_path is not None:
                output_path = self.cache_file_path
            else:
                from agentic_patterns.core.connectors.openapi.config import (
                    API_CACHE_DIR,
                    API_INFO_EXT,
                )

                output_dir = API_CACHE_DIR / self.api_id
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{self.api_id}{API_INFO_EXT}"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_dict(), indent=2))
        self.cache_file_path = output_path
        return output_path

    def to_dict(self) -> dict:
        return {
            "api_id": self.api_id,
            "title": self.title,
            "version": self.version,
            "description": self.description,
            "base_url": self.base_url,
            "endpoints": [e.to_dict() for e in self.endpoints],
            "example_use_cases": self.example_use_cases,
        }

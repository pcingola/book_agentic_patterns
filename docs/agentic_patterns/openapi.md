# OpenAPI Connector

`OpenApiConnector` lets agents interact with REST APIs described by OpenAPI 3.x specifications. The API spec is ingested once offline; at runtime the agent discovers endpoints, inspects parameters, and makes validated calls.

## Configuration and Ingestion

APIs are declared in `apis.yaml`:

```yaml
- id: cbioportal
  name: cBioPortal
  spec_url: https://www.cbioportal.org/api/v3/api-docs
  base_url: https://www.cbioportal.org
```

The ingestion CLI fetches the spec, parses endpoints, runs AI-powered annotation (descriptions, categories, example requests), and caches the result:

```bash
ingest-openapi cbioportal
```

At runtime, `ApiInfos.get()` loads cached metadata without re-fetching.

## Data Models

`ApiInfo` -- API-level metadata: `api_id`, `title`, `version`, `description`, `base_url`, `endpoints: list[EndpointInfo]`, `example_use_cases`.

`EndpointInfo` -- endpoint specification: `path`, `method`, `operation_id`, `summary`, `description`, `parameters: list[ParameterInfo]`, `request_body: RequestSchemaInfo | None`, `responses: list[ResponseSchemaInfo]`, `category`, `example_request`.

`ParameterInfo` -- single parameter: `name`, `location` (query/header/path/cookie), `required`, `schema_type`, `description`, `enum_values`, `example`.

## Operations

`list_apis()` -- all registered APIs with metadata and endpoint counts.

`list_endpoints(api_id, category=None)` -- endpoints for an API, optionally filtered by category.

`show_api_summary(api_id)` -- categorized endpoint overview.

`show_endpoint_details(api_id, method, path)` -- parameters, request body schema, response schemas, and example request.

`call_endpoint(api_id, method, path, parameters=None, body=None, output_file=None)` -- execute an HTTP request. Routes parameters to query/header/path automatically. Saves response to a JSON file. If the API has a non-PUBLIC sensitivity level, tags the session via `PrivateData`.

## Tool Wrappers

The OpenAPI tools in `agentic_patterns.tools.openapi` wrap the connector with `@tool_permission` annotations:

```python
from agentic_patterns.tools.openapi import get_all_tools

tools = get_all_tools()  # returns 5 tool functions
agent = get_agent(tools=tools)
```

Discovery tools (`list_endpoints`, `show_api_summary`, `show_endpoint_details`) carry READ permission. External-facing tools (`list_apis`, `call_endpoint`) carry CONNECT permission, which is blocked when the session contains private data.

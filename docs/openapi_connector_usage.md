# OpenAPI Connector Usage Guide

The OpenAPI connector allows AI agents to interact with REST APIs using OpenAPI 3.x specifications.

## Quick Start

### 1. Configure APIs

Create or edit `apis.yaml` at the project root:

```yaml
apis:
  petstore:
    spec_source: https://petstore3.swagger.io/api/v3/openapi.json
    base_url: https://petstore3.swagger.io/api/v3

  local_api:
    spec_source: specs/my_api.yaml  # Relative paths supported
    base_url: http://localhost:8000
```

Environment variables are supported using `${VAR}` syntax.

#### Base URL Override Behavior

The `base_url` in the configuration **overrides** the `servers` section in the OpenAPI spec. This provides flexibility for:

**Environment-specific deployments:**
```yaml
apis:
  myapi_dev:
    spec_source: https://api.example.com/openapi.json
    base_url: https://dev.api.example.com  # Dev environment

  myapi_prod:
    spec_source: https://api.example.com/openapi.json
    base_url: https://api.example.com      # Production
```

**Local testing:**
```yaml
apis:
  myapi_local:
    spec_source: https://api.example.com/openapi.json
    base_url: http://localhost:8000  # Override to local instance
```

**Correcting outdated specs:**
If the OpenAPI spec contains an outdated or incorrect server URL, the config's `base_url` takes precedence.

If `base_url` is not specified in the config, the connector falls back to the first URL in the spec's `servers` section.

### 2. Ingest and Annotate API Spec

Run the ingestion CLI to fetch the OpenAPI spec and enrich it with AI-generated descriptions:

```bash
python -m agentic_patterns.core.connectors.openapi.cli.ingest petstore --verbose
```

This will:
- Download the OpenAPI specification
- Parse endpoints, parameters, and schemas
- Generate API and endpoint descriptions using LLM
- Categorize endpoints into logical groups
- Generate example curl requests
- Save annotated data to `data/api/petstore/petstore.api_info.json`

### 3. Use with Python

```python
from agentic_patterns.core.connectors.openapi.api_connection_config import ApiConnectionConfigs
from agentic_patterns.core.connectors.openapi.config import APIS_YAML_PATH
from agentic_patterns.core.connectors.openapi.connector import OpenApiConnector

# Load configurations
configs = ApiConnectionConfigs.get()
configs.load_from_yaml(APIS_YAML_PATH)

# Create connector
connector = OpenApiConnector()

# List available APIs
apis = await connector.list_apis()

# Show API summary
summary = await connector.show_api_summary("petstore")

# List endpoints
endpoints = await connector.list_endpoints("petstore")

# Get endpoint details
details = await connector.show_endpoint_details("petstore", "GET", "/pet/{petId}")

# Call an endpoint
result = await connector.call_endpoint(
    api_id="petstore",
    method="GET",
    path="/pet/{petId}",
    parameters={"petId": "1"}
)
```

### 4. Use with PydanticAI Agents

```python
from pydantic_ai import Agent
from agentic_patterns.core.tools.openapi import get_all_tools

agent = Agent(
    "openai:gpt-4",
    tools=get_all_tools(),
    system_prompt="You are a helpful assistant that can interact with REST APIs."
)

# Agent can now use OpenAPI tools
result = await agent.run("What APIs are available?")
result = await agent.run("Show me the petstore API endpoints")
result = await agent.run("Get details for the endpoint that retrieves a pet by ID")
result = await agent.run("Get pet with ID 1 from the petstore API")
```

## Available Tools

When using `get_all_tools()`, agents have access to:

- `openapi_list_apis()` - List all available APIs
- `openapi_list_endpoints(api_id, category)` - List endpoints, optionally filtered by category
- `openapi_show_api_summary(api_id)` - Show API summary with categorized endpoints
- `openapi_show_endpoint_details(api_id, method, path)` - Show detailed endpoint information
- `openapi_call_endpoint(api_id, method, path, parameters, body, output_file)` - Call an API endpoint

## Architecture

The connector follows the layered architecture pattern:

```
Configuration Layer (apis.yaml, ApiConnectionConfig)
        ↓
Registry Layer (ApiInfos, ApiConnectionConfigs singletons)
        ↓
Extraction Layer (ApiSpecExtractor, OpenApiV3Parser)
        ↓
Annotation Layer (ApiSpecAnnotator - LLM enrichment)
        ↓
Connector Layer (OpenApiConnector - operations)
        ↓
Tool Layer (tools/openapi.py - agent interface)
```

## Data Models

- `ApiInfo` - Complete API specification with metadata
- `EndpointInfo` - Individual endpoint details
- `ParameterInfo` - Parameter definitions
- `RequestSchemaInfo` - Request body schema
- `ResponseSchemaInfo` - Response schema

All models support serialization with `to_dict()`, `from_dict()`, `save()`, and `load()`.

## Context Management

Large API responses are automatically saved to the workspace (`/workspace/results/`) and truncated in the agent's context to prevent context window overflow. The `@context_result()` decorator handles this automatically.

## Limitations (Current Implementation)

- OpenAPI 3.x only (Swagger 2.0 not supported)
- No authentication (open APIs only)
- No rate limiting
- Sync HTTP client with async wrapper (could be improved with httpx)

## Future Enhancements

- Authentication support (bearer tokens, API keys, OAuth2)
- Rate limiting
- Swagger 2.0 support
- Request/response validation
- Async HTTP client (httpx)
- GraphQL support

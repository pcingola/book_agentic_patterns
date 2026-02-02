# OpenAPI Connector Implementation Plan

## Overview

Implement an OpenAPI connector following the SQL connector architecture patterns. This connector will allow AI agents to interact with OpenAPI-based REST APIs by ingesting specs, generating descriptions with LLM annotation, and providing tools for listing and calling endpoints.

## Scope

**Initial Implementation:**
- OpenAPI 3.x spec support only (not Swagger 2.0)
- No authentication (open APIs only)
- Mandatory LLM annotation pipeline during ingestion
- No rate limiting
- Support both URL and file-based spec sources
- Large response handling with @context_result() decorator

## Architecture

The connector follows the layered architecture pattern established by the SQL connector:

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

## Module Structure

```
agentic_patterns/core/connectors/openapi/
├── __init__.py
├── models.py                  # ApiInfo, EndpointInfo, ParameterInfo, etc.
├── config.py                  # Constants (API_CACHE_DIR, paths)
├── api_connection_config.py   # ApiConnectionConfig, ApiConnectionConfigs
├── api_infos.py              # ApiInfos singleton registry
├── connector.py              # OpenApiConnector (core operations)
├── factories.py              # create_spec_parser(), create_http_client()
├── extraction/
│   ├── __init__.py
│   ├── spec_extractor.py     # ApiSpecExtractor (fetch + parse + cache)
│   ├── spec_parser.py        # Abstract ApiSpecParser
│   └── openapi_v3_parser.py  # OpenApiV3Parser implementation
├── annotation/
│   ├── __init__.py
│   └── annotator.py          # ApiSpecAnnotator (LLM enrichment)
├── client/
│   ├── __init__.py
│   ├── http_client.py        # Abstract ApiHttpClient
│   └── requests_client.py    # RequestsApiClient implementation
└── cli/
    ├── __init__.py
    └── ingest.py             # CLI for ingestion + annotation

agentic_patterns/core/tools/
└── openapi.py                # Tool wrappers with @tool_permission

prompts/openapi/
└── annotation/
    ├── api_description.md
    ├── endpoint_description.md
    └── endpoint_categorization.md

data/api/                     # Runtime cache
└── {api_id}/
    └── {api_id}.api_info.json
```

## Data Models (models.py)

All models follow the SQL connector pattern with `__str__()`, `from_dict()`, `to_dict()`, `save()`, `load()` methods.

**ParameterInfo:**
- name, location (query/header/path), required, schema_type
- description, default, enum_values, example

**RequestSchemaInfo:**
- content_type, schema_json (JSON schema as string)
- example, description

**ResponseSchemaInfo:**
- status_code, content_type, schema_json
- description, example

**EndpointInfo:**
- path, method, operation_id, summary, description
- parameters: list[ParameterInfo]
- request_body: RequestSchemaInfo | None
- responses: list[ResponseSchemaInfo]
- tags: list[str], deprecated: bool
- category: str (LLM-generated)
- example_request: str (LLM-generated)
- api: ApiInfo reference

**ApiInfo:**
- api_id, title, version, description, base_url
- endpoints: list[EndpointInfo]
- example_use_cases: list[str]
- Methods: add_endpoint(), get_endpoint(), get_endpoints_by_category(), format_summary()

## Configuration

**config.py:**
```python
APIS_YAML_PATH = MAIN_PROJECT_DIR / "apis.yaml"
API_CACHE_DIR = DATA_DIR / "api"
API_INFO_EXT = ".api_info.json"
REQUEST_TIMEOUT = int(os.getenv("API_REQUEST_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))
```

**apis.yaml structure (no auth):**
```yaml
apis:
  petstore:
    spec_source: https://petstore3.swagger.io/api/v3/openapi.json
    base_url: https://petstore3.swagger.io/api/v3

  local_api:
    spec_source: specs/my_api.yaml  # Relative path
    base_url: http://localhost:8000
```

**ApiConnectionConfig (Pydantic):**
- api_id, spec_source, base_url
- Load from YAML with environment variable expansion
- Resolve relative file paths

**ApiConnectionConfigs (singleton):**
- Registry of all API configs
- load_from_yaml(), get_config(), list_api_ids()

## Extraction Layer

**ApiSpecExtractor:**
- `connect(spec_source)`: Fetch from URL or file, detect format, create parser
- `api_info(cache=True)`: Extract ApiInfo, save to cache
- Context manager support (optional)

**ApiSpecParser (abstract):**
- Base class with `parse() -> ApiInfo` method

**OpenApiV3Parser:**
- Parse OpenAPI 3.x spec into ApiInfo structure
- Extract info, servers, paths, operations, parameters
- Parse request bodies, responses, schemas
- Handle $ref resolution for parameters and schemas

## Annotation Layer

**ApiSpecAnnotator:**
- Mandatory LLM enrichment pipeline
- `annotate(spec_source) -> ApiInfo`: Run full pipeline

**Pipeline steps:**
1. Extract spec using ApiSpecExtractor
2. Generate API-level description (LLM prompt with endpoint summary)
3. Categorize endpoints (group by resource/domain)
4. Generate endpoint descriptions (if missing)
5. Generate example requests (curl-style)
6. Save annotated ApiInfo to cache

**Prompt templates (in prompts/openapi/annotation/):**
- api_description.md: Generate overall API description
- endpoint_description.md: Describe individual endpoint
- endpoint_categorization.md: Group endpoints into categories

## Connector Layer

**OpenApiConnector (core operations):**

```python
@context_result()
async def call_endpoint(api_id, method, path, parameters, body, output_file) -> str
    """Call API endpoint, return JSON response."""

async def list_apis() -> str
    """List all available APIs with metadata."""

@context_result()
async def list_endpoints(api_id, category=None) -> str
    """List endpoints, optionally filtered by category."""

async def show_api_summary(api_id) -> str
    """Show API summary with categorized endpoints."""

async def show_endpoint_details(api_id, method, path) -> str
    """Show detailed endpoint information."""
```

**Error handling:** Return "[Error] message" strings, never raise exceptions.

## Registry Layer

**ApiInfos (singleton):**
- Registry of all cached ApiInfo objects
- Lazy-loads cached JSON files on initialization
- Manages HTTP client instances per API
- Methods: get_api_info(), get_client(), list_api_ids(), add()

## HTTP Client Layer

**ApiHttpClient (abstract):**
- `request(method, path, params, headers, json, data) -> dict`

**RequestsApiClient:**
- Uses requests library (sync, with async wrapper)
- Retry logic with MAX_RETRIES
- Returns dict with status_code, headers, body
- No authentication handling (simplified for open APIs)

## Tool Layer

**tools/openapi.py:**

Factory function `get_all_tools()` returns list of tool functions:

```python
@tool_permission(ToolPermission.CONNECT)
async def openapi_list_apis() -> str

@tool_permission(ToolPermission.READ)
async def openapi_list_endpoints(api_id, category=None) -> str

@tool_permission(ToolPermission.READ)
async def openapi_show_api_summary(api_id) -> str

@tool_permission(ToolPermission.READ)
async def openapi_show_endpoint_details(api_id, method, path) -> str

@tool_permission(ToolPermission.CONNECT)
async def openapi_call_endpoint(api_id, method, path, parameters, body, output_file) -> str
```

## CLI Tools

**cli/ingest.py:**
```bash
python -m agentic_patterns.core.connectors.openapi.cli.ingest <api_id> [--verbose]
```

Workflow:
1. Load config from apis.yaml
2. Create ApiSpecExtractor, connect to spec_source
3. Extract ApiInfo
4. Run mandatory annotation pipeline
5. Save to cache

## Factory Functions

**factories.py:**

```python
def create_spec_parser(spec_dict, api_id) -> ApiSpecParser
    # Detect version from spec_dict["openapi"]
    # Return OpenApiV3Parser (raise error for unsupported versions)

def create_http_client(api_id) -> ApiHttpClient
    # Return RequestsApiClient with config
```

## Implementation Order

1. **Phase 1: Data Models & Configuration**
   - models.py (ApiInfo, EndpointInfo, ParameterInfo, etc.)
   - config.py (constants, paths)
   - api_connection_config.py (config models, singleton)
   - Create apis.yaml at project root

2. **Phase 2: Extraction Layer**
   - extraction/spec_parser.py (abstract base)
   - extraction/openapi_v3_parser.py (parser implementation)
   - extraction/spec_extractor.py (orchestrator)

3. **Phase 3: HTTP Client**
   - client/http_client.py (abstract)
   - client/requests_client.py (implementation)

4. **Phase 4: Registry & Connector**
   - api_infos.py (singleton registry)
   - factories.py (factory functions)
   - connector.py (core operations)

5. **Phase 5: Annotation Pipeline**
   - prompts/openapi/annotation/*.md (prompt templates)
   - annotation/annotator.py (LLM enrichment)

6. **Phase 6: Tools & CLI**
   - tools/openapi.py (tool wrappers)
   - cli/ingest.py (CLI command)

7. **Phase 7: Testing & Examples**
   - Unit tests for parser, models
   - Integration test with petstore API
   - Example notebook

## Key Patterns to Follow

1. **Singleton registries:** ApiInfos, ApiConnectionConfigs with `.get()` classmethod
2. **Error strings:** Return "[Error] message", never raise to agent
3. **@context_result():** Use on list_endpoints and call_endpoint for large results
4. **Workspace isolation:** Save large responses to /workspace/results/
5. **@tool_permission():** Decorate all tool functions (CONNECT for mutations/connections, READ for queries)
6. **Factory pattern:** Use match/case for parser creation (ready for future formats)
7. **Async operations:** All connector methods async (tool layer too)
8. **Alphabetical sorting:** Methods sorted alphabetically except underscores

## Critical Files

Files that must be created/modified:

**New files:**
- agentic_patterns/core/connectors/openapi/models.py
- agentic_patterns/core/connectors/openapi/config.py
- agentic_patterns/core/connectors/openapi/api_connection_config.py
- agentic_patterns/core/connectors/openapi/api_infos.py
- agentic_patterns/core/connectors/openapi/connector.py
- agentic_patterns/core/connectors/openapi/factories.py
- agentic_patterns/core/connectors/openapi/extraction/spec_extractor.py
- agentic_patterns/core/connectors/openapi/extraction/spec_parser.py
- agentic_patterns/core/connectors/openapi/extraction/openapi_v3_parser.py
- agentic_patterns/core/connectors/openapi/annotation/annotator.py
- agentic_patterns/core/connectors/openapi/client/http_client.py
- agentic_patterns/core/connectors/openapi/client/requests_client.py
- agentic_patterns/core/connectors/openapi/cli/ingest.py
- agentic_patterns/core/tools/openapi.py
- prompts/openapi/annotation/api_description.md
- prompts/openapi/annotation/endpoint_description.md
- prompts/openapi/annotation/endpoint_categorization.md
- apis.yaml (at project root)

**Modified files:**
- None (this is a new connector)

## Verification & Testing

**Manual verification:**

1. Create apis.yaml with petstore API:
```yaml
apis:
  petstore:
    spec_source: https://petstore3.swagger.io/api/v3/openapi.json
    base_url: https://petstore3.swagger.io/api/v3
```

2. Run ingestion:
```bash
python -m agentic_patterns.core.connectors.openapi.cli.ingest petstore --verbose
```

3. Verify cache file created:
```bash
ls -la data/api/petstore/petstore.api_info.json
```

4. Test in Python REPL:
```python
from agentic_patterns.core.connectors.openapi.connector import OpenApiConnector
from agentic_patterns.core.connectors.openapi.api_connection_config import ApiConnectionConfigs
from agentic_patterns.core.connectors.openapi.config import APIS_YAML_PATH

# Load config
ApiConnectionConfigs.get().load_from_yaml(APIS_YAML_PATH)

# Test connector
connector = OpenApiConnector()
print(await connector.list_apis())
print(await connector.list_endpoints("petstore"))
print(await connector.show_endpoint_details("petstore", "GET", "/pet/{petId}"))
```

5. Test with agent (create example notebook):
```python
from pydantic_ai import Agent
from agentic_patterns.core.tools.openapi import get_all_tools

agent = Agent("openai:gpt-4", tools=get_all_tools())
result = agent.run_sync("List all available APIs")
result = agent.run_sync("Show me the endpoints in the petstore API")
result = agent.run_sync("Get details for a specific pet endpoint")
```

**Unit tests:**
- Test ApiInfo.from_dict() / to_dict() / save() / load()
- Test OpenApiV3Parser with sample spec
- Test ApiConnectionConfigs YAML loading
- Mock HTTP responses for client tests

**Integration tests:**
- Full ingestion + annotation pipeline with petstore API
- End-to-end tool execution with agent
- Large response handling with @context_result()

## Example Usage

After implementation, agents can use the connector like this:

```python
# Setup
agent_with_openapi = Agent(
    "openai:gpt-4",
    tools=get_all_tools()
)

# List available APIs
agent.run("What APIs are available?")
# Returns: petstore API with 20 endpoints

# Explore API
agent.run("Show me the petstore API endpoints grouped by category")
# Returns: Pet Operations (5), Store Operations (4), User Operations (8), etc.

# Get endpoint details
agent.run("Show me details for creating a new pet")
# Returns: POST /pet endpoint with parameters, request schema, response codes

# Call endpoint (if API is live and accessible)
agent.run("Get pet with ID 123 from petstore")
# Returns: JSON response with pet data
```

## Dependencies

Add to pyproject.toml (if not already present):
- requests (for HTTP client)
- pyyaml (for spec parsing)
- All existing dependencies (pydantic-ai, etc.)

## Future Enhancements (Not in Initial Scope)

- Swagger 2.0 support
- Authentication (bearer, api_key, oauth2)
- Rate limiting
- Response schema validation
- Request parameter validation
- GraphQL support
- Async HTTP client (httpx)
- Endpoint mocking for testing
- OpenAPI spec generation from code

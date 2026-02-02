## Hands-On: OpenAPI Connector

The OpenAPI connector lets an agent interact with any REST API described by an OpenAPI 3.x specification. Instead of hard-coding HTTP calls or teaching the agent raw URL patterns, the connector ingests a spec once and exposes five stable operations: list available APIs, list endpoints, show an API summary, show endpoint details, and call an endpoint. The agent discovers the API surface at runtime and makes calls autonomously.

This hands-on walks through `example_openapi.ipynb`, where an agent queries the cBioPortal cancer genomics API to retrieve all available studies, then a second agent uses the JsonConnector to explore and extract information from the saved results.

## API Configuration and Ingestion

Before the connector can work, the API spec must be ingested. Configuration lives in `apis.yaml`, which declares an identifier, a human-readable name, the spec URL, and an optional `base_url` override:

```yaml
- id: cbioportal
  name: cBioPortal
  spec_url: https://www.cbioportal.org/api/v3/api-docs
  base_url: https://www.cbioportal.org
```

The ingestion CLI (`python -m agentic_patterns.core.connectors.openapi.cli.ingest cbioportal`) fetches the spec, parses all endpoints, runs AI-powered annotation to generate descriptions and categories, and caches the result as a JSON file. This is a one-time offline step. At runtime, `ApiInfos.get()` loads the cached metadata without re-fetching the spec.

## Loading API Metadata

The first code cell loads the cached API metadata and prints it to confirm the connector knows about the cBioPortal API:

```python
api_infos = ApiInfos.get()
print(api_infos)
```

`ApiInfos` is a singleton registry. It reads `apis.yaml` for connection config and loads the cached JSON files produced by the ingestion step. The `print()` output shows each registered API with its endpoint count and categories.

## The Agent with OpenAPI Tools

The five tools are created by `get_all_tools()`, which instantiates an `OpenApiConnector` and wraps each of its methods as an agent tool with appropriate permissions (`READ` for discovery operations, `CONNECT` for listing and calling):

```python
openapi_tools = get_all_tools()
agent = get_agent(tools=openapi_tools)
```

The tools are:

1. `openapi_list_apis` -- returns all registered APIs with metadata and endpoint counts.
2. `openapi_list_endpoints` -- lists endpoints for a given API, optionally filtered by category.
3. `openapi_show_api_summary` -- shows categorized endpoint overview for an API.
4. `openapi_show_endpoint_details` -- returns parameter definitions, request body schema, and response schema for a specific endpoint.
5. `openapi_call_endpoint` -- executes an HTTP request against an endpoint, with optional parameters, body, and output file path.

The agent receives no instructions about cBioPortal's URL structure, authentication, or endpoint paths. It discovers everything through the tools. This is the core difference from a generic HTTP tool: the connector provides structured discovery, so the agent can reason about what is available rather than guessing URLs.

## Running the Query

The prompt asks the agent to find all available cancer studies and save the results:

```python
query = """Using the cbioportal API, find all available cancer studies.
Save the results to /workspace/cancer_studies.json"""

result, nodes = await run_agent(agent, query, verbose=True)
```

With `verbose=True`, you can observe the agent's reasoning. It typically calls `openapi_list_apis` first to confirm the API exists, then `openapi_list_endpoints` or `openapi_show_api_summary` to find the right endpoint, then `openapi_show_endpoint_details` to understand the parameters, and finally `openapi_call_endpoint` to make the HTTP request and save the response to the specified file. The agent follows the same discovery-then-action pattern a developer would: orient, inspect, then execute.

The `call_endpoint` tool uses the `@context_result()` decorator, which means large API responses are saved to the workspace file in full while only a truncated preview is returned to the agent context. This keeps the conversation manageable even when the API returns hundreds of records.

## Chaining with the JsonConnector

The second half of the notebook demonstrates connector chaining. The OpenAPI agent produced a JSON file; now a second agent equipped with JsonConnector tools operates on it:

```python
json_connector = JsonConnector()
json_tools = [
    json_connector.append, json_connector.delete_key, json_connector.get,
    json_connector.head, json_connector.keys, json_connector.merge,
    json_connector.query, json_connector.schema, json_connector.set,
    json_connector.tail, json_connector.validate,
]

json_agent = get_agent(tools=json_tools)
```

The JsonConnector provides JSONPath-based navigation, schema inspection, head/tail previews, and key listing. The second agent has no knowledge of cBioPortal or REST APIs -- it only knows how to work with JSON files.

```python
json_query = """Using the file /workspace/cancer_studies.json:
1. Show me the schema of the file.
2. Find 3 studies related to breast cancer. Show their study ID, name, and number of samples."""
```

The agent calls `schema` to understand the structure, then `query` with a JSONPath expression to filter breast cancer studies. It works entirely from the file, with no API calls.

## Connector Layering

This example illustrates a pattern that recurs throughout the connector architecture. The OpenAPI connector handles the API interaction layer: discovery, validation, HTTP execution, response persistence. The JsonConnector handles the data inspection layer: schema discovery, querying, filtering. Neither agent knows about the other. The workspace filesystem is the integration surface -- one agent writes, another reads.

This layering reflects the chapter's core design principle: connectors expose a small number of predictable operations rather than raw access primitives. The agent never constructs URLs, parses HTTP headers, or navigates raw JSON arrays. Each connector provides the right level of abstraction for its data source, and the agent reasons at that level.

## Key Takeaways

The OpenAPI connector turns API specifications into discoverable, callable tool surfaces. Ingestion happens once offline; at runtime the agent discovers endpoints, inspects parameters, and makes validated calls without any hard-coded API knowledge. Large responses are persisted to the workspace and truncated in context, keeping the agent loop efficient. Connector chaining through the workspace filesystem lets specialized agents collaborate on different aspects of the same data without coupling.

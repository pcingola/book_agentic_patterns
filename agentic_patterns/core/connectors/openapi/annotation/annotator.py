"""API specification annotation pipeline -- AI-powered enrichment."""

import json
import re

from agentic_patterns.core.agents.agents import get_agent, run_agent
from agentic_patterns.core.connectors.openapi.extraction.spec_extractor import ApiSpecExtractor
from agentic_patterns.core.connectors.openapi.models import ApiInfo
from agentic_patterns.core.prompt import get_prompt


class ApiSpecAnnotator:
    """Orchestrates AI-powered API spec annotation: descriptions, categorization, examples."""

    def __init__(self, api_id: str):
        self.api_id = api_id

    async def annotate(self, spec_source: str, base_url: str | None = None, verbose: bool = False, debug: bool = False) -> ApiInfo:
        """Run the full annotation pipeline.

        Args:
            spec_source: URL or file path to OpenAPI spec
            base_url: Optional base URL to override spec's servers section
            verbose: Enable informative progress output
            debug: Enable debug output (agent steps)
        """
        self._verbose = verbose
        self._debug = debug

        # Extract base API info
        print(f"Fetching and parsing OpenAPI spec from {spec_source}...")
        with ApiSpecExtractor(self.api_id, base_url) as extractor:
            extractor.connect(spec_source)
            api_info = extractor.api_info(cache=False)

        # Run annotation steps
        print(f"Extracted {len(api_info.endpoints)} endpoints from spec")
        print("Step 1/4: Generating API description...")
        await self._annotate_api_description(api_info)
        print("Step 2/4: Categorizing endpoints...")
        await self._categorize_endpoints(api_info)
        print("Step 3/4: Generating endpoint descriptions...")
        await self._annotate_endpoint_descriptions(api_info)
        print("Step 4/4: Generating example requests...")
        await self._generate_example_requests(api_info)

        # Save annotated API info
        api_info.save()
        print(f"Annotation complete for {self.api_id}")
        return api_info

    async def _annotate_api_description(self, api_info: ApiInfo) -> None:
        """Generate API-level description using LLM."""
        if self._verbose:
            print(f"  Generating API description for {api_info.api_id}")

        # Build endpoints summary
        endpoints_summary = []
        for endpoint in api_info.endpoints:
            endpoints_summary.append(f"- {endpoint.method} {endpoint.path}: {endpoint.summary or 'No summary'}")

        prompt = get_prompt(
            "openapi/annotation/api_description",
            title=api_info.title,
            version=api_info.version,
            base_url=api_info.base_url,
            endpoints_summary="\n".join(endpoints_summary),
        )

        agent = get_agent(system_prompt="You are an API documentation expert.")
        result, _ = await run_agent(agent, prompt, verbose=self._debug)

        if result:
            api_info.description = result.result.output.strip()

    async def _categorize_endpoints(self, api_info: ApiInfo) -> None:
        """Categorize endpoints into logical groups using LLM."""
        if self._verbose:
            print(f"  Categorizing {len(api_info.endpoints)} endpoints for {api_info.api_id}")

        # Build endpoints list for categorization
        endpoints_list = []
        for endpoint in api_info.endpoints:
            endpoints_list.append(
                {
                    "operation_id": endpoint.operation_id,
                    "method": endpoint.method,
                    "path": endpoint.path,
                    "summary": endpoint.summary,
                    "tags": endpoint.tags,
                }
            )

        prompt = get_prompt(
            "openapi/annotation/endpoint_categorization",
            endpoints_list=json.dumps(endpoints_list, indent=2),
        )

        agent = get_agent(system_prompt="You are an API documentation expert.")
        result, _ = await run_agent(agent, prompt, verbose=self._debug)

        if result:
            try:
                # Parse JSON response -- extract JSON from markdown code blocks or raw text
                output = result.result.output.strip()
                json_match = re.search(r"```(?:json)?\s*\n(.*?)```", output, re.DOTALL)
                if json_match:
                    output = json_match.group(1).strip()

                categorization = json.loads(output)

                # Apply categories to endpoints
                for endpoint in api_info.endpoints:
                    if endpoint.operation_id in categorization:
                        endpoint.category = categorization[endpoint.operation_id]
                    else:
                        endpoint.category = "Uncategorized"

            except json.JSONDecodeError as e:
                print(f"WARNING: Failed to parse categorization JSON: {e}")
                # Fallback: use tags or set to Uncategorized
                for endpoint in api_info.endpoints:
                    endpoint.category = endpoint.tags[0] if endpoint.tags else "Uncategorized"

    async def _annotate_endpoint_descriptions(self, api_info: ApiInfo) -> None:
        """Generate endpoint descriptions for endpoints missing them."""
        endpoints_to_describe = [e for e in api_info.endpoints if not e.description]
        total = len(endpoints_to_describe)
        print(f"  {total} endpoints need descriptions ({len(api_info.endpoints) - total} already have one)")

        for i, endpoint in enumerate(endpoints_to_describe, 1):

            # Build parameters summary
            params_lines = []
            for param in endpoint.parameters:
                required_str = " (required)" if param.required else ""
                params_lines.append(f"- {param.name} ({param.location}, {param.schema_type}){required_str}: {param.description}")

            # Build request body summary
            request_body_str = "None"
            if endpoint.request_body:
                request_body_str = f"{endpoint.request_body.content_type}: {endpoint.request_body.description}"

            # Build responses summary
            responses_lines = []
            for response in endpoint.responses:
                responses_lines.append(f"- {response.status_code}: {response.description}")

            if self._verbose:
                print(f"  [{i}/{total}] {endpoint.method} {endpoint.path}")

            prompt = get_prompt(
                "openapi/annotation/endpoint_description",
                method=endpoint.method,
                path=endpoint.path,
                operation_id=endpoint.operation_id,
                summary=endpoint.summary or "No summary",
                parameters="\n".join(params_lines) if params_lines else "None",
                request_body=request_body_str,
                responses="\n".join(responses_lines) if responses_lines else "None",
            )

            agent = get_agent(system_prompt="You are an API documentation expert.")
            result, _ = await run_agent(agent, prompt, verbose=self._debug)

            if result:
                endpoint.description = result.result.output.strip()

    async def _generate_example_requests(self, api_info: ApiInfo) -> None:
        """Generate example curl requests for endpoints."""
        total = len(api_info.endpoints)
        for i, endpoint in enumerate(api_info.endpoints, 1):
            if self._verbose:
                print(f"  [{i}/{total}] {endpoint.method} {endpoint.path}")
            # Build basic curl command
            url = f"{api_info.base_url}{endpoint.path}"

            # Replace path parameters with example values
            for param in endpoint.parameters:
                if param.location == "path":
                    example_value = param.example or "{value}"
                    url = url.replace(f"{{{param.name}}}", str(example_value))

            curl_parts = [f"curl -X {endpoint.method}"]

            # Add query parameters
            query_params = [p for p in endpoint.parameters if p.location == "query"]
            if query_params:
                query_parts = []
                for param in query_params[:3]:  # Limit to first 3 for brevity
                    example_value = param.example or "value"
                    query_parts.append(f"{param.name}={example_value}")
                url += "?" + "&".join(query_parts)

            curl_parts.append(f'"{url}"')

            # Add headers
            header_params = [p for p in endpoint.parameters if p.location == "header"]
            for param in header_params:
                example_value = param.example or "value"
                curl_parts.append(f'-H "{param.name}: {example_value}"')

            # Add request body
            if endpoint.request_body:
                if endpoint.request_body.content_type == "application/json":
                    curl_parts.append('-H "Content-Type: application/json"')
                    body_example = endpoint.request_body.example or '{"key": "value"}'
                    curl_parts.append(f"-d '{body_example}'")

            endpoint.example_request = " \\\n  ".join(curl_parts)

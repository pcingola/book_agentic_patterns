"""Template MCP client demonstrating get_mcp_client() with error handling.

Connects to the template server, exercises tools, and shows how retryable
vs fatal errors behave. Requires the template server running:

    fastmcp run agentic_patterns/examples/mcp/template/server.py:mcp

The client uses get_mcp_client() which returns MCPServerStreamableHTTPStrict
(or MCPClientPrivateData when url_isolated is configured). Fatal tool errors
abort the run immediately instead of being retried.
"""

import asyncio

from agentic_patterns.core.agents import get_agent, run_agent
from agentic_patterns.core.mcp import get_mcp_client


async def main() -> None:
    server = get_mcp_client("template")

    agent = get_agent(toolsets=[server])

    async with agent:
        # Normal tool call: read a file
        print("--- read_file ---")
        result, _ = await run_agent(agent, "Read the file at /workspace/hello.txt", verbose=True)
        print(f"Result: {result.result.output}\n")

        # Retryable error: empty query (LLM can retry with a proper query)
        print("--- search_records (retryable error) ---")
        result, _ = await run_agent(agent, "Search for records about 'customers'", verbose=True)
        print(f"Result: {result.result.output}\n")

        # Private data flagging: loads sensitive dataset
        print("--- load_sensitive_dataset ---")
        result, _ = await run_agent(agent, "Load the 'patient_records' sensitive dataset", verbose=True)
        print(f"Result: {result.result.output}\n")


if __name__ == "__main__":
    asyncio.run(main())

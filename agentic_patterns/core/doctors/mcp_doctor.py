"""MCP doctor: Analyze tools from MCP servers and provide recommendations."""

from pydantic_ai.mcp import MCPServerStdio, MCPServerStreamableHTTP

from agentic_patterns.core.agents import get_agent, run_agent
from agentic_patterns.core.doctors.base import DoctorBase
from agentic_patterns.core.doctors.models import ToolRecommendation
from agentic_patterns.core.prompt import load_prompt


class MCPDoctor(DoctorBase):
    """Analyzes tools from MCP servers for clarity and completeness."""

    def __init__(self, mcp_server: MCPServerStreamableHTTP | MCPServerStdio):
        self.mcp_server = mcp_server

    async def _analyze_batch_internal(
        self, batch: list, verbose: bool = False
    ) -> list[ToolRecommendation]:
        """Analyze tools from the MCP server. Batch parameter is ignored as we analyze all tools."""
        prompt = load_prompt(
            "doctors/tool_doctor",
            tools_description="(tools provided via MCP)",
        )

        agent = get_agent(
            toolsets=[self.mcp_server], output_type=list[ToolRecommendation]
        )
        async with agent:
            agent_run, _ = await run_agent(agent, prompt, verbose=verbose)
        return agent_run.result.output if agent_run else []

    async def analyze_all(self, verbose: bool = False) -> list[ToolRecommendation]:
        """Analyze all tools from the MCP server."""
        return await self._analyze_batch_internal([], verbose=verbose)


async def mcp_doctor(
    server: MCPServerStreamableHTTP | MCPServerStdio | str,
    verbose: bool = False,
) -> list[ToolRecommendation]:
    """Analyze tools from an MCP server and provide recommendations.

    Args:
        server: MCP server instance or URL string for HTTP server.
        verbose: Enable verbose output.

    Returns:
        List of recommendations for each tool.
    """
    if isinstance(server, str):
        server = MCPServerStreamableHTTP(url=server)

    doctor = MCPDoctor(server)
    return await doctor.analyze_all(verbose=verbose)

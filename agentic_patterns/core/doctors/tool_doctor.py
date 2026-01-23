"""Tool doctor: Analyze tool definitions and provide recommendations."""

from typing import Callable

from agentic_patterns.core.agents import get_agent, run_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.doctors.base import DoctorBase
from agentic_patterns.core.doctors.models import ToolRecommendation
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.core.tools import func_to_description


class ToolDoctor(DoctorBase):
    """Analyzes tool function definitions for clarity and completeness."""

    async def analyze(self, tool: Callable, verbose: bool = False) -> ToolRecommendation:
        """Analyze a single tool function."""
        results = await self._analyze_batch_internal([tool], verbose=verbose)
        return results[0]

    async def _analyze_batch_internal(self, batch: list[Callable], verbose: bool = False) -> list[ToolRecommendation]:
        """Analyze a batch of tool functions."""
        tools_description = "\n\n".join(func_to_description(tool) for tool in batch)
        prompt = load_prompt(PROMPTS_DIR / "doctors" / "tool_doctor.md", tools_description=tools_description)

        agent = get_agent(tools=batch, output_type=list[ToolRecommendation])
        agent_run, _ = await run_agent(agent, prompt, verbose=verbose)
        return agent_run.result.output if agent_run else []


async def tool_doctor(
    tools: list[Callable],
    batch_size: int = 5,
    verbose: bool = False,
) -> list[ToolRecommendation]:
    """Analyze tools and provide recommendations for improvement.

    Args:
        tools: List of tool functions to analyze.
        batch_size: Number of tools to analyze per batch.
        verbose: Enable verbose output.

    Returns:
        List of recommendations for each tool.
    """
    doctor = ToolDoctor()
    return await doctor.analyze_batch(tools, batch_size=batch_size, verbose=verbose)

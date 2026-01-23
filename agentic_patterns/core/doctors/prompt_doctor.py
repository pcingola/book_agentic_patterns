"""Prompt doctor: Analyze prompts and provide recommendations."""

import re
from pathlib import Path

from agentic_patterns.core.agents import get_agent, run_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.doctors.base import DoctorBase
from agentic_patterns.core.doctors.models import PromptRecommendation
from agentic_patterns.core.prompt import load_prompt


def _extract_placeholders(content: str) -> list[str]:
    """Extract placeholder names from a prompt template."""
    return list(set(re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", content)))


def _format_prompt_for_analysis(name: str, content: str) -> str:
    """Format a prompt for analysis."""
    placeholders = _extract_placeholders(content)
    placeholders_str = ", ".join(placeholders) if placeholders else "(none)"
    return f"### Prompt: {name}\nPlaceholders: {placeholders_str}\n\n{content}"


class PromptDoctor(DoctorBase):
    """Analyzes prompts for clarity and completeness."""

    async def analyze(self, prompt: str | Path, verbose: bool = False) -> PromptRecommendation:
        """Analyze a single prompt."""
        results = await self._analyze_batch_internal([prompt], verbose=verbose)
        return results[0]

    async def _analyze_batch_internal(self, batch: list[str | Path], verbose: bool = False) -> list[PromptRecommendation]:
        """Analyze a batch of prompts."""
        prompts_content = []
        for item in batch:
            if isinstance(item, Path):
                name = item.name
                content = item.read_text(encoding="utf-8")
            else:
                name = f"prompt_{len(prompts_content) + 1}"
                content = item
            prompts_content.append(_format_prompt_for_analysis(name, content))

        analysis_prompt = load_prompt(
            PROMPTS_DIR / "doctors" / "prompt_doctor.md",
            prompts_content="\n\n---\n\n".join(prompts_content),
        )

        agent = get_agent(output_type=list[PromptRecommendation])
        agent_run, _ = await run_agent(agent, analysis_prompt, verbose=verbose)
        return agent_run.result.output if agent_run else []


async def prompt_doctor(
    prompts: list[str | Path],
    batch_size: int = 5,
    verbose: bool = False,
) -> list[PromptRecommendation]:
    """Analyze prompts and provide recommendations for improvement.

    Args:
        prompts: List of prompts (strings or file paths) to analyze.
        batch_size: Number of prompts to analyze per batch.
        verbose: Enable verbose output.

    Returns:
        List of recommendations for each prompt.
    """
    doctor = PromptDoctor()
    return await doctor.analyze_batch(prompts, batch_size=batch_size, verbose=verbose)

"""A2A doctor: Analyze agent-to-agent cards and provide recommendations."""

import json

import httpx
from pydantic import BaseModel

from agentic_patterns.core.agents import get_agent, run_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.doctors.base import DoctorBase
from agentic_patterns.core.doctors.models import A2ARecommendation
from agentic_patterns.core.prompt import load_prompt


class AgentCard(BaseModel):
    """Minimal representation of an A2A agent card."""
    name: str
    description: str | None = None
    capabilities: list[str] | None = None
    skills: list[dict] | None = None
    url: str | None = None


async def fetch_agent_card(url: str) -> AgentCard:
    """Fetch an agent card from a URL."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        return AgentCard(
            name=data.get("name", "unknown"),
            description=data.get("description"),
            capabilities=data.get("capabilities"),
            skills=data.get("skills"),
            url=url,
        )


def _format_agent_card(card: AgentCard) -> str:
    """Format an agent card for analysis."""
    lines = [f"### Agent: {card.name}"]
    if card.url:
        lines.append(f"URL: {card.url}")
    if card.description:
        lines.append(f"Description: {card.description}")
    if card.capabilities:
        lines.append(f"Capabilities: {', '.join(card.capabilities)}")
    if card.skills:
        lines.append("Skills:")
        for skill in card.skills:
            lines.append(f"  - {json.dumps(skill)}")
    return "\n".join(lines)


class A2ADoctor(DoctorBase):
    """Analyzes A2A agent cards for clarity and completeness."""

    async def analyze(self, agent: str | AgentCard, verbose: bool = False) -> A2ARecommendation:
        """Analyze a single agent card."""
        results = await self._analyze_batch_internal([agent], verbose=verbose)
        return results[0]

    async def _analyze_batch_internal(self, batch: list[str | AgentCard], verbose: bool = False) -> list[A2ARecommendation]:
        """Analyze a batch of agent cards."""
        cards = []
        for item in batch:
            if isinstance(item, str):
                card = await fetch_agent_card(item)
            else:
                card = item
            cards.append(card)

        agent_cards_content = "\n\n---\n\n".join(_format_agent_card(card) for card in cards)
        analysis_prompt = load_prompt(
            PROMPTS_DIR / "doctors" / "a2a_doctor.md",
            agent_cards=agent_cards_content,
        )

        agent = get_agent(output_type=list[A2ARecommendation])
        agent_run, _ = await run_agent(agent, analysis_prompt, verbose=verbose)
        return agent_run.result.output if agent_run else []


async def a2a_doctor(
    agents: list[str | AgentCard],
    batch_size: int = 5,
    verbose: bool = False,
) -> list[A2ARecommendation]:
    """Analyze A2A agent cards and provide recommendations for improvement.

    Args:
        agents: List of agent card URLs or AgentCard objects to analyze.
        batch_size: Number of agents to analyze per batch.
        verbose: Enable verbose output.

    Returns:
        List of recommendations for each agent.
    """
    doctor = A2ADoctor()
    return await doctor.analyze_batch(agents, batch_size=batch_size, verbose=verbose)

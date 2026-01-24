"""A2A doctor: Analyze agent-to-agent cards and provide recommendations."""

import json

import httpx
from fasta2a.schema import AgentCard

from agentic_patterns.core.agents import get_agent, run_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.doctors.base import DoctorBase
from agentic_patterns.core.doctors.models import A2ARecommendation
from agentic_patterns.core.prompt import load_prompt

# Required top-level fields in an A2A agent card per the protocol spec.
AGENT_CARD_REQUIRED_FIELDS = ["name", "description", "url", "version", "skills"]


def validate_agent_card(data: dict) -> AgentCard:
    """Validate that the response contains a valid A2A agent card.

    We use basic validation instead of fasta2a's agent_card_ta.validate_python() because
    the fasta2a library incorrectly marks Skill.inputModes and Skill.outputModes as required
    fields, when the A2A protocol spec defines them as optional (skills inherit from the
    agent-level defaultInputModes/defaultOutputModes when not specified). This causes
    validation to fail on valid agent cards that follow the protocol correctly.
    """
    missing = [f for f in AGENT_CARD_REQUIRED_FIELDS if f not in data]
    if missing:
        raise ValueError(f"Invalid agent card: missing required fields: {missing}")
    return data  # type: ignore[return-value]


async def fetch_agent_card(base_url: str, verbose: bool = False) -> AgentCard:
    """Fetch an agent card from an A2A server base URL."""
    url = base_url.rstrip("/") + "/.well-known/agent-card.json"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        if verbose:
            print(f"Agent card: {json.dumps(data, indent=2)}")
        return validate_agent_card(data)


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
                card = await fetch_agent_card(item, verbose=verbose)
            else:
                card = item
                if verbose:
                    print(f"Agent card: {json.dumps(card, indent=2)}")
            cards.append(card)

        agent_cards_content = "\n\n---\n\n".join(json.dumps(card, indent=2) for card in cards)
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

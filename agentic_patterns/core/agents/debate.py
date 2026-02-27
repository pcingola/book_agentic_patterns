"""Structured debate orchestrator: advocate vs. critic with arbiter verdicts."""

from pydantic import BaseModel

from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt


class Argument(BaseModel):
    """A single argument with claim, evidence, and rebuttals."""

    claim: str
    evidence: str
    rebuttals: list[str] = []


class DebateTurn(BaseModel):
    """One side's contribution in a round."""

    position: str
    arguments: list[Argument]


class Verdict(BaseModel):
    """Arbiter's decision after evaluating the debate."""

    decision: str
    reasoning: str
    accepted_claims: list[str]
    rejected_claims: list[str]
    open_questions: list[str]
    is_sufficient: bool


class DebateRound(BaseModel):
    """A single round containing advocate and critic turns."""

    advocate: DebateTurn
    critic: DebateTurn


class DebateResult(BaseModel):
    """Full debate output: rounds played and final verdict."""

    proposal: str
    rounds: list[DebateRound]
    verdict: Verdict


def _format_turn(role: str, turn: DebateTurn) -> str:
    lines = [f"### {role}"]
    for arg in turn.arguments:
        lines.append(f"- **{arg.claim}**: {arg.evidence}")
        for r in arg.rebuttals:
            lines.append(f"  - Rebuttal: {r}")
    return "\n".join(lines)


def _format_round(i: int, rnd: DebateRound) -> str:
    return f"## Round {i + 1}\n\n{_format_turn('Advocate', rnd.advocate)}\n\n{_format_turn('Critic', rnd.critic)}"


class DebateOrchestrator:
    """Runs a multi-round advocate-vs-critic debate with arbiter verdicts.

    Persona simulation is achieved by passing role descriptions as
    advocate_prompt / critic_prompt (e.g. "You are a senior security engineer...").
    """

    def __init__(
        self,
        *,
        advocate_prompt: str = "",
        critic_prompt: str = "",
        config_name: str = "default",
        max_rounds: int = 2,
    ):
        self._advocate_prompt = advocate_prompt
        self._critic_prompt = critic_prompt
        self._max_rounds = max_rounds
        self._advocate = get_agent(config_name=config_name, output_type=DebateTurn)
        self._critic = get_agent(config_name=config_name, output_type=DebateTurn)
        self._arbiter = get_agent(config_name=config_name, output_type=Verdict)

    async def run(self, proposal: str) -> DebateResult:
        rounds: list[DebateRound] = []
        transcript = "(no prior rounds)"
        verdict: Verdict | None = None

        for i in range(self._max_rounds):
            # Advocate turn
            adv_prompt = load_prompt(
                PROMPTS_DIR / "adversarial" / "advocate_turn.md",
                proposal=proposal,
                transcript=transcript,
                additional_instructions=self._advocate_prompt,
            )
            adv_result = await self._advocate.run(adv_prompt)
            adv_turn = adv_result.output

            # Critic turn
            pro_text = _format_turn("Advocate", adv_turn)
            crit_prompt = load_prompt(
                PROMPTS_DIR / "adversarial" / "critic_turn.md",
                proposal=proposal,
                transcript=transcript,
                pro_arguments=pro_text,
                additional_instructions=self._critic_prompt,
            )
            crit_result = await self._critic.run(crit_prompt)
            crit_turn = crit_result.output

            rnd = DebateRound(advocate=adv_turn, critic=crit_turn)
            rounds.append(rnd)

            # Update transcript for next round
            transcript = "\n\n".join(_format_round(j, r) for j, r in enumerate(rounds))

            # Arbiter verdict
            arb_prompt = load_prompt(
                PROMPTS_DIR / "adversarial" / "arbiter_verdict.md",
                proposal=proposal,
                transcript=transcript,
            )
            arb_result = await self._arbiter.run(arb_prompt)
            verdict = arb_result.output

            if verdict.is_sufficient:
                break

        return DebateResult(proposal=proposal, rounds=rounds, verdict=verdict)

    def __str__(self) -> str:
        return f"DebateOrchestrator(max_rounds={self._max_rounds})"

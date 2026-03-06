from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.agents.debate.listener import DebateListener
from agentic_patterns.agents.debate.models import (
    DebateResult,
    DebateRound,
    DebateTurn,
    Verdict,
)
from agentic_patterns.core.prompt import load_prompt


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
    Pass a DebateListener to receive structured callbacks after each step.
    """

    def __init__(
        self,
        *,
        advocate_prompt: str = "",
        critic_prompt: str = "",
        config_name: str = "default",
        max_rounds: int = 2,
        listener: DebateListener | None = None,
    ):
        self._advocate_prompt = advocate_prompt
        self._critic_prompt = critic_prompt
        self._max_rounds = max_rounds
        self._listener = listener
        self._advocate = get_agent(config_name=config_name, output_type=DebateTurn)
        self._critic = get_agent(config_name=config_name, output_type=DebateTurn)
        self._arbiter = get_agent(config_name=config_name, output_type=Verdict)

    async def _advocate_turn(
        self, proposal: str, transcript: str, round_num: int
    ) -> DebateTurn:
        if self._listener:
            await self._listener.on_advocate_start(round_num, self._max_rounds)
        prompt = load_prompt(
            "adversarial/advocate_turn",
            proposal=proposal,
            transcript=transcript,
            additional_instructions=self._advocate_prompt,
        )
        turn = (await self._advocate.run(prompt)).output
        if self._listener:
            await self._listener.on_advocate(round_num, self._max_rounds, turn)
        return turn

    async def _critic_turn(
        self, proposal: str, transcript: str, adv_turn: DebateTurn, round_num: int
    ) -> DebateTurn:
        if self._listener:
            await self._listener.on_critic_start(round_num, self._max_rounds)
        prompt = load_prompt(
            "adversarial/critic_turn",
            proposal=proposal,
            transcript=transcript,
            pro_arguments=_format_turn("Advocate", adv_turn),
            additional_instructions=self._critic_prompt,
        )
        turn = (await self._critic.run(prompt)).output
        if self._listener:
            await self._listener.on_critic(round_num, self._max_rounds, turn)
        return turn

    async def _arbiter_verdict(
        self, proposal: str, transcript: str, round_num: int
    ) -> Verdict:
        if self._listener:
            await self._listener.on_verdict_start(round_num, self._max_rounds)
        prompt = load_prompt(
            "adversarial/arbiter_verdict",
            proposal=proposal,
            transcript=transcript,
        )
        verdict = (await self._arbiter.run(prompt)).output
        if self._listener:
            await self._listener.on_verdict(round_num, self._max_rounds, verdict)
        return verdict

    async def run(self, proposal: str) -> DebateResult:
        if self._listener:
            await self._listener.on_start()
        rounds: list[DebateRound] = []
        transcript = "(no prior rounds)"
        verdict: Verdict | None = None

        for i in range(self._max_rounds):
            adv_turn = await self._advocate_turn(proposal, transcript, i + 1)
            crit_turn = await self._critic_turn(proposal, transcript, adv_turn, i + 1)
            rnd = DebateRound(advocate=adv_turn, critic=crit_turn)
            rounds.append(rnd)
            transcript = "\n\n".join(_format_round(j, r) for j, r in enumerate(rounds))
            verdict = await self._arbiter_verdict(proposal, transcript, i + 1)
            if verdict.is_sufficient:
                break

        result = DebateResult(proposal=proposal, rounds=rounds, verdict=verdict)
        if self._listener:
            await self._listener.on_done(result)
        return result

    def __str__(self) -> str:
        return f"DebateOrchestrator(max_rounds={self._max_rounds})"

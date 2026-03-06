"""Red-team analysis agent for generating structured challenges against a result."""

from pydantic import BaseModel

from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.core.listeners import AgentListener
from agentic_patterns.core.prompt import load_prompt


class Challenge(BaseModel):
    """A single red-team challenge."""

    claim: str
    attack: str
    severity: str
    required_evidence: str


class RedTeamResult(BaseModel):
    """Ranked list of challenges with summary."""

    challenges: list[Challenge]
    summary: str


class RedTeamListener(AgentListener[RedTeamResult]):
    """Hooks called before and after red-team analysis. Override to customise behaviour."""


class PrintRedTeamListener(RedTeamListener):
    """Prints progress and a summary of challenges to stdout."""

    async def on_start(self) -> None:
        print("Red-teaming...")

    async def on_done(self, result: RedTeamResult) -> None:
        print(f"Summary: {result.summary}")
        for ch in result.challenges:
            print(f"  [{ch.severity}] {ch.claim}")


class RedTeamAgent:
    """Generates adversarial challenges against a result, guided by a threat model."""

    def __init__(
        self,
        threat_model: str,
        *,
        config_name: str = "default",
        listener: RedTeamListener | None = None,
    ):
        self._threat_model = threat_model
        self._listener = listener
        self._agent = get_agent(config_name=config_name, output_type=RedTeamResult)

    async def analyze(self, result: str, context: str = "") -> RedTeamResult:
        if self._listener:
            await self._listener.on_start()
        prompt = load_prompt(
            "adversarial/red_team",
            threat_model=self._threat_model,
            result=result,
            context=context,
        )
        rt_result = (await self._agent.run(prompt)).output
        if self._listener:
            await self._listener.on_done(rt_result)
        return rt_result

    def __str__(self) -> str:
        return f"RedTeamAgent(threat_model={self._threat_model!r})"

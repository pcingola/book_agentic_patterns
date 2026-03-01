"""Red-team analysis agent for generating structured challenges against a result."""

from collections.abc import Callable

from pydantic import BaseModel

from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
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


class RedTeamAgent:
    """Generates adversarial challenges against a result, guided by a threat model."""

    def __init__(
        self,
        threat_model: str,
        *,
        config_name: str = "default",
        on_start: Callable[[], None] | None = None,
    ):
        self._threat_model = threat_model
        self._on_start = on_start
        self._agent = get_agent(config_name=config_name, output_type=RedTeamResult)

    async def analyze(self, result: str, context: str = "") -> RedTeamResult:
        if self._on_start:
            self._on_start()
        prompt = load_prompt(
            PROMPTS_DIR / "adversarial" / "red_team.md",
            threat_model=self._threat_model,
            result=result,
            context=context,
        )
        run = await self._agent.run(prompt)
        return run.output

    def __str__(self) -> str:
        return f"RedTeamAgent(threat_model={self._threat_model!r})"

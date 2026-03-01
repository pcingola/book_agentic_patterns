from pydantic import BaseModel


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

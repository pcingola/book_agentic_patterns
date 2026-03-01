from agentic_patterns.agents.debate.models import DebateResult, DebateTurn, Verdict
from agentic_patterns.core.listeners import AgentListener


class DebateListener(AgentListener[DebateResult]):
    """Hooks called before and after each step of the debate. Override to customise behaviour."""

    async def on_advocate_start(self, round_num: int, total: int) -> None:
        pass

    async def on_advocate(self, round_num: int, total: int, turn: DebateTurn) -> None:
        pass

    async def on_critic_start(self, round_num: int, total: int) -> None:
        pass

    async def on_critic(self, round_num: int, total: int, turn: DebateTurn) -> None:
        pass

    async def on_verdict_start(self, round_num: int, total: int) -> None:
        pass

    async def on_verdict(self, round_num: int, total: int, verdict: Verdict) -> None:
        pass


class PrintDebateListener(DebateListener):
    """Prints each step's content to stdout as it completes."""

    async def on_start(self) -> None:
        print("Starting debate...")

    async def on_advocate_start(self, round_num: int, total: int) -> None:
        print(f"\n--- Round {round_num}/{total} ---")
        print("Advocate thinking...")

    async def on_advocate(self, round_num: int, total: int, turn: DebateTurn) -> None:
        print(f"Advocate ({turn.position}):")
        for arg in turn.arguments:
            print(f"  - {arg.claim}")
            print(f"    Evidence: {arg.evidence}")
            for r in arg.rebuttals:
                print(f"    Rebuttal: {r}")

    async def on_critic_start(self, round_num: int, total: int) -> None:
        print("Critic thinking...")

    async def on_critic(self, round_num: int, total: int, turn: DebateTurn) -> None:
        print(f"Critic ({turn.position}):")
        for arg in turn.arguments:
            print(f"  - {arg.claim}")
            print(f"    Evidence: {arg.evidence}")
            for r in arg.rebuttals:
                print(f"    Rebuttal: {r}")

    async def on_verdict_start(self, round_num: int, total: int) -> None:
        print("Arbiter deciding...")

    async def on_verdict(self, round_num: int, total: int, verdict: Verdict) -> None:
        print(f"Verdict: {verdict.decision}")

    async def on_done(self, result: DebateResult) -> None:
        print(f"Debate complete. Final verdict: {result.verdict.decision}")

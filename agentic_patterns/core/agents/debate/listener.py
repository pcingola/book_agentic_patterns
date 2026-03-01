from agentic_patterns.core.agents.debate.models import DebateTurn, Verdict


class DebateListener:
    """Hooks called before and after each step of the debate. Override to customise behaviour."""

    def on_advocate_start(self, round_num: int, total: int) -> None:
        pass

    def on_advocate(self, round_num: int, total: int, turn: DebateTurn) -> None:
        pass

    def on_critic_start(self, round_num: int, total: int) -> None:
        pass

    def on_critic(self, round_num: int, total: int, turn: DebateTurn) -> None:
        pass

    def on_verdict_start(self, round_num: int, total: int) -> None:
        pass

    def on_verdict(self, round_num: int, total: int, verdict: Verdict) -> None:
        pass


class PrintDebateListener(DebateListener):
    """Prints each step's content to stdout as it completes."""

    def on_advocate_start(self, round_num: int, total: int) -> None:
        print(f"\n--- Round {round_num}/{total} ---")
        print("Advocate thinking...")

    def on_advocate(self, round_num: int, total: int, turn: DebateTurn) -> None:
        print(f"Advocate ({turn.position}):")
        for arg in turn.arguments:
            print(f"  - {arg.claim}")
            print(f"    Evidence: {arg.evidence}")
            for r in arg.rebuttals:
                print(f"    Rebuttal: {r}")

    def on_critic_start(self, round_num: int, total: int) -> None:
        print("Critic thinking...")

    def on_critic(self, round_num: int, total: int, turn: DebateTurn) -> None:
        print(f"Critic ({turn.position}):")
        for arg in turn.arguments:
            print(f"  - {arg.claim}")
            print(f"    Evidence: {arg.evidence}")
            for r in arg.rebuttals:
                print(f"    Rebuttal: {r}")

    def on_verdict_start(self, round_num: int, total: int) -> None:
        print("Arbiter deciding...")

    def on_verdict(self, round_num: int, total: int, verdict: Verdict) -> None:
        print(f"Verdict: {verdict.decision}")

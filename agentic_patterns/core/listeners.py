"""Common listener base classes for agents and pipelines.

AgentListener[T] is the single unified base for all agent runs, covering lifecycle,
tool calls, skills, sub-agent delegation, context compaction, and iterative progress.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

import rich

if TYPE_CHECKING:
    from agentic_patterns.core.context.history import CompactionResult

T = TypeVar("T")


class AgentListener(Generic[T]):
    """Hooks for any agent run. All methods are async no-ops; override to customise."""

    async def on_start(self) -> None:
        pass

    async def on_done(self, result: T) -> None:
        pass

    async def on_text(self, text: str) -> None:
        pass

    async def on_tool_call(self, name: str, args: dict) -> None:
        pass

    async def on_tool_result(self, name: str, result: str) -> None:
        pass

    async def on_skill_call(self, name: str) -> None:
        pass

    async def on_agent_launch(self, name: str) -> None:
        pass

    async def on_agent_done(self, result: str) -> None:
        pass

    async def on_compaction(self, result: CompactionResult) -> None:
        pass

    async def on_item_start(self, item: Any, total: int) -> None:
        pass

    async def on_item_done(self, item: Any, result: Any, done: int, total: int) -> None:
        pass


class PrintAgentListener(AgentListener[T]):
    """Prints all agent events to stdout using rich."""

    async def on_start(self) -> None:
        rich.print("[bold]Starting...[/bold]")

    async def on_done(self, result: T) -> None:
        rich.print("[bold green]Done.[/bold green]")

    async def on_text(self, text: str) -> None:
        rich.print(f"  [dim]> {text.replace(chr(10), ' ')[:120]}[/dim]")

    async def on_tool_call(self, name: str, args: dict) -> None:
        params = " ".join(f"{k}={v}" for k, v in args.items())
        rich.print(f"  [green]{name}[/green] {params[:100]}")

    async def on_tool_result(self, name: str, result: str) -> None:
        rich.print(f"  [dim]  <- {name}: {result.replace(chr(10), ' ')[:120]}[/dim]")

    async def on_skill_call(self, name: str) -> None:
        rich.print(f"  [cyan]skill:[/cyan] {name}")

    async def on_agent_launch(self, name: str) -> None:
        rich.print(f"  [blue]agent launch:[/blue] {name}")

    async def on_agent_done(self, result: str) -> None:
        rich.print(f"  [blue]agent done:[/blue] {result.replace(chr(10), ' ')[:500]}")

    async def on_compaction(self, result: CompactionResult) -> None:
        rich.print(
            f"  [yellow]compaction:[/yellow] {result.original_messages} -> {result.compacted_messages} messages, "
            f"{result.original_tokens} -> {result.compacted_tokens} tokens"
        )

    async def on_item_done(self, item: Any, result: Any, done: int, total: int) -> None:
        rich.print(f"  [{done}/{total}] {result}")

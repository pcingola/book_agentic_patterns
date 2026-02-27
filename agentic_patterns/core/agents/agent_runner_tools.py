"""PydanticAI tool functions for unified agent spawning."""

import asyncio
from collections.abc import Callable

from pydantic_ai import RunContext

from agentic_patterns.core.agents.agent_runner import AgentRunner
from agentic_patterns.core.agents.agent_status import AgentStatus


def get_agent_runner_tools(runner: AgentRunner) -> list[Callable]:
    """Return the three agent spawning tools bound to the given AgentRunner."""

    async def task_launch(
        ctx: RunContext,
        description: str,
        prompt: str,
        agent_name: str,
        *,
        run_in_background: bool = False,
    ) -> str:
        """Launch an agent to handle a task. Returns result (foreground) or agent_id (background)."""
        try:
            result = await runner.launch(
                agent_name, prompt, run_in_background=run_in_background
            )
        except ValueError as e:
            return str(e)

        if run_in_background:
            return (
                f"Agent launched in background: {result.agent_id} ({result.agent_name})"
            )

        if result.usage:
            ctx.usage.incr(result.usage)
        if result.status == AgentStatus.COMPLETED:
            return result.output or ""
        return f"Agent failed: {result.error or result.status.value}"

    async def task_output(
        ctx: RunContext, agent_id: str, *, block: bool = True, timeout: int = 30000
    ) -> str:
        """Get output from a background agent."""
        result = runner.get_output(agent_id)
        if result is None:
            return f"Agent {agent_id} not found."

        if result.status == AgentStatus.RUNNING and block:
            timeout_sec = timeout / 1000
            try:
                await _wait_for_completion(runner, agent_id, timeout_sec)
            except TimeoutError:
                return f"Agent {agent_id} still running after {timeout_sec}s timeout."
            result = runner.get_output(agent_id)
            if result is None:
                return f"Agent {agent_id} not found."

        if result.status == AgentStatus.COMPLETED:
            if result.usage:
                ctx.usage.incr(result.usage)
            return result.output or ""
        if result.status == AgentStatus.RUNNING:
            return f"Agent {agent_id} still running."
        return f"Agent {agent_id}: {result.status.value} - {result.error or ''}"

    async def task_stop(ctx: RunContext, agent_id: str) -> str:
        """Stop a running agent."""
        if runner.stop(agent_id):
            return f"Agent {agent_id} stopped."
        return f"Agent {agent_id} not found or already finished."

    return [task_launch, task_output, task_stop]


async def _wait_for_completion(
    runner: AgentRunner, agent_id: str, timeout: float
) -> None:
    """Wait for an agent to finish. For local agents, awaits the asyncio.Task directly.
    For remote agents, polls with backoff."""
    # Local agent: await the asyncio task directly if available
    local_task = runner._running_tasks.get(agent_id)
    if local_task is not None:
        try:
            await asyncio.wait_for(asyncio.shield(local_task), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError()
        return

    # Remote agent: poll
    elapsed = 0.0
    interval = 0.5
    while elapsed < timeout:
        result = runner.get_output(agent_id)
        if result is None or result.status != AgentStatus.RUNNING:
            return
        await runner.check_remote(agent_id)
        result = runner.get_output(agent_id)
        if result is None or result.status != AgentStatus.RUNNING:
            return
        await asyncio.sleep(interval)
        elapsed += interval
    raise TimeoutError()

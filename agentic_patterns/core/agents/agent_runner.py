"""AgentRunner: unified launcher for local sub-agents and remote A2A agents."""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai.usage import RunUsage

from agentic_patterns.core.agents.agent_status import AgentStatus

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    agent_id: str
    agent_name: str
    status: AgentStatus
    output: str | None = None
    error: str | None = None
    usage: RunUsage | None = None
    # For remote agents: the A2A task ID used to poll status
    _remote_task_id: str | None = field(default=None, repr=False)


class AgentRunner:
    """Spawns and tracks both local sub-agents and remote A2A agents."""

    def __init__(
        self,
        local_agents: dict[str, Any] | None = None,
        remote_agents: dict[str, tuple[Any, dict]] | None = None,
    ):
        self._local_specs = local_agents or {}
        self._remote_agents = (
            remote_agents or {}
        )  # {name: (A2AClientExtended, agent_card)}
        self._running_tasks: dict[str, asyncio.Task] = {}  # local only
        self._results: dict[str, AgentResult] = {}
        self._task_list = None  # set by orchestrator to share TaskList with children

    def catalog(self) -> dict[str, str]:
        """Return {name: description} for all available agents."""
        cat: dict[str, str] = {}
        for name, spec in self._local_specs.items():
            cat[name] = getattr(spec, "description", None) or name
        for name, (_client, card) in self._remote_agents.items():
            cat[name] = card.get("description", name)
        return cat

    async def cancel_all(self) -> None:
        for task in self._running_tasks.values():
            task.cancel()
        self._running_tasks.clear()

    def get_output(self, agent_id: str) -> AgentResult | None:
        return self._results.get(agent_id)

    async def launch(
        self, agent_name: str, prompt: str, *, run_in_background: bool = False
    ) -> AgentResult:
        """Launch an agent (local or remote). Always non-blocking internally.

        If run_in_background=False (foreground), awaits completion before returning.
        If run_in_background=True, returns immediately with status=RUNNING.
        """
        if (
            agent_name not in self._local_specs
            and agent_name not in self._remote_agents
        ):
            all_names = sorted(set(self._local_specs) | set(self._remote_agents))
            raise ValueError(
                f"Unknown agent '{agent_name}'. Available: {', '.join(all_names)}"
            )

        agent_id = str(uuid.uuid4())[:8]

        if agent_name in self._local_specs:
            return await self._launch_local(
                agent_id, agent_name, prompt, run_in_background
            )
        return await self._launch_remote(
            agent_id, agent_name, prompt, run_in_background
        )

    def stop(self, agent_id: str) -> bool:
        # Local agent: cancel the asyncio task
        task = self._running_tasks.pop(agent_id, None)
        if task is not None:
            task.cancel()
            result = self._results.get(agent_id)
            if result:
                result.status = AgentStatus.CANCELLED
            return True

        # Remote agent: best-effort cancel
        result = self._results.get(agent_id)
        if result and result.status == AgentStatus.RUNNING and result._remote_task_id:
            name = result.agent_name
            if name in self._remote_agents:
                client, _ = self._remote_agents[name]
                asyncio.create_task(client.cancel_task(result._remote_task_id))
            result.status = AgentStatus.CANCELLED
            return True

        return False

    async def check_remote(self, agent_id: str) -> None:
        """Poll a remote agent once and update its result if terminal."""
        result = self._results.get(agent_id)
        if (
            result is None
            or result.status != AgentStatus.RUNNING
            or result._remote_task_id is None
        ):
            return
        name = result.agent_name
        if name not in self._remote_agents:
            return
        client, _ = self._remote_agents[name]
        try:
            status, task = await client.get_task(result._remote_task_id)
            if status is None:
                return  # still running
            self._finalize_remote(result, status, task)
        except Exception as e:
            logger.warning(f"Failed to check remote agent {agent_id}: {e}")

    # -- Local agents --

    async def _launch_local(
        self, agent_id: str, agent_name: str, prompt: str, background: bool
    ) -> AgentResult:
        result = AgentResult(
            agent_id=agent_id, agent_name=agent_name, status=AgentStatus.RUNNING
        )
        self._results[agent_id] = result

        if background:
            task = asyncio.create_task(self._run_local(agent_id, agent_name, prompt))
            self._running_tasks[agent_id] = task
            return result

        await self._run_local(agent_id, agent_name, prompt)
        return self._results[agent_id]

    async def _run_local(self, agent_id: str, agent_name: str, prompt: str) -> None:
        from agentic_patterns.core.agents.orchestrator import OrchestratorAgent

        spec = self._local_specs[agent_name]
        result = self._results[agent_id]
        try:
            async with OrchestratorAgent(
                spec, task_list=self._task_list
            ) as orchestrator:
                agent_result = await orchestrator.run(prompt)
                result.output = str(agent_result.output)
                result.usage = agent_result.usage()
                result.status = AgentStatus.COMPLETED
        except asyncio.CancelledError:
            result.status = AgentStatus.CANCELLED
        except Exception as e:
            result.error = str(e)
            result.status = AgentStatus.FAILED
        finally:
            self._running_tasks.pop(agent_id, None)

    # -- Remote agents --

    async def _launch_remote(
        self, agent_id: str, agent_name: str, prompt: str, background: bool
    ) -> AgentResult:
        client, _ = self._remote_agents[agent_name]
        result = AgentResult(
            agent_id=agent_id, agent_name=agent_name, status=AgentStatus.RUNNING
        )
        self._results[agent_id] = result

        try:
            remote_task_id = await client.send_message_only(prompt)
            result._remote_task_id = remote_task_id
        except Exception as e:
            result.error = str(e)
            result.status = AgentStatus.FAILED
            return result

        if not background:
            await self._wait_remote(result)

        return result

    async def _wait_remote(self, result: AgentResult, timeout: float = 300) -> None:
        """Poll remote agent until terminal or timeout."""
        name = result.agent_name
        client, _ = self._remote_agents[name]
        elapsed = 0.0
        interval = 0.5
        while elapsed < timeout:
            try:
                status, task = await client.get_task(result._remote_task_id)
                if status is not None:
                    self._finalize_remote(result, status, task)
                    return
            except Exception as e:
                logger.warning(f"Error polling remote agent {result.agent_id}: {e}")
            await asyncio.sleep(interval)
            elapsed += interval
        result.status = AgentStatus.TIMEOUT

    def _finalize_remote(
        self, result: AgentResult, status: Any, task: dict | None
    ) -> None:
        """Map A2A TaskStatus to AgentStatus and store output."""
        from agentic_patterns.core.a2a.client import TaskStatus as A2ATaskStatus
        from agentic_patterns.core.a2a.utils import extract_text

        match status:
            case A2ATaskStatus.COMPLETED:
                result.status = AgentStatus.COMPLETED
                result.output = extract_text(task) if task else None
            case A2ATaskStatus.FAILED:
                result.status = AgentStatus.FAILED
                result.error = (
                    task["status"].get("message") if task else "Unknown error"
                )
            case A2ATaskStatus.INPUT_REQUIRED:
                result.status = AgentStatus.INPUT_REQUIRED
                result.output = str(task) if task else None
            case A2ATaskStatus.CANCELLED:
                result.status = AgentStatus.CANCELLED
            case A2ATaskStatus.TIMEOUT:
                result.status = AgentStatus.TIMEOUT

    def __str__(self) -> str:
        agents = sorted(set(self._local_specs) | set(self._remote_agents))
        lines = [f"AgentRunner(agents={agents})"]
        for r in self._results.values():
            lines.append(f"  {r.agent_id} ({r.agent_name}): {r.status.value}")
        return "\n".join(lines)

import asyncio
import logging
from typing import Any

from pydantic_ai._agent_graph import CallToolsNode
from pydantic_ai.messages import TextPart, ToolCallPart

from agentic_patterns.core.tasks.models import EventType, TaskEvent
from agentic_patterns.core.tasks.state import TaskState
from agentic_patterns.core.tasks.store import TaskStore

logger = logging.getLogger(__name__)


class Worker:
    """Executes tasks by running sub-agents. Supports both bare agents and AgentSpecs."""

    def __init__(
        self,
        store: TaskStore,
        model: Any = None,
        agent_specs: dict[str, Any] | None = None,
    ) -> None:
        self._store = store
        self._model = model
        self._agent_specs = agent_specs or {}

    async def execute(self, task_id: str) -> None:
        task = await self._store.get(task_id)
        if task is None:
            logger.warning("Task %s not found", task_id[:8])
            return

        await self._store.update_state(task_id, TaskState.RUNNING)
        await self._store.add_event(
            task_id,
            TaskEvent(
                task_id=task_id,
                event_type=EventType.STATE_CHANGE,
                payload={"state": TaskState.RUNNING.value},
            ),
        )

        try:
            agent_name = task.metadata.get("agent_name")
            if agent_name and agent_name in self._agent_specs:
                result, usage_dict = await self._execute_with_spec(task_id, task.input, agent_name)
            else:
                result, usage_dict = await self._execute_bare(task_id, task)

            await self._store.update_state(task_id, TaskState.COMPLETED, result=result)
            await self._store.add_event(
                task_id,
                TaskEvent(
                    task_id=task_id,
                    event_type=EventType.STATE_CHANGE,
                    payload={"state": TaskState.COMPLETED.value, "usage": usage_dict},
                ),
            )
            logger.info("Task %s completed", task_id[:8])

        except asyncio.CancelledError:
            await self._store.update_state(task_id, TaskState.CANCELLED)
            await self._store.add_event(
                task_id,
                TaskEvent(
                    task_id=task_id,
                    event_type=EventType.STATE_CHANGE,
                    payload={"state": TaskState.CANCELLED.value},
                ),
            )
            logger.info("Task %s cancelled", task_id[:8])
            raise

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            await self._store.update_state(task_id, TaskState.FAILED, error=error_msg)
            await self._store.add_event(
                task_id,
                TaskEvent(
                    task_id=task_id,
                    event_type=EventType.STATE_CHANGE,
                    payload={"state": TaskState.FAILED.value, "error": error_msg},
                ),
            )
            logger.error("Task %s failed: %s", task_id[:8], error_msg)

    async def _execute_bare(self, task_id: str, task: Any) -> tuple[str, dict]:
        """Fallback: run with bare get_agent()/run_agent() (backward compat)."""
        from agentic_patterns.core.agents import get_agent, run_agent

        system_prompt = task.metadata.get("system_prompt", "You are a helpful assistant.")
        config_name = task.metadata.get("config_name", "default")
        agent = await asyncio.to_thread(get_agent, model=self._model, config_name=config_name, system_prompt=system_prompt)
        agent_run, _ = await run_agent(agent, task.input)
        if agent_run is None:
            raise RuntimeError("Agent run returned None")
        result = str(agent_run.result.output)
        usage = agent_run.result.usage()
        return result, {"requests": usage.requests, "request_tokens": usage.request_tokens, "response_tokens": usage.response_tokens, "total_tokens": usage.total_tokens}

    async def _execute_with_spec(self, task_id: str, prompt: str, agent_name: str) -> tuple[str, dict]:
        """Run via OrchestratorAgent using the registered AgentSpec."""
        from agentic_patterns.core.agents.orchestrator import OrchestratorAgent

        spec = self._agent_specs[agent_name]
        node_hook = self._make_node_hook(task_id)

        async with OrchestratorAgent(spec, on_node=node_hook) as sub:
            run_result = await sub.run(prompt)

        usage = run_result.usage()
        usage_dict = {"requests": usage.requests, "request_tokens": usage.request_tokens, "response_tokens": usage.response_tokens, "total_tokens": usage.total_tokens}
        return run_result.output, usage_dict

    def _make_node_hook(self, task_id: str):
        """Create a node hook that emits PROGRESS/LOG events to the store."""
        store = self._store

        def hook(node) -> None:
            if not isinstance(node, CallToolsNode):
                return
            for part in node.model_response.parts:
                if isinstance(part, ToolCallPart):
                    args = part.args_as_dict() or {}
                    first_val = str(next(iter(args.values()), ""))[:80]
                    asyncio.get_event_loop().create_task(
                        store.add_event(
                            task_id,
                            TaskEvent(
                                task_id=task_id,
                                event_type=EventType.PROGRESS,
                                payload={"tool": part.tool_name, "arg": first_val},
                            ),
                        )
                    )
                elif isinstance(part, TextPart) and part.content.strip():
                    snippet = part.content.strip().replace("\n", " ")[:120]
                    asyncio.get_event_loop().create_task(
                        store.add_event(
                            task_id,
                            TaskEvent(
                                task_id=task_id,
                                event_type=EventType.LOG,
                                payload={"message": snippet},
                            ),
                        )
                    )

        return hook

import logging

from agentic_patterns.core.agents import get_agent, run_agent
from agentic_patterns.core.tasks.models import EventType, TaskEvent
from agentic_patterns.core.tasks.state import TaskState
from agentic_patterns.core.tasks.store import TaskStore

logger = logging.getLogger(__name__)


class Worker:
    """Executes tasks by running sub-agents. Stateless with respect to task identity."""

    def __init__(self, store: TaskStore, model=None) -> None:
        self._store = store
        self._model = model

    async def execute(self, task_id: str) -> None:
        task = await self._store.get(task_id)
        if task is None:
            logger.warning("Task %s not found", task_id[:8])
            return

        await self._store.update_state(task_id, TaskState.RUNNING)
        await self._store.add_event(task_id, TaskEvent(task_id=task_id, event_type=EventType.STATE_CHANGE, payload={"state": TaskState.RUNNING.value}))

        try:
            system_prompt = task.metadata.get("system_prompt", "You are a helpful assistant.")
            config_name = task.metadata.get("config_name", "default")
            agent = get_agent(model=self._model, config_name=config_name, system_prompt=system_prompt)
            agent_run, _ = await run_agent(agent, task.input)

            if agent_run is None:
                raise RuntimeError("Agent run returned None")

            result = str(agent_run.result.output)
            await self._store.update_state(task_id, TaskState.COMPLETED, result=result)
            await self._store.add_event(task_id, TaskEvent(task_id=task_id, event_type=EventType.STATE_CHANGE, payload={"state": TaskState.COMPLETED.value}))
            logger.info("Task %s completed", task_id[:8])

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            await self._store.update_state(task_id, TaskState.FAILED, error=error_msg)
            await self._store.add_event(task_id, TaskEvent(task_id=task_id, event_type=EventType.STATE_CHANGE, payload={"state": TaskState.FAILED.value, "error": error_msg}))
            logger.error("Task %s failed: %s", task_id[:8], error_msg)

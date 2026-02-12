import asyncio
import logging
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any

from agentic_patterns.core.tasks.models import Task, TaskEvent, EventType
from agentic_patterns.core.tasks.state import TERMINAL_STATES, TaskState
from agentic_patterns.core.tasks.store import TaskStore, TaskStoreJson
from agentic_patterns.core.tasks.worker import Worker

logger = logging.getLogger(__name__)


class TaskBroker:
    """Coordination layer for task submission, observation, and dispatch."""

    def __init__(
        self,
        store: TaskStore | None = None,
        poll_interval: float = 0.5,
        model: Any = None,
        activity: asyncio.Event | None = None,
    ) -> None:
        self._store = store or TaskStoreJson()
        self._poll_interval = poll_interval
        self._model = model
        self._activity = activity
        self._agent_specs: dict[str, Any] = {}
        self._worker = Worker(self._store, model=model)
        self._dispatch_task: asyncio.Task | None = None
        self._running: dict[str, asyncio.Task] = {}
        self._callbacks: dict[
            str,
            list[tuple[set[TaskState], Callable[[Task], Coroutine[Any, Any, None]]]],
        ] = {}

    def register_agents(self, specs: dict[str, Any]) -> None:
        """Register AgentSpecs so the worker can resolve them by name."""
        self._agent_specs.update(specs)
        self._worker = Worker(self._store, model=self._model, agent_specs=self._agent_specs)

    async def __aenter__(self) -> "TaskBroker":
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._dispatch_task is not None:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
            self._dispatch_task = None

    # -- Submission --

    async def submit(self, input: str, **metadata: Any) -> str:
        """Create a task and return its id."""
        task = Task(input=input, metadata=metadata)
        await self._store.create(task)
        logger.info("Submitted task %s", task.id[:8])
        return task.id

    # -- Observation --

    async def cancel(self, task_id: str) -> Task | None:
        """Cancel a pending or running task."""
        task = await self._store.get(task_id)
        if task is None or task.state in TERMINAL_STATES:
            return task
        # Cancel the asyncio.Task if running
        running_task = self._running.get(task_id)
        if running_task and not running_task.done():
            running_task.cancel()
        updated = await self._store.update_state(task_id, TaskState.CANCELLED)
        await self._store.add_event(
            task_id,
            TaskEvent(
                task_id=task_id,
                event_type=EventType.STATE_CHANGE,
                payload={"state": TaskState.CANCELLED.value},
            ),
        )
        logger.info("Cancelled task %s", task_id[:8])
        return updated

    async def cancel_all(self) -> None:
        """Cancel all non-terminal tasks and their asyncio.Tasks."""
        for task_id, atask in list(self._running.items()):
            if not atask.done():
                atask.cancel()
        for task_id in list(self._running.keys()):
            task = await self._store.get(task_id)
            if task and task.state not in TERMINAL_STATES:
                await self._store.update_state(task_id, TaskState.CANCELLED)

    async def notify(
        self,
        task_id: str,
        states: set[TaskState],
        callback: Callable[[Task], Coroutine[Any, Any, None]],
    ) -> None:
        """Register a callback for specific state changes."""
        self._callbacks.setdefault(task_id, []).append((states, callback))

    async def poll(self, task_id: str) -> Task | None:
        """Return current task state."""
        return await self._store.get(task_id)

    async def stream(self, task_id: str) -> AsyncIterator[TaskEvent]:
        """Yield events as they arrive until task reaches terminal state."""
        seen = 0
        while True:
            task = await self._store.get(task_id)
            if task is None:
                return
            new_events = task.events[seen:]
            for event in new_events:
                yield event
            seen = len(task.events)
            if task.state in TERMINAL_STATES:
                return
            await asyncio.sleep(self._poll_interval)

    async def wait(self, task_id: str) -> Task | None:
        """Poll until the task reaches a terminal state."""
        while True:
            task = await self._store.get(task_id)
            if task is None:
                return None
            if task.state in TERMINAL_STATES:
                return task
            await asyncio.sleep(self._poll_interval)

    # -- Dispatch --

    async def _dispatch_loop(self) -> None:
        """Background loop that picks pending tasks and dispatches them concurrently."""
        while True:
            try:
                task = await self._store.next_pending()
                if task is not None and task.id not in self._running:
                    atask = asyncio.create_task(self._run_and_notify(task.id))
                    self._running[task.id] = atask
                await asyncio.sleep(self._poll_interval)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Dispatch loop error")
                await asyncio.sleep(self._poll_interval)

    async def _run_and_notify(self, task_id: str) -> None:
        """Run worker for a task, fire callbacks, handle cancellation."""
        try:
            await self._worker.execute(task_id)
            await self._fire_callbacks(task_id)
        except asyncio.CancelledError:
            # Worker handles CancelledError internally (marks CANCELLED)
            pass
        except Exception:
            logger.exception("Error running task %s", task_id[:8])
        finally:
            self._running.pop(task_id, None)
            if self._activity is not None:
                self._activity.set()

    async def _fire_callbacks(self, task_id: str) -> None:
        """Fire registered callbacks if the task state matches."""
        task = await self._store.get(task_id)
        if task is None:
            return
        for states, callback in self._callbacks.get(task_id, []):
            if task.state in states:
                try:
                    await callback(task)
                except Exception:
                    logger.exception("Callback error for task %s", task_id[:8])

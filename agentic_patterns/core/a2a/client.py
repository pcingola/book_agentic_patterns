"""Extended A2A client with polling, retry, timeout, and cancellation."""

import asyncio
import logging
import time
from collections.abc import Callable
from enum import Enum

from fasta2a.client import A2AClient

from agentic_patterns.core.a2a.config import A2AClientConfig, get_client_config
from agentic_patterns.core.a2a.utils import create_message

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Possible status outcomes from send_and_observe."""
    COMPLETED = "completed"
    FAILED = "failed"
    INPUT_REQUIRED = "input-required"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class A2AClientExtended:
    """Extended A2A client with polling, retry, timeout, and cancellation support."""

    def __init__(self, config: A2AClientConfig):
        self._config = config
        self._client = A2AClient(base_url=config.url)
        if config.bearer_token:
            self._client.http_client.headers["Authorization"] = f"Bearer {config.bearer_token}"

    async def get_agent_card(self) -> dict:
        """Fetch agent card from /.well-known/agent-card.json"""
        response = await self._client.http_client.get("/.well-known/agent-card.json")
        response.raise_for_status()
        return response.json()

    async def cancel_task(self, task_id: str) -> dict | None:
        """Cancel a task via JSON-RPC tasks/cancel method."""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tasks/cancel",
                "params": {"id": task_id}
            }
            response = await self._client.http_client.post("/", json=payload)
            response.raise_for_status()
            result = response.json()
            if "result" in result:
                return result["result"]
            return None
        except Exception as e:
            logger.warning(f"[A2A] Failed to cancel task {task_id}: {e}")
            return None

    async def send_and_observe(
        self,
        prompt: str,
        task_id: str | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> tuple[TaskStatus, dict | None]:
        """Send message and poll until terminal state or input-required.

        Args:
            prompt: The message text to send
            task_id: Existing task ID for continuing a conversation
            is_cancelled: Callback to check if operation should be cancelled

        Returns:
            Tuple of (status, task) where status indicates the outcome
        """
        start_time = time.monotonic()

        message = create_message(prompt)
        if task_id:
            response = await self._send_with_retry(message, task_id=task_id)
        else:
            response = await self._send_with_retry(message)

        # JSON-RPC response has result field containing the task
        result = response["result"]
        task_id = result["id"]
        logger.info(f"[A2A] Task {task_id} created")

        while True:
            elapsed = time.monotonic() - start_time

            if elapsed > self._config.timeout:
                logger.error(f"[A2A] Task {task_id} timed out")
                await self.cancel_task(task_id)
                return (TaskStatus.TIMEOUT, None)

            if is_cancelled and is_cancelled():
                logger.info(f"[A2A] Task {task_id} cancelled by user")
                await self.cancel_task(task_id)
                return (TaskStatus.CANCELLED, None)

            response = await self._get_task_with_retry(task_id)
            task = response["result"]
            state = task["status"]["state"]
            logger.debug(f"[A2A] Task {task_id}: {state}")

            match state:
                case "completed":
                    logger.info(f"[A2A] Task {task_id} completed")
                    return (TaskStatus.COMPLETED, task)
                case "failed" | "rejected":
                    logger.error(f"[A2A] Task {task_id} {state}")
                    return (TaskStatus.FAILED, task)
                case "canceled":
                    return (TaskStatus.CANCELLED, task)
                case "input-required":
                    logger.info(f"[A2A] Task {task_id} needs input")
                    return (TaskStatus.INPUT_REQUIRED, task)

            await asyncio.sleep(self._config.poll_interval)

    async def _send_with_retry(self, message, **kwargs):
        """Send message with exponential backoff retry."""
        for attempt in range(self._config.max_retries):
            try:
                return await self._client.send_message(message, **kwargs)
            except (ConnectionError, TimeoutError) as e:
                if attempt == self._config.max_retries - 1:
                    raise
                delay = self._config.retry_delay * (2 ** attempt)
                logger.warning(f"[A2A] Retry {attempt + 1}: {e}")
                await asyncio.sleep(delay)
        raise RuntimeError("Max retries exceeded")

    async def _get_task_with_retry(self, task_id: str) -> dict:
        """Get task status with exponential backoff retry."""
        for attempt in range(self._config.max_retries):
            try:
                return await self._client.get_task(task_id)
            except (ConnectionError, TimeoutError) as e:
                if attempt == self._config.max_retries - 1:
                    raise
                delay = self._config.retry_delay * (2 ** attempt)
                logger.warning(f"[A2A] Retry {attempt + 1}: {e}")
                await asyncio.sleep(delay)
        raise RuntimeError("Max retries exceeded")


def get_a2a_client(config_name: str) -> A2AClientExtended:
    """Get an A2A client by configuration name."""
    config = get_client_config(config_name)
    return A2AClientExtended(config)

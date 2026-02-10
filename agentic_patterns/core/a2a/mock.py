"""Mock A2A server for testing without LLM calls."""

import re
import uuid

from fastapi import FastAPI, Request


class MockA2AServer:
    """A controllable A2A server for testing."""

    def __init__(
        self, name: str = "MockAgent", description: str = "A mock agent for testing"
    ):
        self._card = {
            "name": name,
            "description": description,
            "skills": [],
            "url": "http://localhost:8000",
            "version": "1.0.0",
            "protocolVersion": "0.3.0",
            "defaultInputModes": ["application/json"],
            "defaultOutputModes": ["application/json"],
            "capabilities": {
                "streaming": False,
                "pushNotifications": False,
                "stateTransitionHistory": False,
            },
        }
        self._responses: list[tuple[re.Pattern | str, dict]] = []
        self._default_result = "OK"
        self._tasks: dict[str, dict] = {}
        self._task_poll_counts: dict[str, int] = {}
        self._delayed_responses: dict[
            str, tuple[int, dict]
        ] = {}  # task_id -> (polls_needed, final_response)
        self.received_prompts: list[str] = []
        self.cancelled_task_ids: set[str] = set()

    def on_prompt(
        self,
        prompt: str,
        *,
        result: str | None = None,
        error: str | None = None,
        input_required: str | None = None,
    ) -> "MockA2AServer":
        """Configure response for exact prompt match."""
        self._responses.append(
            (prompt, self._make_response(result, error, input_required))
        )
        return self

    def on_pattern(
        self,
        pattern: str,
        *,
        result: str | None = None,
        error: str | None = None,
        input_required: str | None = None,
    ) -> "MockA2AServer":
        """Configure response for regex pattern match."""
        self._responses.append(
            (
                re.compile(pattern, re.IGNORECASE),
                self._make_response(result, error, input_required),
            )
        )
        return self

    def set_default(self, result: str) -> "MockA2AServer":
        """Set default result when no pattern matches."""
        self._default_result = result
        return self

    def on_prompt_delayed(
        self,
        prompt: str,
        polls: int,
        *,
        result: str | None = None,
        error: str | None = None,
        input_required: str | None = None,
    ) -> "MockA2AServer":
        """Configure a delayed response that returns 'working' until N polls, then final state."""
        self._responses.append(
            (
                prompt,
                {
                    "state": "working",
                    "polls": polls,
                    "final": self._make_response(result, error, input_required),
                },
            )
        )
        return self

    def _make_response(
        self, result: str | None, error: str | None, input_required: str | None
    ) -> dict:
        if error:
            return {"state": "failed", "error": error}
        if input_required:
            return {"state": "input-required", "question": input_required}
        return {"state": "completed", "result": result or "OK"}

    def _find_response(self, prompt: str) -> dict:
        for pattern, response in self._responses:
            if isinstance(pattern, re.Pattern):
                if pattern.search(prompt):
                    return response
            elif pattern == prompt:
                return response
        return {"state": "completed", "result": self._default_result}

    def _build_task(self, task_id: str, context_id: str, response: dict) -> dict:
        status: dict = {"state": response["state"]}
        if response["state"] == "input-required" and "question" in response:
            status["message"] = {
                "role": "agent",
                "parts": [{"kind": "text", "text": response["question"]}],
                "kind": "message",
                "messageId": str(uuid.uuid4()),
            }

        task: dict = {
            "id": task_id,
            "contextId": context_id,
            "kind": "task",
            "status": status,
        }

        if response["state"] == "completed":
            task["artifacts"] = [
                {
                    "artifactId": str(uuid.uuid4()),
                    "parts": [{"kind": "text", "text": response["result"]}],
                }
            ]
        elif response["state"] == "failed":
            status["message"] = {
                "role": "agent",
                "parts": [{"kind": "text", "text": response["error"]}],
                "kind": "message",
                "messageId": str(uuid.uuid4()),
            }

        return task

    def _extract_prompt(self, params: dict) -> str:
        """Extract prompt text from message."""
        message = params.get("message", {})
        if isinstance(message, dict):
            parts = message.get("parts", [])
            for part in parts:
                if isinstance(part, dict) and part.get("kind") == "text":
                    return part.get("text", "")
        return ""

    def to_app(self) -> FastAPI:
        """Create FastAPI app for this mock server."""
        app = FastAPI()

        @app.get("/.well-known/agent-card.json")
        async def get_agent_card():
            return self._card

        @app.post("/")
        async def handle_jsonrpc(request: Request):
            body = await request.json()
            method = body.get("method", "")
            params = body.get("params", {})
            req_id = body.get("id", 1)

            if method == "message/send":
                prompt = self._extract_prompt(params)
                self.received_prompts.append(prompt)
                task_id = str(uuid.uuid4())
                context_id = str(uuid.uuid4())
                response = self._find_response(prompt)

                # Handle delayed responses
                if response.get("state") == "working":
                    self._delayed_responses[task_id] = (
                        response["polls"],
                        response["final"],
                    )
                    self._task_poll_counts[task_id] = 0
                    task = self._build_task(task_id, context_id, {"state": "working"})
                else:
                    task = self._build_task(task_id, context_id, response)

                self._tasks[task_id] = task
                return {"jsonrpc": "2.0", "id": req_id, "result": task}

            elif method == "tasks/get":
                task_id = params.get("id")
                task = self._tasks.get(task_id)
                if task:
                    if task_id in self.cancelled_task_ids:
                        task = {**task, "status": {"state": "canceled"}}
                    elif task_id in self._delayed_responses:
                        self._task_poll_counts[task_id] = (
                            self._task_poll_counts.get(task_id, 0) + 1
                        )
                        polls_needed, final_response = self._delayed_responses[task_id]
                        if self._task_poll_counts[task_id] >= polls_needed:
                            task = self._build_task(
                                task_id, task["contextId"], final_response
                            )
                            self._tasks[task_id] = task
                            del self._delayed_responses[task_id]
                    return {"jsonrpc": "2.0", "id": req_id, "result": task}
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32001, "message": "Task not found"},
                }

            elif method == "tasks/cancel":
                task_id = params.get("id")
                if task_id in self._tasks:
                    self.cancelled_task_ids.add(task_id)
                    task = {**self._tasks[task_id], "status": {"state": "canceled"}}
                    return {"jsonrpc": "2.0", "id": req_id, "result": task}
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32001, "message": "Task not found"},
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": "Method not found"},
            }

        return app

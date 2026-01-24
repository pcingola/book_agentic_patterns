# A2A Library Implementation Plan

## What fasta2a Already Provides

**Client (`fasta2a.client.A2AClient`):**
- `send_message(message)` - sends message, returns Task or Message
- `get_task(task_id)` - returns Task with status, artifacts, history

**Schema (`fasta2a.schema`):**
- `TaskState` - literal: 'submitted', 'working', 'input-required', 'completed', 'canceled', 'failed', 'rejected', 'auth-required', 'unknown'
- `Task`, `TaskStatus`, `Message`, `TextPart`, `FilePart`, `DataPart`, `Artifact`
- `AgentCard`, `Skill`
- Error types: `TaskNotFoundError`, `TaskNotCancelableError`, etc.

## What We Need to Add

| Feature | Why |
|---------|-----|
| `cancel_task()` | Protocol supports it, client doesn't implement |
| `get_agent_card()` | Need to fetch from `/.well-known/agent.json` |
| Polling loop | Client only has single-shot methods |
| Retry on transient errors | Network resilience |
| Timeout | Prevent stuck tasks |
| Config from YAML | Consistent with rest of core library |
| Tool factory | Create PydanticAI tools for coordinator agents |

## Architecture

```
[User] <-> [UI] <-> [Coordinator Agent] <-> [A2A Tool] <-> [Remote Agent]
```

Human-in-the-loop: Tool returns `[INPUT_REQUIRED:task_id=xyz] question`, coordinator asks user, calls tool again with `task_id` to continue.

Cancellation: Tool checks `is_cancelled()` each poll cycle, calls `cancel_task()` when triggered.

## Module Structure

```
agentic_patterns/core/a2a/
    config.py    # Config models, YAML loading
    client.py    # Extended A2AClient with polling, retry, timeout
    tool.py      # Tool factory for coordinator agents
    utils.py     # Helpers: extract_text, create_message
```

## config.py

```yaml
# config.yaml
a2a:
  clients:
    arithmetic:
      url: "http://localhost:8000"
      timeout: 300
      poll_interval: 1.0
      max_retries: 3
      retry_delay: 1.0
```

```python
from pydantic import BaseModel

class A2AClientConfig(BaseModel):
    url: str
    timeout: int = 300
    poll_interval: float = 1.0
    max_retries: int = 3
    retry_delay: float = 1.0

def get_client_config(name: str) -> A2AClientConfig: ...
def list_client_configs() -> list[str]: ...
```

## client.py

Extends `fasta2a.client.A2AClient` with missing methods and polling loop.

```python
import logging
import time
from fasta2a.client import A2AClient
from fasta2a.schema import Task, Message, TextPart, AgentCard, TaskState

logger = logging.getLogger(__name__)

class A2AClientExtended:
    """Extended A2A client with polling, retry, timeout, and cancellation."""

    def __init__(self, config: A2AClientConfig):
        self._config = config
        self._client = A2AClient(base_url=config.url)

    async def get_agent_card(self) -> AgentCard:
        """Fetch agent card from /.well-known/agent.json"""
        response = await self._client.http_client.get("/.well-known/agent.json")
        response.raise_for_status()
        return response.json()

    async def cancel_task(self, task_id: str) -> Task:
        """Cancel a task via tasks/cancel method."""
        # Implement JSON-RPC call to tasks/cancel
        ...

    async def send_and_observe(
        self,
        prompt: str,
        task_id: str | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> tuple[str, Task]:
        """
        Send message and poll until terminal state or input-required.

        Returns (status, task) where status is one of:
        - "completed"
        - "failed"
        - "input-required"
        - "cancelled"
        - "timeout"
        """
        start_time = time.monotonic()

        # Send message (with retry)
        message = create_message(prompt)
        if task_id:
            response = await self._send_with_retry(message, task_id=task_id)
        else:
            response = await self._send_with_retry(message)

        task_id = response.result["id"]
        logger.info(f"[A2A] Task {task_id} created")

        # Poll loop
        while True:
            elapsed = time.monotonic() - start_time

            # Timeout check
            if elapsed > self._config.timeout:
                logger.error(f"[A2A] Task {task_id} timed out")
                try:
                    await self.cancel_task(task_id)
                except Exception:
                    pass
                return ("timeout", None)

            # Cancellation check
            if is_cancelled and is_cancelled():
                logger.info(f"[A2A] Task {task_id} cancelled by user")
                await self.cancel_task(task_id)
                return ("cancelled", None)

            # Get task (with retry)
            task = await self._get_task_with_retry(task_id)
            state = task["status"]["state"]
            logger.debug(f"[A2A] Task {task_id}: {state}")

            if state == "completed":
                logger.info(f"[A2A] Task {task_id} completed")
                return ("completed", task)

            if state in ("failed", "rejected"):
                logger.error(f"[A2A] Task {task_id} {state}")
                return ("failed", task)

            if state == "canceled":
                return ("cancelled", task)

            if state == "input-required":
                logger.info(f"[A2A] Task {task_id} needs input")
                return ("input-required", task)

            await asyncio.sleep(self._config.poll_interval)

    async def _send_with_retry(self, message: Message, **kwargs) -> SendMessageResponse:
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

    async def _get_task_with_retry(self, task_id: str) -> Task:
        """Get task with exponential backoff retry."""
        # Similar retry logic
        ...

def get_a2a_client(config_name: str) -> A2AClientExtended:
    config = get_client_config(config_name)
    return A2AClientExtended(config)
```

## tool.py

Creates PydanticAI tools from A2A clients.

```python
from pydantic_ai import Tool

def create_a2a_tool(client: A2AClientExtended, name: str | None = None) -> Tool:
    """
    Create a PydanticAI tool that delegates to a remote A2A agent.

    Returns formatted string for coordinator to interpret:
    - [COMPLETED] result text
    - [INPUT_REQUIRED:task_id=xyz] question
    - [FAILED] error message
    - [CANCELLED] task was cancelled
    - [TIMEOUT] task timed out
    """
    card = asyncio.run(client.get_agent_card())
    tool_name = name or slugify(card["name"])

    async def delegate(ctx: RunContext, prompt: str, task_id: str | None = None) -> str:
        def is_cancelled() -> bool:
            return getattr(ctx, "is_cancelled", lambda: False)()

        status, task = await client.send_and_observe(
            prompt=prompt,
            task_id=task_id,
            is_cancelled=is_cancelled,
        )

        match status:
            case "completed":
                return f"[COMPLETED] {extract_text(task)}"
            case "input-required":
                question = extract_question(task)
                return f"[INPUT_REQUIRED:task_id={task['id']}] {question}"
            case "failed":
                return f"[FAILED] {task['status'].get('message', 'Unknown error')}"
            case "cancelled":
                return "[CANCELLED] Task was cancelled"
            case "timeout":
                return "[TIMEOUT] Task timed out"

    delegate.__name__ = tool_name
    delegate.__doc__ = f"Delegate to {card['name']}: {card['description']}"

    return Tool(delegate)
```

## utils.py

Thin wrappers around fasta2a types.

```python
import uuid
from fasta2a.schema import Message, TextPart, Task

def create_message(text: str, message_id: str | None = None) -> Message:
    return Message(
        role="user",
        kind="message",
        parts=[TextPart(kind="text", text=text)],
        message_id=message_id or str(uuid.uuid4()),
    )

def extract_text(task: Task) -> str | None:
    """Extract text from task artifacts."""
    texts = []
    for artifact in task.get("artifacts") or []:
        for part in artifact.get("parts") or []:
            if part.get("kind") == "text":
                texts.append(part["text"])
    return "\n".join(texts) if texts else None

def extract_question(task: Task) -> str:
    """Extract question from input-required task."""
    status = task.get("status", {})
    msg = status.get("message")
    if msg and isinstance(msg, dict):
        for part in msg.get("parts") or []:
            if part.get("kind") == "text":
                return part["text"]
    return "Agent requires input"

def agent_card_to_prompt(card: dict) -> str:
    """Format agent card for coordinator system prompt."""
    lines = [f"## {card['name']}", card.get("description", ""), "", "Skills:"]
    for skill in card.get("skills") or []:
        lines.append(f"- {skill['name']}: {skill.get('description', '')}")
    return "\n".join(lines)

def slugify(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")
```

## Usage Example

```python
from agentic_patterns.core.a2a import get_a2a_client, create_a2a_tool, agent_card_to_prompt
from agentic_patterns.core.agents import get_agent

# Create clients
math_client = get_a2a_client("arithmetic")
tax_client = get_a2a_client("tax_calculator")

# Create tools
math_tool = create_a2a_tool(math_client)
tax_tool = create_a2a_tool(tax_client)

# Build system prompt with agent descriptions
math_card = await math_client.get_agent_card()
tax_card = await tax_client.get_agent_card()

system_prompt = f"""You coordinate tasks between specialized agents.

Available agents:
{agent_card_to_prompt(math_card)}
{agent_card_to_prompt(tax_card)}

When you see [INPUT_REQUIRED:task_id=...], ask the user and call the tool again with task_id.
"""

# Create coordinator
coordinator = get_agent(system_prompt=system_prompt, tools=[math_tool, tax_tool])

# Run
result = await coordinator.run("Calculate taxes for $75000 income")
```

## Coverage

| Feature | Status |
|---------|--------|
| Reuse fasta2a types | Yes - no redundant definitions |
| Config from YAML | Yes |
| Polling with retry | Yes |
| Timeout | Yes |
| Cancellation | Yes |
| Human-in-the-loop | Yes (via tool response format) |
| Tool factory | Yes |
| Logging/observability | Yes |
| Health check | Via get_agent_card() |

## Not Covered (deferred)

| Feature | Reason |
|---------|--------|
| SSE streaming | Polling sufficient for POC |
| Push notifications | Requires webhook server |
| Authentication | Add as middleware later |
| Server config | Focus on client side first |

## Code to Reuse from aixtools

### From `aixtools/a2a/utils.py` (take as-is or adapt)

| Function | Action | Notes |
|----------|--------|-------|
| `fetch_agent_card(client)` | Take | Fetches `/.well-known/agent.json` |
| `get_result_text(ret)` | Take | Extracts text from task artifacts |
| `text_message(text)` | Take | Creates Message with TextPart |
| `tool2skill(tool)` | Take | Converts tool function to Skill |
| `card2description(card)` | Take | Formats card for system prompt |
| `poll_task(client, task_id)` | Adapt | Add retry, timeout, cancellation, input-required |

### From `aixtools/a2a_direct_client/tool.py` (adapt patterns)

| Function | Action | Notes |
|----------|--------|-------|
| `_build_agent_tool_description(card)` | Adapt | Good pattern: lists skills with descriptions |
| `_agent_tool_name(card)` | Take | Slugify with regex: `re.sub(r"[^0-9a-zA-Z_]", "_", base)` |
| `_agent_tool_schema(card)` | Adapt | Includes skill examples in tool schema |

### Not taking

| Code | Reason |
|------|--------|
| `A2AClientWithBearerAuth` | Uses different `a2a` library, not fasta2a |
| `RemoteAgentConnection` | Google SDK dependency we don't need |
| Session metadata injection | Specific to their context system |

## Implementation Order

1. `config.py` - A2AClientConfig, YAML loading
2. `utils.py` - take from aixtools: `text_message`, `fetch_agent_card`, `get_result_text`, `card2description`, `tool2skill`
3. `client.py` - adapt `poll_task` into `send_and_observe` with retry/timeout/cancellation
4. `tool.py` - adapt `_build_agent_tool_description`, `_agent_tool_name`, `_agent_tool_schema`
5. Add `a2a.clients` section to config.yaml

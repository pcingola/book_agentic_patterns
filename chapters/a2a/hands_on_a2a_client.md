# Hands-On: A2A Client-Server

This hands-on demonstrates the A2A protocol in action through `example_a2a_server.py` and `example_a2a_client.ipynb`. The server exposes an agent with tools over HTTP, and the client discovers the agent's capabilities, sends a task, and retrieves results using the standard A2A operations.

## The A2A Server

The server in `example_a2a_server.py` creates an agent with two arithmetic tools and exposes it via the A2A protocol:

```python
from agentic_patterns.core.agents import get_agent


def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


def sub(a: int, b: int) -> int:
    """Subtract two numbers"""
    return a - b


agent = get_agent(tools=[add, sub])
app = agent.to_a2a()
```

The `to_a2a()` method transforms a PydanticAI agent into an ASGI application that speaks the A2A protocol. This application handles JSON-RPC requests for task creation, message sending, and task retrieval. It also serves the Agent Card at the well-known URL.

Start the server with uvicorn:

```bash
uvicorn agentic_patterns.a2a.example_a2a_server:app --host 0.0.0.0 --port 8000
```

## Discovering the Agent

Before sending work to an agent, a client can retrieve its Agent Card to understand what it offers. The card is published at a well-known URL:

```python
import httpx

async with httpx.AsyncClient() as http:
    response = await http.get("http://127.0.0.1:8000/.well-known/agent-card.json")
    card = response.json()
```

The Agent Card contains metadata about the agent: its name, description, supported capabilities, and available skills. This "metadata-first" approach lets clients make routing decisions before sending any task content.

## Creating an A2A Client

The `fasta2a` library provides an `A2AClient` that handles the JSON-RPC protocol details:

```python
from fasta2a.client import A2AClient

client = A2AClient(base_url="http://127.0.0.1:8000")
```

The client connects to the server's base URL and provides methods for the core A2A operations: sending messages, retrieving tasks, and managing task lifecycle.

## Sending a Task

A2A messages are structured with parts that can contain text, files, or structured data. For a simple text request:

```python
from fasta2a.schema import Message, TextPart
import uuid

prompt = "What is the sum of 40123456789 and 2123456789?"

message = Message(
    kind="message",
    role="user",
    parts=[TextPart(kind="text", text=prompt)],
    message_id=str(uuid.uuid4())
)

response = await client.send_message(message=message)
task_id = response['result']['id']
```

The `message_id` is client-generated and enables idempotent retries. If the same message is sent twice (due to network issues), the server can detect the duplicate and return the existing result.

The response includes a task ID that serves as the handle for all subsequent operations on this unit of work.

## Polling for Completion

A2A tasks are asynchronous by default. After sending a message, the client polls for status updates:

```python
import asyncio

while True:
    task = await client.get_task(task_id=task_id)
    state = task['result']['status']['state']

    if state == "completed":
        break
    elif state == "failed":
        raise Exception("Task failed")

    await asyncio.sleep(0.2)
```

The task progresses through states like "working" before reaching a terminal state ("completed", "failed", "cancelled", or "rejected"). Polling is intentionally simple and robust, making it suitable for environments where streaming connections are not feasible.

## Extracting Results

Completed tasks include artifacts containing the outputs:

```python
artifacts = task['result'].get('artifacts', [])
for artifact in artifacts:
    for part in artifact.get('parts', []):
        if part.get('kind') == 'text':
            print(part['text'])
```

Artifacts are first-class objects in A2A, not just response text. They can contain structured data, files, or multiple parts, making them suitable for diverse output types.

## Key Takeaways

The A2A protocol standardizes agent-to-agent communication over HTTP using JSON-RPC. `to_a2a()` converts any PydanticAI agent into an A2A server with no changes to the agent's internal design.

Agent Cards enable discovery and capability matching before task submission. Clients can inspect what an agent offers and make routing decisions based on declared skills.

Tasks are the central abstraction. They have identities, states, and lifecycles that persist beyond individual request-response cycles. This supports long-running operations, retries, and coordination patterns that synchronous APIs cannot express.

Polling provides a baseline observation mechanism. While A2A also supports streaming and push notifications for real-time updates, polling guarantees eventual visibility of results in any network environment.

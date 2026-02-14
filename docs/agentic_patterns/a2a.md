# A2A (Agent-to-Agent Protocol)

A2A standardizes how autonomous agents discover, communicate with, and delegate work to other agents over HTTP. While MCP connects agents to tools and data, A2A connects agents to other agents as opaque, autonomous peers. A common composition is A2A for delegation (coordinator to specialist) and MCP for tool-use (specialist to databases, file systems, sandboxes).

The library provides A2A client infrastructure, a coordinator factory, delegation tools, authentication middleware, skill conversion utilities, and a mock server for testing. All A2A infrastructure lives in `agentic_patterns.core.a2a`. A2A server implementations (thin wrappers over agents + MCP) live in `agentic_patterns.a2a.*`.


## Exposing an Agent as an A2A Server

Any PydanticAI agent can be exposed as an A2A server using `to_a2a()`. This creates an ASGI application that handles JSON-RPC requests for task creation, message sending, and task retrieval. It also serves the Agent Card at `/.well-known/agent-card.json`.

```python
from agentic_patterns.core.agents import get_agent

def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

agent = get_agent(tools=[add])
app = agent.to_a2a()
```

Run with uvicorn:

```bash
uvicorn mymodule:app --host 0.0.0.0 --port 8000
```

### Declaring skills

Skills appear in the Agent Card and let clients understand what the agent can do before sending any task. Use `tool_to_skill()` to convert tool functions into A2A Skill objects:

```python
from agentic_patterns.core.a2a import tool_to_skill

tools = [add, sub, mul]
skills = [tool_to_skill(f) for f in tools]

app = agent.to_a2a(
    name="Arithmetic",
    description="Basic arithmetic operations",
    skills=skills
)
```

`tool_to_skill()` extracts the function name as the skill ID/name and the docstring as the description.

### Building skills from multiple sources

A2A servers often compose skills from several sources. The library provides conversion functions for each:

```python
from agentic_patterns.core.a2a import (
    tool_to_skill,              # local function -> Skill
    mcp_to_skills_sync,         # MCP server tools -> list[Skill]
    card_to_skills,             # A2A sub-agent card -> list[Skill]
    skill_metadata_to_a2a_skill # SKILL.md metadata -> Skill
)
```

`mcp_to_skills_sync()` connects to an MCP server by config name, lists its tools, and converts each to a Skill. It is safe to call even if an event loop is already running (spawns a thread if needed). The async variant is `mcp_to_skills()`.

### Authentication middleware

A2A servers should use `AuthSessionMiddleware` to extract JWT Bearer tokens from incoming requests and set the user session context:

```python
from agentic_patterns.core.a2a import AuthSessionMiddleware

app = agent.to_a2a(name="MyAgent", skills=skills)
app.add_middleware(AuthSessionMiddleware)
```

The middleware reads `sub` (user ID) and `session_id` from JWT claims and calls `set_user_session_from_token()`, propagating identity into contextvars for downstream code (workspace paths, compliance checks, etc.).

### Server implementation pattern

All A2A servers in `agentic_patterns/a2a/` follow the same structure:

```
agentic_patterns/a2a/nl2sql/
    server.py       # Load prompt, build skills, create agent, expose via to_a2a()
```

Each server: loads a system prompt, connects to MCP servers via `get_mcp_client()`, builds the skills list via `mcp_to_skills_sync()`, creates the agent with `get_agent(toolsets=...)`, and exposes it with `agent.to_a2a()` plus `AuthSessionMiddleware`. Servers are started with uvicorn.


## Calling Remote A2A Agents

### Client configuration

A2A client settings are defined in `config.yaml` under `a2a.clients` and loaded via `load_a2a_settings()`. Environment variables are expanded with `${VAR}` syntax.

```yaml
a2a:
  clients:
    nl2sql:
      url: http://localhost:8002
      timeout: 300
      poll_interval: 1.0
      max_retries: 3
      retry_delay: 1.0
      bearer_token: ${A2A_TOKEN}

    data_analysis:
      url: http://localhost:8201
```

### Creating clients

```python
from agentic_patterns.core.a2a import A2AClientExtended, A2AClientConfig, get_a2a_client

# From config.yaml by name
client = get_a2a_client("nl2sql")

# From explicit config
client = A2AClientExtended(A2AClientConfig(url="http://localhost:8002", timeout=300))
```

### Agent discovery

Before sending work, a client can fetch the Agent Card to understand what the agent offers:

```python
card = await client.get_agent_card()
# card contains: name, description, skills, capabilities, authentication
```

### Sending tasks and observing results

`send_and_observe()` encapsulates the complete send-then-poll loop. It returns a `(TaskStatus, task)` tuple:

```python
from agentic_patterns.core.a2a import TaskStatus

status, task = await client.send_and_observe("Reconcile invoice #4812")

match status:
    case TaskStatus.COMPLETED:
        from agentic_patterns.core.a2a import extract_text
        result = extract_text(task)
    case TaskStatus.INPUT_REQUIRED:
        from agentic_patterns.core.a2a import extract_question
        question = extract_question(task)
        # Continue the conversation on the same task
        status, task = await client.send_and_observe(
            "The answer is yes",
            task_id=task['id']
        )
    case TaskStatus.FAILED:
        ...
    case TaskStatus.TIMEOUT:
        ...  # client auto-cancels the remote task on timeout
    case TaskStatus.CANCELLED:
        ...
```

`TaskStatus` values: `COMPLETED`, `FAILED`, `INPUT_REQUIRED`, `CANCELLED`, `TIMEOUT`. The first four map to A2A protocol states. `TIMEOUT` is a client-side addition -- when the configured deadline is exceeded, the client cancels the remote task before returning.

### Client resilience

`A2AClientExtended` provides production-ready behavior on top of the base `fasta2a.A2AClient`:

- Retry with exponential backoff on transient `ConnectionError` and `TimeoutError` (configurable `max_retries` and `retry_delay`).
- Timeout with auto-cancel. A configurable `timeout` bounds total wait time. On expiration, the client cancels the remote task.
- Cooperative cancellation via an `is_cancelled` callback checked on every poll cycle:

```python
status, task = await client.send_and_observe(
    "Long computation",
    is_cancelled=lambda: user_pressed_cancel
)
```


## Coordinator Pattern

The coordinator pattern is a local agent that routes tasks to specialized remote A2A agents. The coordinator fetches Agent Cards, understands capabilities, and delegates via delegation tools.

### Quick setup with `create_coordinator()`

`create_coordinator()` automates the full setup: fetches agent cards, creates delegation tools, and builds the system prompt.

```python
from agentic_patterns.core.a2a import create_coordinator, A2AClientConfig

coordinator = await create_coordinator(
    clients=[
        A2AClientConfig(url="http://localhost:8000"),
        A2AClientConfig(url="http://localhost:8001"),
    ]
)

result = await coordinator.run("What is the area of a circle with radius 5?")
```

You can also pass `A2AClientExtended` instances or a custom `system_prompt` (appended to the auto-generated prompt describing available agents). An `is_cancelled` callback propagates cancellation to all delegation tools.

### Manual coordinator construction

For full control over the coordinator setup, build the pieces individually. `create_a2a_tool()` wraps an A2A client and agent card into a PydanticAI tool that handles the delegation lifecycle:

```python
from agentic_patterns.core.a2a import (
    A2AClientExtended, A2AClientConfig,
    create_a2a_tool, build_coordinator_prompt
)
from agentic_patterns.core.agents import get_agent

clients = [
    A2AClientExtended(A2AClientConfig(url="http://localhost:8000")),
    A2AClientExtended(A2AClientConfig(url="http://localhost:8001")),
]

cards = [await c.get_agent_card() for c in clients]
tools = [create_a2a_tool(c, card) for c, card in zip(clients, cards)]
prompt = build_coordinator_prompt(cards)

coordinator = get_agent(tools=tools, instructions=prompt)
```

`create_a2a_tool()` produces a tool function `delegate(ctx, prompt, task_id=None)` that returns formatted status strings: `[COMPLETED] result text`, `[INPUT_REQUIRED:task_id=xyz] question`, `[FAILED] error`, `[CANCELLED]`, `[TIMEOUT]`. The status prefix lets the LLM understand the outcome and decide next steps (e.g., answering a follow-up question for `INPUT_REQUIRED`).

`build_coordinator_prompt()` generates a system prompt section listing each agent's name, description, and skills.


## Testing

### MockA2AServer

`MockA2AServer` implements the A2A JSON-RPC interface with configurable responses, allowing deterministic testing without running LLM-backed agents.

```python
from agentic_patterns.core.a2a.mock import MockA2AServer

mock = MockA2AServer(name="Arithmetic", description="Does math")

# Exact prompt match
mock.on_prompt("add 2 and 3", result="5")

# Regex pattern match
mock.on_pattern(r"subtract \d+ from \d+", result="0")

# Default fallback
mock.set_default(result="unknown operation")

# Delayed response (returns "working" for N polls, then completes)
mock.on_prompt_delayed("factorial(100)", polls=3, result="9332621544...")

# Error responses
mock.on_prompt("crash", error="Division by zero")

# Input-required responses
mock.on_prompt("need clarification", input_required="Which account?")

app = mock.to_app()  # FastAPI instance for test clients
```

After a test run, inspect what was received:

```python
assert "add 2 and 3" in mock.received_prompts
assert task_id in mock.cancelled_task_ids  # if cancellation was tested
```

Configuration methods return `self` for chaining:

```python
mock = (MockA2AServer(name="Agent")
    .on_prompt("hello", result="hi")
    .on_pattern(r"sum.*", result="42")
    .set_default(result="unknown"))
```


## Utilities

Helper functions in `agentic_patterns.core.a2a`:

`create_message(text, message_id=None)` creates an A2A user message dict with a generated `message_id`.

`extract_text(task)` joins text from all task artifact parts into a single string. Returns `None` if no text artifacts.

`extract_question(task)` extracts the question text from an `input-required` task status message.

`card_to_prompt(card)` formats an agent card as a markdown string for inclusion in system prompts (name, description, skills list).

`slugify(name)` converts a name to a valid Python identifier (lowercase, non-alphanumeric replaced with underscores).


## API Reference

### `agentic_patterns.core.a2a`

| Name | Kind | Description |
|---|---|---|
| `A2AClientExtended(config)` | Class | A2A client with retry, timeout, cancellation |
| `A2AClientConfig` | Pydantic model | Client config (url, timeout, poll_interval, max_retries, retry_delay, bearer_token) |
| `TaskStatus` | Enum | Task outcome: COMPLETED, FAILED, INPUT_REQUIRED, CANCELLED, TIMEOUT |
| `get_a2a_client(name)` | Function | Create client from config.yaml by name |
| `create_coordinator(clients, system_prompt, is_cancelled)` | Function | Create coordinator agent with delegation tools |
| `create_a2a_tool(client, card, name, is_cancelled)` | Function | Create delegation tool from client + agent card |
| `build_coordinator_prompt(cards)` | Function | Build system prompt from agent cards |
| `AuthSessionMiddleware` | Middleware | JWT Bearer token to user session bridge |
| `tool_to_skill(func)` | Function | Convert tool function to fasta2a Skill |
| `card_to_skills(card)` | Function | Extract skills from agent card |
| `mcp_to_skills(config_name)` | Function | MCP server tools to skills (async) |
| `mcp_to_skills_sync(config_name)` | Function | MCP server tools to skills (sync) |
| `skill_metadata_to_a2a_skill(meta)` | Function | SKILL.md metadata to fasta2a Skill |
| `create_message(text, message_id)` | Function | Create A2A user message dict |
| `extract_text(task)` | Function | Extract text from task artifacts |
| `extract_question(task)` | Function | Extract question from input-required status |
| `card_to_prompt(card)` | Function | Format agent card as prompt markdown |
| `slugify(name)` | Function | Name to valid Python identifier |
| `MockA2AServer` | Class | Mock A2A server for testing |
| `A2ASettings` | Pydantic model | Container for A2A client configs |
| `load_a2a_settings(config_path)` | Function | Load A2A settings from YAML |


## Examples

See the files in `agentic_patterns/examples/a2a/`:

- `example_a2a_server.py` -- minimal A2A server with arithmetic tools
- `example_a2a_server_1.py` -- A2A server with skills (arithmetic)
- `example_a2a_server_2.py` -- A2A server with skills (area calculations)
- `example_a2a_client.ipynb` -- basic client: discover, send task, poll, extract result
- `example_a2a_coordinator.ipynb` -- coordinator agent routing to multiple specialists

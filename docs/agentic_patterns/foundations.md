# Foundations

The foundations module (`agentic_patterns.core.agents`) provides the minimal surface for creating and running agents. It wraps PydanticAI's `Agent` with YAML-based model configuration so you never hardcode provider credentials or model names in Python code.

## Configuration

All model configuration lives in `config.yaml` at the project root. Each entry under `models:` defines a named configuration with a `model_family` that selects the provider, a `model_name`, credentials, and optional settings.

```yaml
models:
  default:
    model_family: openrouter
    model_name: anthropic/claude-sonnet-4.5
    api_key: ${OPENROUTER_API_KEY}
    api_url: https://openrouter.ai/api/v1
    timeout: 120

  fast:
    model_family: openai
    model_name: gpt-4o-mini
    api_key: ${OPENAI_API_KEY}
    timeout: 60

  local:
    model_family: ollama
    model_name: llama3
    url: http://localhost:11434/v1
    timeout: 300
```

Supported model families and their required fields:

| Family | Required fields | Notes |
|---|---|---|
| `azure` | `model_name`, `api_key`, `endpoint`, `api_version` | Azure OpenAI Service |
| `bedrock` | `model_name` | AWS credentials via profile or env vars. Optional `claude_sonnet_1m_tokens: true` for 1M context. |
| `ollama` | `model_name`, `url` | Local models via Ollama |
| `openai` | `model_name`, `api_key` | Direct OpenAI API |
| `openrouter` | `model_name`, `api_key` | Multi-provider gateway. Optional `api_url` (defaults to `https://openrouter.ai/api/v1`). |

All families support `timeout` (default 120 seconds) and `parallel_tool_calls` (optional boolean).

## get_agent

Creates a PydanticAI `Agent` from configuration.

```python
from agentic_patterns.core.agents import get_agent

# Uses the "default" entry in config.yaml
agent = get_agent()

# Uses a named configuration
agent = get_agent(config_name="fast")

# With a system prompt
agent = get_agent(system_prompt="Translate into French")

# With tools
agent = get_agent(tools=[my_tool_fn])
```

**Signature:**

```python
def get_agent(
    model=None,
    *,
    config_name: str = "default",
    config_path: Path | str | None = None,
    model_settings=None,
    http_client=None,
    history_compactor=None,
    **kwargs,
) -> Agent
```

When `model` is `None` (the default), the function reads `config.yaml`, looks up the entry named `config_name`, creates the appropriate PydanticAI model instance, and passes it to `Agent()`. Any extra keyword arguments (`system_prompt`, `tools`, `toolsets`, `output_type`, `deps_type`, `retries`, etc.) are forwarded directly to PydanticAI's `Agent` constructor.

If you pass a pre-configured `model` instance, configuration lookup is skipped entirely.

## run_agent

Executes an agent with a prompt and returns the run result plus execution nodes.

```python
from agentic_patterns.core.agents import get_agent, run_agent

agent = get_agent()
agent_run, nodes = await run_agent(agent, "Translate to French: I like coffee.")

print(agent_run.result.output)  # "J'aime le cafe."
```

**Signature:**

```python
async def run_agent(
    agent: Agent,
    prompt: str | list[str],
    message_history: Sequence[ModelMessage] | None = None,
    usage_limits: UsageLimits | None = None,
    verbose: bool = False,
    catch_exceptions: bool = False,
    ctx: Context | None = None,
) -> tuple[AgentRun | None, list[AgentNode]]
```

The function uses PydanticAI's async iteration interface (`agent.iter()`) to stream execution step by step. Each step is a graph node -- `UserPromptNode`, `ModelRequestNode`, or `CallToolsNode` -- collected into the returned `nodes` list. This provides full visibility into what the agent did: which tools it called, what the model responded at each step, and how the conversation flowed.

When `verbose=True`, each node is printed via `rich`. When a FastMCP `ctx` is provided (i.e., running inside an MCP server), debug messages are sent to the MCP client.

If `catch_exceptions=True`, errors are swallowed and `agent_run` is returned as `None`. The default (`False`) lets exceptions propagate.

## Multi-turn conversations

LLMs are stateless. To maintain context across turns, pass the message history from the previous turn into the next call.

```python
from agentic_patterns.core.agents import get_agent, run_agent
from agentic_patterns.core.agents.utils import nodes_to_message_history

agent = get_agent()

# Turn 1
agent_run_1, nodes_1 = await run_agent(agent, "Translate to French: I like coffee.")

# Extract history
history = nodes_to_message_history(nodes_1)

# Turn 2 -- agent knows "it" refers to coffee
agent_run_2, nodes_2 = await run_agent(agent, "How do you like it?", message_history=history)
```

### nodes_to_message_history

Converts the list of execution nodes from `run_agent()` into the `Sequence[ModelMessage]` format that `run_agent()` accepts as `message_history`.

```python
def nodes_to_message_history(
    nodes: list,
    remove_last_call_tool: bool = True,
) -> Sequence[ModelMessage]
```

By default it strips the trailing `CallToolsNode` from the history (if present) because tool call/return pairs at the end of a turn are internal to that turn's execution and should not leak into the next turn's context.

### Chaining turns

Each turn uses the history from the immediately preceding turn:

```python
run_1, nodes_1 = await run_agent(agent, prompt_1)
history_1 = nodes_to_message_history(nodes_1)

run_2, nodes_2 = await run_agent(agent, prompt_2, message_history=history_1)
history_2 = nodes_to_message_history(nodes_2)

run_3, nodes_3 = await run_agent(agent, prompt_3, message_history=history_2)
```

## System prompts

Pass `system_prompt` to `get_agent()` to separate persistent instructions from per-request content. The system prompt is included in every API call the agent makes.

```python
agent = get_agent(system_prompt="Translate into French")

# Only the content varies per call
run_1, _ = await run_agent(agent, "I like coffee.")
run_2, _ = await run_agent(agent, "The weather is nice.")
```

Use a system prompt when the agent has a persistent role or behavior. Use the user prompt for the specific input to process. Combine with `message_history` for multi-turn conversations where both role and context are preserved.

## Environment & Project Configuration

The configuration module (`agentic_patterns.core.config`) handles environment loading, path resolution, and project-level constants. It is designed to work both when the library runs standalone and when it is installed as a package inside another project.

### Environment loading

At import time, `config.py` calls `load_env_variables()` which searches for a `.env` file in multiple locations: the current working directory and its parents, the project root (determined by the main script's location), and the config file's own directory. The first `.env` found wins. If no `.env` file exists, the process exits with code 1.

```python
from agentic_patterns.core.config.env import get_variable_env

# Read an environment variable with a default
api_key = get_variable_env("MY_API_KEY", default="fallback")

# Require a variable to be set (raises ValueError if missing)
db_url = get_variable_env("DATABASE_URL", allow_empty=False)
```

### Path constants

All paths are `Path` objects. Most can be overridden via environment variables; otherwise they resolve relative to `MAIN_PROJECT_DIR` (the parent directory of the found `.env` file).

| Constant | Env override | Default |
|---|---|---|
| `AGENTIC_PATTERNS_PROJECT_DIR` | -- | The `agentic_patterns/` package directory |
| `MAIN_PROJECT_DIR` | -- | Parent of the `.env` file |
| `SCRIPTS_DIR` | -- | `MAIN_PROJECT_DIR / "scripts"` |
| `DATA_DIR` | `DATA_DIR` | `MAIN_PROJECT_DIR / "data"` |
| `DATA_DB_DIR` | `DATA_DB_DIR` | `DATA_DIR / "db"` |
| `PROMPTS_DIR` | `PROMPTS_DIR` | `MAIN_PROJECT_DIR / "prompts"` |
| `WORKSPACE_DIR` | `WORKSPACE_DIR` | `DATA_DIR / "workspaces"` |
| `PRIVATE_DATA_DIR` | `PRIVATE_DATA_DIR` | `DATA_DIR / "private_data"` |
| `FEEDBACK_DIR` | `FEEDBACK_DIR` | `DATA_DIR / "feedback"` |
| `SKILLS_DIR` | `SKILLS_DIR` | `DATA_DIR / "skills"` |
| `LOGS_DIR` | -- | `MAIN_PROJECT_DIR / "logs"` |
| `USER_DATABASE_FILE` | `USER_DATABASE_FILE` | `MAIN_PROJECT_DIR / "users.json"` |
| `CHAINLIT_DATA_LAYER_DB` | `CHAINLIT_DATA_LAYER_DB` | `DATA_DIR / "chainlit.db"` |
| `CHAINLIT_FILE_STORAGE_DIR` | `CHAINLIT_FILE_STORAGE_DIR` | `DATA_DIR / "chainlit_files"` |
| `CHAINLIT_SCHEMA_FILE` | `CHAINLIT_SCHEMA_FILE` | `DATA_DIR / "sql" / "chainlit_data_layer.sql"` |

### Session defaults

Two constants provide default values for user/session identity, used by notebooks and development environments where no explicit session is established:

```python
from agentic_patterns.core.config.config import DEFAULT_USER_ID, DEFAULT_SESSION_ID

DEFAULT_USER_ID   # "default_user"
DEFAULT_SESSION_ID  # "default_session"
```

### Workspace and JWT constants

`SANDBOX_PREFIX` (`"/workspace"`) is the path prefix agents see for sandbox paths. JWT constants (`JWT_SECRET`, `JWT_ALGORITHM`) are loaded from environment variables with development defaults.


## Authentication

`agentic_patterns.core.auth` provides JWT token generation and validation for propagating user identity across layers (HTTP requests, MCP servers, A2A calls).

```python
from agentic_patterns.core.auth import create_token, decode_token

token = create_token(user_id="alice", session_id="sess-42", expires_in=3600)
claims = decode_token(token)
# claims["sub"] == "alice", claims["session_id"] == "sess-42"
```

`create_token(user_id, session_id, expires_in=3600)` encodes a JWT with `sub` (user ID), `session_id`, `iat`, and `exp` claims using the HS256 algorithm and the secret from `JWT_SECRET`.

`decode_token(token)` validates the signature and expiration, returning the claims dict. Raises `jwt.InvalidTokenError` on failure.


## User Session

`agentic_patterns.core.user_session` manages request-scoped user/session identity using Python's `contextvars`. This avoids threading identity parameters through every function call.

```python
from agentic_patterns.core.user_session import set_user_session, get_user_id, get_session_id

# At request boundary (middleware, MCP handler, etc.)
set_user_session("alice", "sess-42")

# Anywhere downstream
get_user_id()      # "alice"
get_session_id()   # "sess-42"
```

When no session is set (e.g., in notebooks), the contextvars return `DEFAULT_USER_ID` and `DEFAULT_SESSION_ID` from the config module.

`set_user_session_from_token(token)` is a convenience that decodes a JWT and calls `set_user_session()` with the extracted claims. Used by A2A servers and non-FastMCP entry points that receive raw token strings.


## Examples

See the notebooks in `agentic_patterns/examples/foundations/`:

- `example_translate_basic.ipynb` -- single-turn agent with everything in the user prompt
- `example_translate_system_prompt.ipynb` -- separating system prompt from user prompt
- `example_multi_turn.ipynb` -- multi-turn conversation with message history

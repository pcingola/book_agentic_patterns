# User Interface

The UI module provides two integration paths for exposing agents to users: Chainlit (a ready-made chat framework) and AG-UI (a streaming event protocol). It also provides authentication, feedback persistence, and helpers for file uploads.

## Authentication

`agentic_patterns.core.ui.auth` provides a JSON-backed user database with SHA-256 password hashing.

```python
from agentic_patterns.core.ui.auth import UserDatabase, generate_password
from agentic_patterns.core.config.config import USER_DATABASE_FILE

db = UserDatabase(USER_DATABASE_FILE)            # db_path: Path is required
db.add_user("alice", "password123")              # creates user with hashed password
db.add_user("bob", "secret", role="admin")       # optional role
user = db.authenticate("alice", "password123")   # returns User or None
db.change_password("alice", "password123", "new_password")  # requires old_password
db.get_user("bob")                               # returns User or None
db.delete_user("alice")
users = db.list_users()                          # returns list[str] (usernames)
password = generate_password()                   # random 16-char password
```

The `User` model has fields `username`, `password_hash`, and `role` (defaults to `"user"`).

The `manage-users` CLI (registered as a console script in pyproject.toml) provides user management from the terminal:

```bash
manage-users add alice -p password123
manage-users add bob -r admin          # auto-generates password if -p omitted
manage-users list
manage-users passwd alice -p new_pass
manage-users delete alice
```

## Chainlit Integration

`agentic_patterns.core.ui.chainlit` provides lifecycle handlers, SQLite persistence, and filesystem storage for Chainlit applications.

### Handler Registration

`register_all()` sets up authentication, data layer, and chat resume in one call:

```python
from agentic_patterns.core.ui.chainlit.handlers import register_all, setup_user_session

register_all()
```

This registers three Chainlit callbacks. `@cl.password_auth_callback` authenticates against the JSON user database. `@cl.data_layer` configures SQLite storage for chat threads. `@cl.on_chat_resume` restores conversation history when a user returns to a previous thread.

Individual registration functions are also available: `register_auth_callback()`, `register_data_layer()`, `register_chat_resume()`.

### Session Setup

`setup_user_session()` bridges Chainlit's user context into the core `user_session` contextvars so that workspace, connectors, and compliance modules see the correct identity:

```python
import chainlit as cl
from agentic_patterns.core.ui.chainlit.handlers import setup_user_session

@cl.on_chat_start
async def on_chat_start():
    setup_user_session()  # sets user_id and session_id from Chainlit context
    # ... create agent, initialize session state
```

Call `setup_user_session()` at the start of `@cl.on_chat_start` and `@cl.on_message` handlers.

### Data Layer

`get_sqlite_data_layer()` returns a SQLAlchemy-backed data layer for Chainlit thread persistence. `init_db()` creates the schema tables on first run. The database path defaults to `CHAINLIT_DATA_LAYER_DB`. File attachments are stored on the local filesystem via `FilesystemStorageClient` (at `CHAINLIT_FILE_STORAGE_DIR`).

### Tool Visualization

Chainlit's `@cl.step(type="tool")` decorator makes tool calls visible in the chat UI as collapsible steps. Apply it to functions that are also registered as agent tools:

```python
@cl.step(type="tool")
async def search(query: str) -> str:
    """Search for documents."""
    return do_search(query)

agent = get_agent(tools=[search])
```

When the agent calls the tool, the step appears in the Chainlit interface showing the tool name and result.

## AG-UI Integration

`agentic_patterns.core.ui.agui` provides factory functions and event helpers for exposing agents via the AG-UI protocol.

### App Creation

`create_agui_app()` creates an AG-UI application from model configuration:

```python
from agentic_patterns.core.ui.agui.app import create_agui_app

app = create_agui_app(
    instructions="You are a helpful assistant.",
    tools=[my_tool],
)
```

It accepts the same parameters as `get_agent()` (config name, instructions, tools, `state_type`) and wraps the resulting agent in PydanticAI's `AGUIApp`. For wrapping an existing agent, use `create_agui_app_from_agent(agent, state=None)`.

The returned `app` is an ASGI application. Run it with uvicorn:

```bash
uvicorn mymodule:app --reload
```

### State Management

AG-UI supports shared state between frontend and agent via `StateDeps`. Define a Pydantic model for the state, wrap it in `StateDeps`, and tools receive it through `RunContext`:

```python
from pydantic import BaseModel
from pydantic_ai import RunContext
from pydantic_ai.ui.ag_ui import StateDeps

class AppState(BaseModel):
    items: list[str] = []

async def add_item(ctx: RunContext[StateDeps[AppState]], item: str) -> str:
    ctx.deps.state.items.append(item)
    return f"Added {item}"

app = create_agui_app(
    state_type=AppState,
    tools=[add_item],
)
```

PydanticAI's AG-UI adapter automatically serializes state changes as `StateSnapshotEvent` in the SSE stream.

### Event Helpers

`agentic_patterns.core.ui.agui.events` provides helpers for constructing `ToolReturn` values with events:

```python
from agentic_patterns.core.ui.agui.events import tool_return_with_state

async def my_tool(ctx: RunContext[StateDeps[AppState]], value: str) -> ToolReturn:
    ctx.deps.state.items.append(value)
    return tool_return_with_state(
        return_value=f"Added {value}",
        state=ctx.deps.state,
        custom_events=[("item_added", {"value": value})],
    )
```

`tool_return_with_state()` builds a `ToolReturn` carrying the return value (what the LLM sees), a `StateSnapshotEvent` (what the frontend sees to update its state), and optional `CustomEvent` entries for domain-specific signals.

Lower-level helpers `state_snapshot(state)` and `custom_event(name, value)` create individual events.

### Side-Channel Endpoints

AG-UI is a text-streaming protocol. Binary uploads, feedback, and other non-conversational interactions are handled as REST endpoints on the same Starlette app via the `routes` parameter:

```python
from starlette.routing import Route
from pydantic_ai.ui.ag_ui.app import AGUIApp

app = AGUIApp(
    agent,
    routes=[
        Route("/upload", upload_handler, methods=["POST"]),
        Route("/feedback", feedback_handler, methods=["POST"]),
    ],
)
```

## Feedback

`agentic_patterns.core.feedback` provides feedback persistence per user session. Feedback entries are stored as JSON at `FEEDBACK_DIR / user_id / session_id / feedback.json`.

```python
from agentic_patterns.core.feedback import FeedbackType, add_feedback, get_feedback

add_feedback(FeedbackType.THUMBS_UP, comment="Great answer")
add_feedback(FeedbackType.THUMBS_DOWN, comment="Wrong result")

# With explicit user/session (otherwise reads from contextvars)
add_feedback(FeedbackType.COMMENT, comment="Needs more detail", user_id="alice", session_id="sess-1")

session_fb = get_feedback(user_id="alice", session_id="sess-1")
for entry in session_fb.entries:
    print(entry.feedback_type, entry.comment, entry.timestamp)
```

`FeedbackType` has four values: `THUMBS_UP`, `THUMBS_DOWN`, `ERROR_REPORT`, `COMMENT`.

Conversation history can also be persisted per session via `save_session_history()` and `load_session_history()`, which serialize PydanticAI `ModelMessage` lists to `history.json` in the same directory.

## File Uploads

File uploads follow a save-summarize-tag pattern that keeps large files out of the context window while giving the agent enough information to work with them.

1. **Save** the file to the workspace via `write_to_workspace_async()`. The workspace persists across turns and is accessible to tools and connectors.

2. **Tag** the session as containing private data via `PrivateData().add_private_dataset()`. This activates compliance guardrails that block outbound tools for the rest of the session.

3. **Summarize** the file via `read_file_as_string()` from the context reader. The reader detects the file type and produces a compact, type-aware summary within token limits (headers + sample rows for CSV, truncated structure for JSON, extracted text for documents).

The summary and workspace path are appended to the user's message so the agent receives both a preview and a stable reference:

```python
from agentic_patterns.core.workspace import write_to_workspace_async
from agentic_patterns.core.compliance.private_data import PrivateData, DataSensitivity
from agentic_patterns.core.context.reader import read_file_as_string

async def handle_upload(filename: str, content: bytes) -> tuple[str, str]:
    workspace_path = f"/workspace/uploads/{filename}"
    await write_to_workspace_async(workspace_path, content)
    PrivateData().add_private_dataset(f"upload:{filename}", DataSensitivity.CONFIDENTIAL)
    summary = read_file_as_string(host_path)
    return workspace_path, summary
```

The agent can then use `FileConnector`, `CsvConnector`, or other tools to access the full file content on demand.

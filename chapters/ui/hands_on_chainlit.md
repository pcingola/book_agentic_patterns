## Hands-On: Chainlit

This hands-on demonstrates how to wrap a PydanticAI agent in a Chainlit web interface. The examples progress from a minimal echo application to a full agent with authentication, conversation persistence, and tool visualization. The code is in `agentic_patterns/examples/ui/`: `example_chainlit_app_v1.py`, `example_chainlit_app_v2.py`, and `example_chainlit_app_v3.py`.

### Running Chainlit Applications

Chainlit applications are Python files run with the `chainlit` command:

```bash
cd agentic_patterns/examples/ui
chainlit run example_chainlit_app_v1.py
```

This starts a local web server and opens the chat interface in your browser. The application reloads automatically when you save changes to the file.

### Echo Application

The first example (`example_chainlit_app_v1.py`) shows the minimal Chainlit structure:

```python
import chainlit as cl

@cl.on_message
async def on_message(message: cl.Message):
    user_message = message.content
    msg = cl.Message(content=f"Echo:\n{user_message}")
    await msg.send()
```

The `@cl.on_message` decorator registers a handler that Chainlit calls whenever the user sends a message. The handler receives a `Message` object containing the user's input. To respond, create a new `Message` with the desired content and call `send()`.

This pattern separates the UI framework from the application logic. Chainlit handles the websocket communication, message rendering, and session management. The developer provides handlers that process messages and produce responses.

### Adding an Agent

The second example (`example_chainlit_app_v2.py`) integrates a PydanticAI agent:

```python
import chainlit as cl
from agentic_patterns.core.agents import get_agent, run_agent

agent = get_agent()

@cl.on_message
async def on_message(message: cl.Message):
    user_message = message.content
    ret, nodes = await run_agent(agent, user_message)
    output = ret.result.output
    msg = cl.Message(content=output if output else "No response from the agent.")
    await msg.send()
```

The agent is created at module level and reused across all requests. Each message is passed to `run_agent`, which returns the agent's response. This version has no memory: each message is processed independently without context from previous turns.

Creating the agent at module level works for stateless agents. The agent itself doesn't store conversation history; it processes each input fresh. This is sufficient for single-turn interactions like answering questions or performing one-shot tasks.

### Full Application with Authentication and Persistence

The third example (`example_chainlit_app_v3.py`) adds authentication, conversation persistence, chat resume, and starters. These features require setup before running.

#### Setup: User Database

Create users with the CLI:

```bash
manage-users add admin -p your_password -r admin
manage-users add alice -p her_password
manage-users list
```

The `manage-users` command manages a JSON-based user database at `users.json`. Each user has a username, hashed password, and role.

#### Setup: JWT Secret

Chainlit requires a JWT secret for authentication sessions:

```bash
chainlit create-secret
```

Add the output to your `.env` file:

```
CHAINLIT_AUTH_SECRET=your_generated_secret_here
```

#### Setup: Chainlit Config

Enable authentication in `.chainlit/config.toml`:

```toml
[project]
enable_auth = true
```

#### Registering Handlers

The application registers authentication, data layer, and chat resume handlers at startup:

```python
from agentic_patterns.core.ui.chainlit.handlers import register_all, setup_user_session

register_all()
```

This single call sets up three Chainlit callbacks. The `@cl.password_auth_callback` authenticates users against the JSON database. The `@cl.data_layer` configures SQLite storage for chat threads. The `@cl.on_chat_resume` restores conversation history when users return to previous chats.

#### User and Session Tracking

The application tracks the authenticated user and session for downstream code:

```python
@cl.on_chat_start
async def on_chat_start():
    setup_user_session()
    agent = get_agent(tools=[add, sub, mul, div])
    cl.user_session.set(AGENT, agent)
    cl.user_session.set(HISTORY, [])
```

The `setup_user_session()` function extracts the user identifier and thread ID from Chainlit's context and stores them in context variables. This allows workspace operations, logging, and other downstream code to access user/session information without passing it explicitly through every function call.

#### Starters

Starters provide quick-start message suggestions shown to users on new chats:

```python
@cl.set_starters
async def set_starters(user: str | None, language: str | None) -> list[cl.Starter]:
    return [
        cl.Starter(label="Add numbers", message="What is 42 + 17?"),
        cl.Starter(label="Subtract numbers", message="What is 100 - 37?"),
        cl.Starter(label="Calculate", message="Add 25 and 75, then subtract 50 from the result"),
    ]
```

Chainlit displays these as clickable buttons in the chat interface. Clicking a starter sends its message as if the user had typed it. The function receives the authenticated user and browser language, allowing dynamic starters based on user preferences or roles.

#### Chat Resume

When a user returns to a previous chat thread, the `@cl.on_chat_resume` handler (registered by `register_all()`) restores the conversation history:

```python
@cl.on_chat_resume
async def on_chat_resume(thread):
    steps = thread['steps']
    history = []
    for step in steps:
        if step['type'] in ('user_message', 'assistant_message'):
            message = step['input'] + "\n" + step['output']
            history.append(message.strip())
    cl.user_session.set(HISTORY, history)
```

The data layer stores all chat threads in SQLite. When a user selects a previous thread from the sidebar, Chainlit calls this handler with the thread data. The handler reconstructs the history list from the stored steps so the agent has context from the previous conversation.

### Session State and Conversation History

The `@cl.on_chat_start` decorator registers a handler called once when a new chat session begins. This is where per-session initialization belongs: creating agents, loading user preferences, or establishing connections.

`cl.user_session` provides key-value storage scoped to the current chat session. Different browser tabs or users get isolated sessions. Storing the agent and history here ensures each session has its own state.

The message handler retrieves session state and maintains history:

```python
@cl.on_message
async def on_message(message: cl.Message):
    setup_user_session()
    agent = cl.user_session.get(AGENT)
    history = cl.user_session.get(HISTORY)
    user_message = message.content

    messages = list(history) if history else []
    messages.append(user_message)

    ret, nodes = await run_agent(agent, messages)
    agent_response = ret.result.output

    msg = cl.Message(content=agent_response if agent_response else "No response from the agent.")
    await msg.send()

    messages.append(agent_response)
    cl.user_session.set(HISTORY, messages)
```

The history accumulates all messages exchanged in the session. Each turn appends the user message, runs the agent with the full history, appends the agent's response, and stores the updated history. This gives the agent context from previous turns, enabling multi-turn conversations where the agent can reference earlier exchanges.

### Tool Visualization with Steps

The third example also demonstrates Chainlit's step visualization for tool calls:

```python
@cl.step(type="tool")
async def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@cl.step(type="tool")
async def sub(a: int, b: int) -> int:
    """Subtract two numbers"""
    return a - b

@cl.step(type="tool")
async def mul(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b

@cl.step(type="tool")
async def div(a: int, b: int) -> int:
    """Divide two numbers, round to nearest integer"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return int(a / b)
```

The `@cl.step` decorator wraps the function so that each invocation appears as a collapsible step in the Chainlit UI. When the agent calls these tools during execution, users see the tool name, and can expand the step to see the result. This provides visibility into the agent's intermediate actions without requiring custom logging or tracing infrastructure.

The `type="tool"` parameter categorizes the step for visual styling. Other types include `"llm"` for model calls and `"run"` for general execution blocks.

These decorated functions are passed directly to the agent:

```python
agent = get_agent(tools=[add, sub, mul, div])
```

When the agent decides to call any of these tools, the Chainlit context is active (since the call originates from within the `@cl.on_message` handler), so the step visualization works automatically. The agent framework calls the tool, the decorator creates the step, and the result flows back to the model.

### File Upload Support

The third example handles file uploads following the save-summarize-tag pattern described in the [File Uploads](./file_uploads.md) section. Chainlit provides uploaded files through `message.elements`, where each file object has a `name` (original filename) and a `path` (temporary location on disk). The handler saves each file to the workspace, tags the session as private, and generates a summarized representation for the agent's context:

```python
async def process_uploaded_files(files: list) -> str:
    if not files:
        return ""

    file_contexts = []
    for file in files:
        filename = Path(file.name).name
        workspace_path = f"/workspace/uploads/{filename}"

        file_content = Path(file.path).read_bytes()
        await write_to_workspace_async(workspace_path, file_content)

        pd = PrivateData()
        pd.add_private_dataset(f"upload:{filename}", DataSensitivity.CONFIDENTIAL)

        summary = read_file_as_string(file.path)
        file_contexts.append(f"[File: {workspace_path}]\n{summary}")

    return "\n\n".join(file_contexts)
```

In the message handler, the file context is appended to the user's message:

```python
file_context = await process_uploaded_files(message.elements or [])
if file_context:
    user_message = f"{user_message}\n\n{file_context}"
```

The agent receives both the user's text and the file summaries in a single message. The workspace path is included so the agent can access the full file with tools when needed.

### Key Takeaways

Chainlit applications are defined by lifecycle handlers: `@cl.on_chat_start` for session initialization, `@cl.on_message` for processing user input, and `@cl.on_chat_resume` for restoring previous conversations.

Authentication uses `@cl.password_auth_callback` to verify credentials against a user database. The `manage-users` CLI manages user accounts. A JWT secret in the environment secures authentication sessions.

The data layer (`@cl.data_layer`) persists chat threads to SQLite. Combined with `@cl.on_chat_resume`, this enables users to continue previous conversations across browser sessions.

Starters (`@cl.set_starters`) provide quick-start suggestions. They can be static or generated dynamically based on the authenticated user.

`cl.user_session` provides per-session storage for agents, history, and configuration. This keeps sessions isolated and avoids global state.

Conversation history must be maintained explicitly. Append each user message and agent response to a list, pass the full list to the agent, and store the updated list after each turn.

The `@cl.step` decorator makes tool calls visible in the UI. Apply it to tool functions and they appear as expandable steps during agent execution.

File uploads are accessed via `message.elements`. Save files to the workspace, tag the session as private, and use the context reader to generate summaries that fit within context limits.

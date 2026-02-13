## Hands-On: AG-UI Side-Channels

AG-UI is a text-message protocol. Messages flow between frontend and backend as strings, tool calls, and state snapshots -- there is no built-in mechanism for binary file attachments, user feedback, or any other interaction that falls outside the conversation stream. The solution is a side-channel: a separate REST endpoint on the same Starlette application that handles the concern independently, while the AG-UI event stream stays focused on what it does well.

This section extends the v3 calculator (state management) with two side-channels: file uploads (v4) and user feedback (v5). Both v4 and v5 drop the `clear_history` tool from v3 to keep the examples focused on the new functionality.

#### File uploads -- the /upload endpoint

Since `AGUIApp` inherits from Starlette, it accepts a `routes` parameter for additional endpoints. The v4 backend adds an `/upload` route:

```python
from starlette.routing import Route
from pydantic_ai.ui.ag_ui.app import AGUIApp

app = AGUIApp(
    agent,
    deps=StateDeps(CalculatorState()),
    routes=[Route('/upload', upload_handler, methods=['POST'])],
)
```

The upload handler implements the save-summarize-tag pattern described in the file uploads section. It receives a multipart form with a single `file` field:

```python
from agentic_patterns.core.compliance.private_data import DataSensitivity, PrivateData
from agentic_patterns.core.context.reader import read_file_as_string
from agentic_patterns.core.workspace import write_to_workspace_async, workspace_to_host_path

UPLOAD_PREFIX = "/workspace/uploads"

async def upload_handler(request: Request) -> JSONResponse:
    form = await request.form()
    file = form.get("file")
    if file is None:
        return JSONResponse({"error": "No file provided"}, status_code=400)

    content = await file.read()
    filename = file.filename or "upload"
    sandbox_path = f"{UPLOAD_PREFIX}/{filename}"

    # 1. Save to workspace
    await write_to_workspace_async(sandbox_path, content)

    # 2. Tag as private data
    PrivateData().add_private_dataset(f"upload:{filename}", DataSensitivity.CONFIDENTIAL)

    # 3. Summarize with context reader
    host_path = workspace_to_host_path(PurePosixPath(sandbox_path))
    summary = read_file_as_string(host_path)

    return JSONResponse({"workspace_path": sandbox_path, "summary": summary})
```

The three steps execute in order. The file is persisted first so it survives the request. The session is tagged as private before the summary is generated. The response returns the workspace path (a stable pointer the agent can reference later) and a compact summary (what the agent needs to understand the content).

On the frontend side, the `ChatPanel` component gains a hidden file input, an attach button, and a file tag bar. A `pendingFiles` state array tracks selected files. On submit, if files are pending, the component uploads each one to `${backendUrl}/upload` via `fetch` with `FormData`, collects the workspace paths and summaries, and prepends them to the user's message text:

```tsx
async function uploadFiles(files: File[]): Promise<string> {
  const parts: string[] = []
  for (const file of files) {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${backendUrl}/upload`, { method: 'POST', body: formData })
    if (res.ok) {
      const data = await res.json()
      parts.push(`[Uploaded file: ${data.workspace_path}]\n${data.summary}`)
    } else {
      parts.push(`[Upload failed: ${file.name}]`)
    }
  }
  return parts.join('\n\n')
}
```

The agent receives a single message containing both the file context and whatever text the user typed. From the agent's perspective, it looks like the user pasted file information into their message -- no special protocol support is needed.

#### User feedback -- the /feedback endpoint

The v5 backend adds a `/feedback` route alongside the existing `/upload` route:

```python
from agentic_patterns.core.feedback import FeedbackType, add_feedback

DEMO_USER_ID = "demo"
DEMO_SESSION_ID = "agui"

async def feedback_handler(request: Request) -> JSONResponse:
    """Handle user feedback (thumbs up/down, comments)."""
    body = await request.json()
    feedback_type_str = body.get("feedback_type")
    comment = body.get("comment", "")

    try:
        feedback_type = FeedbackType(feedback_type_str)
    except (ValueError, KeyError):
        return JSONResponse({"error": f"Invalid feedback_type: {feedback_type_str}"}, status_code=400)

    add_feedback(feedback_type, comment=comment, user_id=DEMO_USER_ID, session_id=DEMO_SESSION_ID)
    return JSONResponse({"status": "ok"})
```

The handler validates the `feedback_type` field against the `FeedbackType` enum (which accepts `thumbs_up`, `thumbs_down`, `error_report`, `comment`) and delegates to `add_feedback()` from the core feedback module. The core module appends a timestamped `FeedbackEntry` to a per-session JSON file under `FEEDBACK_DIR / user_id / session_id / feedback.json`.

The user and session IDs are hardcoded for the demo. In a production system, these would come from JWT claims decoded at the request boundary -- the same identity propagation pattern described in the session propagation section.

Both routes are registered in the `AGUIApp` constructor:

```python
app = AGUIApp(
    agent,
    deps=StateDeps(CalculatorState()),
    routes=[
        Route('/upload', upload_handler, methods=['POST']),
        Route('/feedback', feedback_handler, methods=['POST']),
    ],
)
```

On the frontend, `ChatPanel` adds a `feedbackGiven` state that tracks which messages have been rated, and a `submitFeedback` function that POSTs to the backend:

```tsx
const [feedbackGiven, setFeedbackGiven] = useState<Record<string, string>>({})

async function submitFeedback(messageId: string, feedbackType: string) {
  setFeedbackGiven((prev) => ({ ...prev, [messageId]: feedbackType }))
  try {
    await fetch(`${backendUrl}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feedback_type: feedbackType }),
    })
  } catch (err) {
    console.error('Feedback submission failed:', err)
  }
}
```

The state update happens before the network call so the UI responds immediately. Each assistant message renders two small buttons below its content:

```tsx
{msg.role === 'assistant' && (
  <div className="feedback-buttons">
    <button
      className={`feedback-btn${feedbackGiven[msg.id] === 'thumbs_up' ? ' active' : ''}`}
      onClick={() => submitFeedback(msg.id, 'thumbs_up')}
      disabled={!!feedbackGiven[msg.id]}
      title="Thumbs up"
    >+1</button>
    <button
      className={`feedback-btn${feedbackGiven[msg.id] === 'thumbs_down' ? ' active' : ''}`}
      onClick={() => submitFeedback(msg.id, 'thumbs_down')}
      disabled={!!feedbackGiven[msg.id]}
      title="Thumbs down"
    >-1</button>
  </div>
)}
```

Once a button is clicked, both buttons are disabled and the selected one is highlighted.

#### Why side-channels

AG-UI streams events over SSE. Injecting binary data into a text protocol would require base64 encoding (33% overhead), break the event format, and force the backend to decode inline. A separate HTTP POST keeps binary transfer clean, leverages standard multipart handling, and works with any file size. The AG-UI message stream stays focused on what it was designed for: text, tool calls, and state.

The side-channel approach also keeps these concerns out of the AG-UI adapter layer. The upload and feedback endpoints are regular Starlette routes with no dependency on the AG-UI protocol. The same handlers could be reused with a different protocol or frontend framework -- only the frontend code that calls the endpoints would change.

This pattern scales to other concerns that sit outside the conversation stream: analytics events, preference toggles, session metadata updates, or audit logging. Each one gets its own endpoint on the same Starlette application, keeping the AG-UI adapter layer clean and focused.

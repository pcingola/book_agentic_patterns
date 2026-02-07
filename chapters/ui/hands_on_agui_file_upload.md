## Hands-On: AG-UI File Upload

AG-UI is a text-message protocol. Messages flow between frontend and backend as strings, tool calls, and state snapshots -- there is no built-in mechanism for binary file attachments. When the user wants to upload a file, the protocol itself cannot carry it. The solution is a side-channel: a separate REST endpoint on the same Starlette application handles the multipart upload, and the frontend injects the returned file context into the user's message text before sending it through AG-UI.

### The /upload endpoint

The v4 backend extends v3 (calculator with state) by adding an `/upload` route. Since `AGUIApp` inherits from Starlette, it accepts a `routes` parameter for additional endpoints:

```python
from starlette.routing import Route
from pydantic_ai.ui.ag_ui.app import AGUIApp

app = AGUIApp(
    agent,
    deps=StateDeps(CalculatorState()),
    routes=[Route('/upload', upload_handler, methods=['POST'])],
)
```

The upload handler implements the same save-summarize-tag pattern described in the file uploads section. It receives a multipart form with a single `file` field:

```python
from agentic_patterns.core.compliance.private_data import PrivateData
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
    PrivateData().add_private_dataset(filename)

    # 3. Summarize with context reader
    host_path = workspace_to_host_path(PurePosixPath(sandbox_path))
    summary = read_file_as_string(host_path)

    return JSONResponse({"workspace_path": sandbox_path, "summary": summary})
```

The three steps execute in order. The file is persisted first so it survives the request. The session is tagged as private before the summary is generated. The response returns the workspace path (a stable pointer the agent can reference later) and a compact summary (what the agent needs to understand the content).

### Frontend changes

The `ChatPanel` component gains three additions: a hidden file input, an attach button, and a file tag bar.

A `pendingFiles` state array tracks selected files. The attach button triggers the hidden `<input type="file">`. Selected files appear as small tags below the message list, each with a remove button. On submit, if files are pending, the component uploads each one to `${backendUrl}/upload` via `fetch` with `FormData`, collects the workspace paths and summaries, and prepends them to the user's message text:

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

The `backendUrl` prop is passed from `App` to `ChatPanel` so the upload endpoint is always consistent with the AG-UI backend URL. When the user switches backends via the header input, uploads go to the correct server.

### Why a side-channel

AG-UI streams events over SSE. Injecting binary data into a text protocol would require base64 encoding (33% overhead), break the event format, and force the backend to decode inline. A separate HTTP POST keeps binary transfer clean, leverages standard multipart handling, and works with any file size. The AG-UI message stream stays focused on what it does well: text, tool calls, and state.

The side-channel approach also keeps the save-summarize-tag pipeline out of the AG-UI adapter layer. The upload endpoint is a regular Starlette route with no dependency on the AG-UI protocol. This means the same upload handler could be reused with a different protocol or frontend framework -- only the frontend code that calls the endpoint would change.

## File Uploads

Users may attach files to their messages. A spreadsheet with sales figures, a PDF contract, a JSON configuration, a CSV export from another tool. The UI receives the raw file and must decide what to do with it before the agent sees anything. Getting this wrong is easy and the consequences compound: a 50 MB CSV dumped directly into the context window exhausts the token budget in a single turn, a confidential document processed without tagging leaves the session unprotected, and a file stored only in memory disappears when the session ends.

Three rules govern file upload handling: save first, summarize second, tag third.

### Save to workspace, never to context

The uploaded file must be persisted to the workspace before any processing happens. The workspace module (`agentic_patterns.core.workspace`) provides `write_to_workspace_async`, which takes a sandbox path and the file content, translates the path to the user/session-isolated host directory, creates parent directories, and writes the file. The workspace survives session restarts and is accessible to tools, connectors, and downstream agents. UI frameworks like Chainlit give you a temporary path on disk that will be cleaned up after the request. If the file is not saved to the workspace, it is gone.

Saving first also means the agent can reference the file later. If the user uploads a spreadsheet and then three turns later asks "go back to that spreadsheet and filter by region," the file is still there at its workspace path. The agent does not need the full content in its context to work with the file -- it needs to know *where* the file is, and it can use the `FileConnector` or other tools to read specific parts on demand.

The critical mistake is adding the raw file content directly to the agent's context. A 10,000-row CSV serialized to text consumes tens of thousands of tokens. Even naive truncation strategies like reading the first N rows do not help when the file is wide rather than long -- a genomics CSV with 20,000 columns overflows the context on a single row. A PDF with embedded images produces megabytes of extracted text. Even a modest JSON file with deeply nested structures can expand to a size that crowds out the conversation history and leaves no room for the agent's reasoning. The workspace path is a pointer; the full content stays on disk where it belongs.

### Summarize with the context reader

The agent still needs to know *what* was uploaded. A bare file path tells the agent nothing about the content. The context reader (`read_file_as_string` from `agentic_patterns.core.context`) bridges this gap by producing a compact, type-aware summary that fits within token limits.

The reader detects the file type from its extension and dispatches to a specialized processor. A CSV file produces a header row plus a handful of sample rows, giving the agent enough to understand the schema without seeing every record. A JSON file is formatted with depth and array limits so the agent sees the structure without the bulk. Code files get syntax-aware truncation. PDFs and Word documents have their text extracted and trimmed. Spreadsheets show sheet names, column headers, and sample data. In every case, the output respects a configurable token budget (5,000 tokens by default), so the summary never dominates the context window regardless of how large the original file is.

The summary is appended to the user's message alongside the workspace path. This gives the agent two things: a human-readable preview of the content (so it can answer questions, identify relevant columns, or describe the file) and a stable path (so it can read, query, or process the full file using tools when needed).

### Tag private data

Uploaded files almost always contain data that should not leave the session. A user uploading a CSV of customer records, a financial report, or an internal configuration file is providing data that the agent should work with but not forward to external services. Unless the user explicitly states the file is public, the safe default is to treat it as private.

The `PrivateData` class from `agentic_patterns.core.compliance.private_data` manages this. Calling `add_private_dataset` with a dataset name and a `DataSensitivity` level tags the session. This activates the enforcement mechanisms described in the data sources chapter: tools annotated with `CONNECT` permission are blocked for the remainder of the session. The agent can still read, analyze, transform, and write results to the workspace, but it cannot send data to external endpoints, APIs, or notification services. The protection is infrastructure-level, not prompt-level -- no amount of prompt engineering by the user or the model can bypass a blocked tool.

The sensitivity level defaults to `CONFIDENTIAL`, which is appropriate for most user-uploaded files. If the application knows more about the file's classification (for example, files uploaded through a specific form field labeled "public data"), it can use a lower level. The ratchet principle applies: once the session reaches a given sensitivity level, it stays there. If the user uploads an internal document and later uploads a confidential one, the session becomes `CONFIDENTIAL` and does not revert when the agent finishes processing the second file.

### The flow

The upload handler iterates over attached files and applies all three steps to each one: save to workspace via `write_to_workspace_async`, tag the session via `PrivateData.add_private_dataset`, and generate a summary via `read_file_as_string`. The order matters -- the file is persisted and the session is protected before summarization runs. The resulting summaries, each prefixed with the workspace path, are concatenated and appended to the user's message so the agent receives both the text and the file context in a single turn. The Chainlit hands-on demonstrates this pattern in `process_uploaded_files`.

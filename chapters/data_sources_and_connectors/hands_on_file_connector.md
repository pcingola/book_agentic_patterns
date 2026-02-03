## Hands-On: File Connector

The FileConnector gives agents the ability to operate on files through the workspace sandbox. Rather than returning file contents directly into the conversation, the connector provides a structured set of operations -- write, read, edit, append, find, head, list, delete -- that let the agent interact with files the same way a developer would. The agent sees sandbox paths like `/workspace/notes.md`, while the actual files live in isolated host directories determined by user and session context.

This hands-on walks through `example_file_connector.ipynb`, where an agent creates a markdown file, reads it back, edits a specific line, and verifies the result.

## Setting Up the Connector and Tools

The FileConnector requires user and session context for workspace path translation, but this context is managed through Python's contextvars mechanism rather than explicit parameters. Instantiate the connector and bind its methods directly as tools:

```python
connector = FileConnector()

tools = [
    connector.append,
    connector.delete,
    connector.edit,
    connector.find,
    connector.head,
    connector.list,
    connector.read,
    connector.tail,
    connector.write,
]
```

Each method already has a clear signature and docstring that the model can reason about. The docstring matters: it is the model's only description of what the tool does. The connector handles all path translation internally by reading the current user and session from contextvars, so the model never sees or manages it.

## The Agent in Action

The prompt asks the agent to perform four sequential steps: create a file, read it, edit a line, and read it again. This exercises the core file operations and demonstrates that the agent can reason about line numbers and file state across multiple tool calls.

```python
agent = get_agent(tools=tools)

prompt = """Do the following steps:
1. Create a file /workspace/notes.md with a title '# Meeting Notes' and three bullet points.
2. Read the file back to verify it was created.
3. Edit line 3 to change the second bullet point to '- Agreed on weekly sync every Monday'.
4. Read the file again and show me the final content."""

agent_run, nodes = await run_agent(agent, prompt, verbose=True)
```

The `verbose=True` flag prints each step the agent takes, so you can see the tool calls and their results as they happen. The agent typically proceeds in order: calls `file_write` to create the file, `file_read` to verify, `file_edit` to modify line 3, and `file_read` again for the final content.

The edit operation uses 1-indexed, inclusive line ranges. When the agent calls the `edit` tool with `("/workspace/notes.md", 3, 3, "- Agreed on weekly sync every Monday")`, it replaces exactly line 3 with the new content. The connector validates that `start_line` and `end_line` are within bounds and returns an informative message describing what changed.

## Verifying on Disk

The final cell translates the sandbox path to the host filesystem and reads the file directly, confirming that the agent's operations produced a real artifact:

```python
host_path = workspace_to_host_path(PurePosixPath("/workspace/notes.md"))
print(host_path.read_text())
```

The `workspace_to_host_path()` function retrieves the current user and session from contextvars, then translates the sandbox path to the actual host filesystem location. This confirms the round-trip: the agent wrote through the sandbox, and we can read the result from the host path. The file persists after the agent conversation ends, available for subsequent agents, tools, or human inspection.

## FileConnector Operations

The full set of operations maps to common file interactions: `read`, `head`, `tail`, `find`, `list` for reading, and `write`, `append`, `edit`, `delete` for writing. Permission enforcement happens at the tool layer (covered in the tools chapter), not inside the connector itself.

All operations return strings: either the requested content or a status message like `"Wrote 142 bytes to /workspace/notes.md"`. Errors are returned as strings prefixed with `[Error]` rather than raised as exceptions. This design keeps the agent loop stable -- a failed tool call produces a message the model can reason about and retry, rather than crashing the loop.

## Key Takeaways

The FileConnector bridges agents and the filesystem through workspace sandbox isolation. Connector methods are bound directly as agent tools without explicit context parameters. The model sees only the logical operations (read, write, edit), while workspace path translation happens automatically inside the connector. Operations return strings for both success and failure, keeping the agent loop resilient.

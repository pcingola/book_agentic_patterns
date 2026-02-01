## Hands-On: File Connector

The FileConnector gives agents the ability to operate on files through the workspace sandbox. Rather than returning file contents directly into the conversation, the connector provides a structured set of operations -- write, read, edit, append, find, head, list, delete -- that let the agent interact with files the same way a developer would. The agent sees sandbox paths like `/workspace/notes.md`, while the actual files live in isolated host directories determined by user and session context.

This hands-on walks through `example_file_connector.ipynb`, where an agent creates a markdown file, reads it back, edits a specific line, and verifies the result.

## Wrapping Connector Methods as Agent Tools

FileConnector is instantiated with a `ctx` dict for workspace path translation. The agent framework calls tools with only the parameters the model specifies -- the model should not see or manage `ctx`. The standard solution is the closure pattern: a factory function captures the connector instance and returns inner functions that close over it.

```python
ctx = {"user_id": "demo", "session_id": "file_connector_demo"}
file = FileConnector(ctx)

def make_file_tools(file):
    def file_write(path: str, content: str) -> str:
        """Write content to a file. Creates parent directories as needed."""
        return file.write(path, content)

    def file_read(path: str) -> str:
        """Read a file."""
        return file.read(path)

    def file_edit(path: str, start_line: int, end_line: int, new_content: str) -> str:
        """Replace lines start_line to end_line (1-indexed, inclusive) with new_content."""
        return file.edit(path, start_line, end_line, new_content)

    # ... more tools ...

    return [file_write, file_read, file_edit, ...]
```

Each inner function has a clear signature and docstring that the model can reason about. The docstring matters: it is the model's only description of what the tool does. The `ctx` is held by the connector instance, invisible to the model.

This pattern appears throughout the codebase whenever tools need runtime context. It was introduced in the workspace hands-on and applies identically here.

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

The edit operation uses 1-indexed, inclusive line ranges. When the agent calls `file_edit("/workspace/notes.md", 3, 3, "- Agreed on weekly sync every Monday")`, it replaces exactly line 3 with the new content. The connector validates that `start_line` and `end_line` are within bounds and returns an informative message describing what changed.

## Verifying on Disk

The final cell translates the sandbox path to the host filesystem and reads the file directly, confirming that the agent's operations produced a real artifact:

```python
host_path = container_to_host_path(PurePosixPath("/workspace/notes.md"), ctx)
print(host_path.read_text())
```

This confirms the round-trip: the agent wrote through the sandbox, and we can read the result from the host path. The file persists after the agent conversation ends, available for subsequent agents, tools, or human inspection.

## FileConnector Operations

The full set of operations maps to common file interactions: `read`, `head`, `tail`, `find`, `list` for reading, and `write`, `append`, `edit`, `delete` for writing. Permission enforcement happens at the tool layer (covered in the tools chapter), not inside the connector itself.

All operations return strings: either the requested content or a status message like `"Wrote 142 bytes to /workspace/notes.md"`. Errors are returned as strings prefixed with `[Error]` rather than raised as exceptions. This design keeps the agent loop stable -- a failed tool call produces a message the model can reason about and retry, rather than crashing the loop.

## Key Takeaways

The FileConnector bridges agents and the filesystem through workspace sandbox isolation. The connector instance holds runtime context, and the closure pattern wraps instance methods into tool functions without exposing context to the model. Operations return strings for both success and failure, keeping the agent loop resilient.

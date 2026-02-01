## Hands-On: The Workspace

The workspace pattern addresses a fundamental tension in agentic systems: models have limited context windows, but real tasks often produce large intermediate artifacts. A data analysis might return thousands of rows. A code generator might produce hundreds of lines. A search might yield dozens of documents. Stuffing all of this into the prompt is wasteful and eventually impossible.

The workspace solves this by providing a shared, persistent file system where tools externalize large outputs. Instead of returning a full dataset, a tool writes it to disk and returns a concise summary with the file path. The agent's context stays small and focused on reasoning, while the workspace holds the unbounded material.

This hands-on explores the workspace pattern through `example_workspace.ipynb`, demonstrating path translation, the write-and-summarize pattern, context capture in tools, user isolation, and security boundaries.

## The Dual Path System

Agents operate in a sandbox. They see paths like `/workspace/reports/analysis.json`, but the actual file lives somewhere else entirely on the host filesystem. This indirection serves two purposes: it presents a clean, predictable interface to the agent, and it enables user isolation behind the scenes.

The workspace module provides functions to translate between these two views:

```python
sandbox_path = "/workspace/reports/analysis.json"
host_path = workspace_to_host_path(PurePosixPath(sandbox_path), ctx)

print(f"Agent sees:    {sandbox_path}")
print(f"Actual file:   {host_path}")
```

The `ctx` parameter carries identity information extracted from the request. In production, this comes from JWT claims or session cookies. For the notebook, we simulate it with a dictionary:

```python
ctx = {"user_id": "alice", "session_id": "session_001"}
```

The translation function uses this context to route the file to the correct user's directory. Alice's `/workspace/report.json` and Bob's `/workspace/report.json` resolve to completely different host paths.

## Write Large Output, Return Summary

The core pattern is straightforward: when a tool produces output too large to return directly, it writes the full result to the workspace and returns only a summary with the file path.

```python
def analyze_dataset(query: str, ctx) -> str:
    """Analyze data and save results to workspace."""
    result = {
        "query": query,
        "row_count": 50000,
        "statistics": {"mean": 42.5, "std": 12.3, "min": 0.1, "max": 99.8},
        "data": [{"id": i, "value": i * 0.1} for i in range(1000)],
    }

    output_path = "/workspace/analysis/result.json"
    write_to_workspace(output_path, json.dumps(result, indent=2), ctx)

    return f"""Analysis complete. Rows: {result['row_count']}, Mean: {result['statistics']['mean']}
Full results: {output_path}"""
```

The tool generates a result with 1000 data points, but returns only the row count, key statistics, and a path. The agent can reason about the summary and, if needed, use another tool to read specific portions of the full result.

This pattern keeps the agent's context efficient. A conversation that processes multiple datasets doesn't accumulate megabytes of raw data in its prompt history.

## Capturing Context in Agent Tools

When tools run inside an agent loop, the agent framework calls them with only the parameters the model specifies. The model doesn't know about `ctx` - it only sees the tool's public interface. We need a way to inject the context without exposing it as a tool parameter.

The solution is closures. A factory function captures `ctx` and returns tool functions that close over it:

```python
def make_workspace_tools(ctx):
    """Create workspace tools with captured context."""

    def search_data(query: str) -> str:
        """Search dataset and save results to workspace."""
        matches = [{"id": i, "name": f"item_{i}", "score": 0.9 - i*0.01} for i in range(500)]

        output_path = "/workspace/search_results.json"
        write_to_workspace(output_path, json.dumps(matches), ctx)

        return f"Found {len(matches)} matches. Top 3: {matches[:3]}. Full results: {output_path}"

    def read_file(path: str) -> str:
        """Read a file from the workspace."""
        return read_from_workspace(path, ctx)

    return [search_data, read_file]
```

The model sees `search_data(query: str)` and `read_file(path: str)`. It doesn't see `ctx`. But when the tools execute, they have access to the context through the closure. This is a common pattern for injecting runtime dependencies into tools without polluting their public signatures.

The agent can then use these tools naturally:

```python
tools = make_workspace_tools(ctx)
agent = get_agent(tools=tools)

prompt = "Search for sensor data and tell me how many results were found."
agent_run, nodes = await run_agent(agent, prompt, verbose=True)
```

## User Isolation

Each user and session gets an isolated directory. Two users writing to the same sandbox path produce files in different locations:

```python
bob_ctx = {"user_id": "bob", "session_id": "session_001"}

write_to_workspace("/workspace/secret.txt", "Bob's private data", bob_ctx)

bob_path = workspace_to_host_path(PurePosixPath("/workspace/secret.txt"), bob_ctx)
alice_path = workspace_to_host_path(PurePosixPath("/workspace/secret.txt"), ctx)

print(f"Bob's file:   {bob_path}")
print(f"Alice's file: {alice_path}")
```

The sandbox path is identical, but the host paths diverge based on the user ID. This isolation is invisible to the agent and to the tools themselves. They simply write to `/workspace/...` and the translation layer handles the rest.

## Security Boundaries

The workspace enforces security boundaries through path validation. Attempts to escape the sandbox are blocked:

```python
try:
    workspace_to_host_path(PurePosixPath("/workspace/../../../etc/passwd"), ctx)
except WorkspaceError as e:
    print(f"Blocked: {e}")
```

Path traversal attacks using `..` sequences are detected and rejected. Paths that don't start with the sandbox prefix are also rejected. The agent can only access files within its designated workspace, regardless of what paths it attempts to construct.

## Connection to Other Patterns

The workspace pattern intersects with several other concerns in agentic systems.

Context management becomes tractable because large artifacts live outside the prompt. The agent reasons over summaries and references, not raw data.

Tool composition becomes flexible because tools communicate through files rather than direct parameter passing. One tool writes an artifact; another tool reads it later. They don't need to know about each other.

Retrieval-augmented generation can treat the workspace as a document store. Files written during a session can be indexed, embedded, and retrieved in subsequent turns.

Debugging and auditing become possible because intermediate artifacts persist on disk. When something goes wrong, you can examine what each tool produced.

## Key Takeaways

The workspace provides a shared file system for externalizing large artifacts. Agents see sandbox paths while actual files are stored in isolated directories per user and session.

Tools should write large outputs to the workspace and return concise summaries with file paths. This keeps the agent's context small and focused.

Closures capture context for tools running inside agents. The factory pattern creates tools that close over `ctx` without exposing it as a parameter.

User isolation happens at the path translation layer. Different users writing to the same sandbox path produce files in different host directories.

Security boundaries prevent path traversal. The translation function validates all paths and rejects attempts to escape the sandbox.

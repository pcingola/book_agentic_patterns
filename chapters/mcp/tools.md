## Tools

**Tools are the execution boundary of MCP: they are where model intent is turned into validated, observable, and recoverable actions.**

In practical MCP systems, tools are not an auxiliary feature; they are the core mechanism through which an agent interacts with the world. Everything else in MCP—prompts, resources, sampling, elicitation—exists to support better decisions about *which tools to invoke and how*. A tool is therefore best understood not as a function exposed to a model, but as a carefully constrained execution contract enforced by the server.

This section focuses on how tools work *in practice*, with concrete examples drawn from common MCP server implementations such as FastMCP, and how errors and failures propagate back into an agent loop typically implemented with frameworks like Pydantic-AI.


#### From functions to tools: contracts, not code

Although tools are often implemented as ordinary functions, MCP deliberately erases that fact at the protocol boundary. What the model sees is never the function itself, only a declarative description derived from it.

Consider a tool that writes a file into a sandboxed workspace:

```python
def write_file(path: str, content: str, overwrite: bool = False) -> None:
    """
    Write text content to a file in the agent workspace.

    Args:
        path: Relative path inside the workspace.
        content: File contents.
        overwrite: Whether to overwrite an existing file.
    """
    ...
```

When exposed via an MCP server, this function is translated into a tool definition consisting of a name, an input schema, and a description. The schema encodes type information, required fields, and defaults. The description is written *for the model*, not for the developer.

At this point, the function body becomes irrelevant to the protocol. The model reasons entirely over the contract. This separation allows the server to validate inputs, enforce permissions, and reject invalid requests before execution.


#### Tool invocation as structured output

From the model’s perspective, invoking a tool is an act of structured generation. The model emits a message that must conform exactly to the tool’s schema. Conceptually, the output looks like this:

```json
{
  "tool": "write_file",
  "arguments": {
    "path": "notes/summary.txt",
    "content": "Draft conclusions…",
    "overwrite": false
  }
}
```

The MCP server validates this payload against the schema derived from the function signature. If validation fails—because a field is missing, a type is incorrect, or an unexpected argument appears—the call is rejected without executing any code.

This is the first and most important safety boundary in MCP. Tool calls are not “best effort”. They are either valid or they do not run.


#### Protocol errors and tool execution errors

MCP distinguishes two categories of failure: **protocol errors** and **tool execution errors**.

Protocol errors are standard JSON-RPC errors that indicate structural problems with the request itself -- calling a tool that does not exist, sending a malformed request, or violating protocol rules. These are returned as JSON-RPC error responses:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "error": {
    "code": -32602,
    "message": "Unknown tool: write_file_v2"
  }
}
```

Tool execution errors, by contrast, are reported inside the tool result with `isError: true`. These indicate that the tool ran but could not complete successfully -- for example, because the model provided a wrong argument value, or because the operation violated a business rule:

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "File already exists and overwrite=false: notes/summary.txt"
      }
    ],
    "isError": true
  }
}
```

This distinction matters for agent behavior. Tool execution errors contain actionable feedback that the model can use to self-correct and retry with different arguments. Protocol errors indicate structural issues that the model is less likely to fix on its own. The MCP specification recommends that clients should provide tool execution errors to the model to enable self-correction.


#### How tool errors propagate into the agent loop

In agentic systems, tool execution is embedded in a reasoning-action loop. A tool result with `isError: true` is injected back into the model's context as an observation, not as an exception that crashes the system. The model reads the error message, reasons about what went wrong, and decides its next action -- perhaps retrying with corrected arguments, choosing a different approach, or asking the user for help.

This is where MCP's design aligns naturally with typed agent frameworks. Errors are values that flow through the same channel as successful results. The model can inspect them, reason over them, and act accordingly.


#### Retryable vs fatal errors in practice

MCP does not define retry semantics, and this is by design. Retries depend on context that only the agent or orchestrator can see: task intent, execution history, side effects already performed, and external constraints.

A crucial practical concern is distinguishing transient failures from terminal ones. A wrong argument value or a missing file may warrant a retry with different inputs. An infrastructure failure or a permission violation usually should not be retried at all -- the agent run should be aborted.

The core library used in this book's code examples makes this distinction explicit through two error classes: `ToolRetryError` and `ToolFatalError`. A `ToolRetryError` is surfaced to the model as a tool execution error, giving it a chance to correct its approach. A `ToolFatalError` aborts the agent run immediately, preventing wasted iterations on unrecoverable problems.

```python
from agentic_patterns.core.mcp import ToolRetryError, ToolFatalError

@mcp.tool()
def write_file(path: str, content: str, overwrite: bool = False) -> str:
    host_path = workspace_to_host_path(path)
    if host_path.exists() and not overwrite:
        raise ToolRetryError(f"File already exists: {path}. Set overwrite=True to replace it.")
    try:
        host_path.write_text(content)
    except OSError as e:
        raise ToolFatalError(f"Cannot write to filesystem: {e}")
    return f"Written {len(content)} bytes to {path}"
```

This separation prevents the agent from endlessly retrying operations that can never succeed, while still allowing recovery from correctable mistakes.



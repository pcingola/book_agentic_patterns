# Chapter: MCP

## Tools

**Tools are the execution boundary of MCP: they are where model intent is turned into validated, observable, and recoverable actions.**

In practical MCP systems, tools are not an auxiliary feature; they are the core mechanism through which an agent interacts with the world. Everything else in MCP—prompts, resources, sampling, elicitation—exists to support better decisions about *which tools to invoke and how*. A tool is therefore best understood not as a function exposed to a model, but as a carefully constrained execution contract enforced by the server.

This section focuses on how tools work *in practice*, with concrete examples drawn from common MCP server implementations such as FastMCP, and how errors and failures propagate back into an agent loop typically implemented with frameworks like Pydantic-AI.

---

## From functions to tools: contracts, not code

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

---

## Tool invocation as structured output

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

---

## Validation failures and early rejection

Validation errors are common, especially in early agent iterations. MCP makes these failures explicit and structured, rather than burying them in logs or free-form text.

For example, if the model omits a required field, the server might return:

```json
{
  "error": {
    "code": "INVALID_ARGUMENTS",
    "message": "Missing required field: path",
    "details": {
      "field": "path"
    }
  }
}
```

This error is returned to the client and injected back into the agent’s context. The agent can now reason over the failure deterministically, rather than guessing what went wrong from an unstructured error string.

---

## Domain errors inside tool execution

Even when inputs are valid, execution may still fail. These failures belong to the *domain* of the tool, not to schema validation.

Returning to the file-writing example, suppose the file already exists and `overwrite` is false. The implementation may raise a domain-specific error, which the MCP server translates into a structured response:

```json
{
  "error": {
    "code": "FILE_EXISTS",
    "message": "File already exists and overwrite=false",
    "details": {
      "path": "notes/summary.txt"
    }
  }
}
```

This distinction matters. The model provided valid inputs, but the requested action is not permissible under current conditions. A well-designed agent can respond by retrying with `overwrite=true`, choosing a different path, or asking the user for confirmation.

---

## How tool errors propagate into the agent loop

In agentic systems, tool execution is embedded in a reasoning–action loop. A simplified control flow looks like this:

```python
result = call_tool(tool_call)

if result.is_error:
    agent.observe_tool_error(
        code=result.error.code,
        message=result.error.message,
        details=result.error.details,
    )
else:
    agent.observe_tool_result(result.data)
```

The critical point is that tool failures are *observations*, not exceptions that crash the system. The agent receives structured data describing what happened and incorporates it into the next reasoning step.

This is where MCP’s design aligns naturally with typed agent frameworks. Errors are values. They can be inspected, classified, and acted upon using ordinary control logic.

---

## Retry and recovery as explicit policy

MCP does not define retry semantics, and this is by design. Retries depend on context that only the agent or orchestrator can see: task intent, execution history, side effects already performed, and external constraints.

Because errors are structured, retry logic can be written explicitly and safely:

```python
if error.code == "RATE_LIMITED":
    sleep(backoff(attempt))
    retry_same_call()
elif error.code == "FILE_EXISTS":
    retry_with_arguments(overwrite=True)
else:
    escalate_or_abort()
```

The tool implementation does not decide whether to retry. It merely reports what went wrong. The agent decides what to do next.

This separation prevents hidden retries, duplicated side effects, and uncontrolled loops—failure modes that are common in naïve tool-calling systems.

---

## Transient vs terminal failures

A crucial practical concern is distinguishing transient failures from terminal ones. Network timeouts, temporary unavailability, or rate limits may warrant retries. Permission errors, unsupported operations, or invariant violations usually do not.

By standardizing error codes and propagating them explicitly, MCP enables agents to make this distinction reliably. Over time, this allows agent behavior to evolve from brittle heuristics into deliberate recovery strategies.

---

## Why this level of rigor matters

In long-running or autonomous agents, tools may be invoked hundreds or thousands of times. Without strict contracts, structured validation, and explicit error propagation, failures accumulate silently and reasoning degrades. Debugging becomes guesswork, and safety boundaries erode.

MCP’s tool model addresses this by treating tool invocation as a first-class, schema-governed interaction with clear failure semantics. When combined with typed agent frameworks and explicit retry policies, tools become a reliable execution substrate rather than a fragile extension of prompting.

In practice, this is what allows MCP-based systems to move beyond demos and into production-grade agentic platforms.

---

## References

1. Anthropic. *Model Context Protocol: Server Tools Specification*. MCP Documentation, 2025. [https://modelcontextprotocol.io/specification/2025-06-18/server/tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
2. FastMCP Contributors. *FastMCP Tool Servers*. FastMCP Documentation, 2025. [https://gofastmcp.com/servers/tools](https://gofastmcp.com/servers/tools)
3. OpenAI. *Structured Outputs and Function Calling*. OpenAI Technical Documentation, 2023.

## Other Server and Client Features

MCP features beyond tools define how instructions, data, generation control, and human input are modeled explicitly, making agent behavior inspectable, reproducible, and scalable.

This section omits tools and focuses on the remaining server- and client-side features that structure *context* and *control flow* around model execution.


## Prompts (server feature)

Prompts are server-defined, named instruction templates that clients can invoke with parameters.

### What prompts are in practice

A prompt is a reusable instruction artifact owned by the server. It encapsulates task framing, tone, constraints, and best practices, while exposing only a small set of parameters to the client. The client selects *which* prompt to use and supplies arguments; the server controls the actual instruction text.

### Server-side definition

```python
@mcp.prompt()
def analyze_log_file(severity: str, audience: str) -> str:
    return f"""
    Analyze the provided log file.
    Focus on issues with severity >= {severity}.
    Explain findings for a {audience} audience.
    Provide concrete remediation steps.
    """
```

Multiple prompts can coexist on the same server, each representing a distinct behavioral contract.

### Client-side usage

```python
response = client.run(
    prompt="analyze_log_file",
    arguments={
        "severity": "ERROR",
        "audience": "site reliability engineers"
    }
)
```

The client never embeds the instruction text itself. This makes prompt changes transparent to clients and easier to review and test centrally.


## Resources (server feature)

Resources expose data artifacts as addressable protocol objects rather than inline text.

### What resources are in practice

A resource is any piece of data an agent may need to consult: documents, configuration files, intermediate results, reports, or generated artifacts. Resources are identified by stable paths or URIs and fetched explicitly.

### Server-side definition

```python
@mcp.resource("reports/{report_id}")
def load_report(report_id: str) -> str:
    path = f"/data/reports/{report_id}.md"
    with open(path) as f:
        return f.read()
```

Resources can also be dynamically generated:

```python
@mcp.resource("runs/{run_id}/summary")
def run_summary(run_id: str) -> str:
    return summarize_run_state(run_id)
```

### Client-side usage

```python
report_text = client.read_resource("reports/incident-2025-01")

analysis = client.run(
    prompt="analyze_log_file",
    arguments={
        "severity": "WARN",
        "audience": "management"
    },
    context={
        "report": report_text
    }
)
```

This pattern avoids copying large documents into every prompt and supports workspace-style workflows where artifacts are produced, stored, and revisited across turns.


## Sampling (client feature)

Sampling gives the client explicit control over generation behavior on a per-request basis.

### What sampling controls

Sampling parameters govern randomness, verbosity, and termination. By elevating these to the protocol level, MCP allows clients to adapt generation behavior to the current phase of an agent workflow.

### Client-side examples

Exploratory reasoning phase:

```python
draft = client.run(
    prompt="brainstorm_hypotheses",
    arguments={"topic": "database latency spikes"},
    sampling={
        "temperature": 0.8,
        "max_tokens": 500
    }
)
```

Deterministic execution phase:

```python
final_report = client.run(
    prompt="produce_incident_report",
    arguments={"incident_id": "2025-01"},
    sampling={
        "temperature": 0.1,
        "max_tokens": 800
    }
)
```

Sampling becomes an explicit part of orchestration logic rather than a hidden global setting.


## Elicitation (client feature)

Elicitation represents explicit requests for human input during agent execution.

### What elicitation is in practice

When an agent cannot proceed safely or correctly without additional information, it emits an elicitation request instead of continuing autonomously. This creates a well-defined pause point that external systems can handle reliably.

### Client-side elicitation request

```python
client.elicit(
    question="Which environment should this fix be deployed to?",
    options=["staging", "production"]
)
```

The agent’s execution is suspended until a response is provided.

### Resuming after elicitation

```python
answer = client.wait_for_elicitation()

deployment = client.run(
    prompt="deploy_fix",
    arguments={"environment": answer}
)
```

This makes human-in-the-loop interaction explicit, auditable, and composable with automated steps.


## How these features work together

A typical flow combining these features might look as follows:

1. The client retrieves a resource representing an existing artifact.
2. The client invokes a server-defined prompt to analyze or transform that artifact.
3. Sampling parameters are tuned to the task’s requirements.
4. If ambiguity arises, the agent issues an elicitation request.
5. Execution resumes once human input is provided, producing new resources or outputs.

None of these steps require embedding large instructions or data blobs directly into prompts. The protocol enforces structure while remaining agnostic to storage, UI, or orchestration frameworks.


## References

1. Model Context Protocol. *Server Prompts Specification*. MCP, 2025. [https://modelcontextprotocol.io/specification/2025-06-18/server/prompts](https://modelcontextprotocol.io/specification/2025-06-18/server/prompts)
2. Model Context Protocol. *Server Resources Specification*. MCP, 2025. [https://modelcontextprotocol.io/specification/2025-06-18/server/resources](https://modelcontextprotocol.io/specification/2025-06-18/server/resources)
3. Model Context Protocol. *Client Sampling Specification*. MCP, 2025. [https://modelcontextprotocol.io/specification/2025-06-18/client/sampling](https://modelcontextprotocol.io/specification/2025-06-18/client/sampling)
4. Model Context Protocol. *Client Elicitation Specification*. MCP, 2025. [https://modelcontextprotocol.io/specification/2025-06-18/client/elicitation](https://modelcontextprotocol.io/specification/2025-06-18/client/elicitation)
5. GoFastMCP. *Examples and Server Patterns*. GoFastMCP, 2024. [https://gofastmcp.com](https://gofastmcp.com)

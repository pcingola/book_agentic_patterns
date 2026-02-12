## Other Server and Client Features

MCP features beyond tools define how instructions, data, generation control, and human input are modeled explicitly, making agent behavior inspectable, reproducible, and scalable.

This section omits tools and focuses on the remaining server- and client-side features that structure *context* and *control flow* around model execution.


### Prompts (server feature)

Prompts are server-defined, named instruction templates that clients can invoke with parameters.

#### What prompts are in practice

A prompt is a reusable instruction artifact owned by the server. It encapsulates task framing, tone, constraints, and best practices, while exposing only a small set of parameters to the client. The client selects *which* prompt to use and supplies arguments; the server controls the actual instruction text.

#### Server-side definition

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

#### Client-side usage

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


### Resources (server feature)

Resources expose data artifacts as addressable protocol objects rather than inline text.

#### What resources are in practice

A resource is any piece of data an agent may need to consult: documents, configuration files, intermediate results, reports, or generated artifacts. Resources are identified by stable paths or URIs and fetched explicitly.

#### Server-side definition

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

#### Client-side usage

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


### Sampling (client feature)

Sampling allows servers to request LLM completions from the client. Rather than requiring servers to hold their own API keys or manage direct access to language models, MCP provides a standardized way for a server to ask the client to generate text, images, or audio on the server's behalf. The client maintains full control over model access, selection, and permissions.

#### How sampling works

When a server needs LLM assistance during its own processing -- for example, to summarize intermediate results, classify an input, or generate a response within a tool execution -- it sends a `sampling/createMessage` request to the client. The client then performs the generation using whatever model it has access to and returns the result.

This flow is deliberately asymmetric. The server specifies what it needs (messages, model preferences, constraints), but the client decides which model to use and whether to honor the request at all. For trust and safety, the specification recommends that there should always be a human in the loop with the ability to review and deny sampling requests.

#### Server-side request

A server requesting a completion provides messages and optional model preferences:

```json
{
  "method": "sampling/createMessage",
  "params": {
    "messages": [
      {
        "role": "user",
        "content": {
          "type": "text",
          "text": "Summarize the following log entries..."
        }
      }
    ],
    "modelPreferences": {
      "hints": [{ "name": "claude-3-sonnet" }],
      "speedPriority": 0.8,
      "intelligencePriority": 0.5
    },
    "maxTokens": 500
  }
}
```

Model preferences use a hint-based system rather than exact model names, since the client may use a different provider entirely. The client maps hints to the best available model based on the requested priorities.

#### Client-side response

The client performs the generation and returns the result:

```json
{
  "result": {
    "role": "assistant",
    "content": {
      "type": "text",
      "text": "The logs show three recurring timeout errors..."
    },
    "model": "claude-3-sonnet-20240307",
    "stopReason": "endTurn"
  }
}
```

This mechanism enables MCP servers to implement agentic behaviors -- tool executions that themselves require reasoning -- without being coupled to any specific model provider. The server delegates generation to the client, which acts as a controlled gateway to LLM capabilities.


### Elicitation (client feature)

Elicitation allows servers to request additional information from users through the client. When a server needs input that it cannot determine on its own -- a confirmation, a preference, missing credentials -- it sends an `elicitation/create` request to the client, which presents the question to the user and returns the response.

#### How elicitation works

Elicitation supports two modes. **Form mode** collects structured data directly through the client's UI, using a JSON Schema to define the expected fields. **URL mode** directs users to an external URL for sensitive interactions (such as OAuth flows or credential entry) that should not pass through the MCP client.

#### Server-side request

A server requesting user input sends a structured elicitation request:

```json
{
  "method": "elicitation/create",
  "params": {
    "mode": "form",
    "message": "Which environment should this fix be deployed to?",
    "requestedSchema": {
      "type": "object",
      "properties": {
        "environment": {
          "type": "string",
          "enum": ["staging", "production"]
        }
      },
      "required": ["environment"]
    }
  }
}
```

The client presents this to the user as a form and returns the response.

#### Client-side response

The user's answer comes back as a structured response with an action indicating what the user did:

```json
{
  "result": {
    "action": "accept",
    "content": {
      "environment": "staging"
    }
  }
}
```

The three possible actions are `accept` (user submitted data), `decline` (user explicitly refused), and `cancel` (user dismissed without choosing). The server handles each case appropriately, for example by proceeding with the selected environment, offering alternatives, or aborting the operation.

This makes human-in-the-loop interaction explicit, auditable, and composable with automated steps. The server never guesses when it can ask, and the client always mediates the interaction with the user.


### How these features work together

A typical flow combining these features might look as follows:

1. The client retrieves a resource representing an existing artifact.
2. The client invokes a server-defined prompt to frame an analysis task.
3. The server uses sampling to request LLM help during tool execution.
4. If ambiguity arises, the server sends an elicitation request to gather user input.
5. Execution resumes once human input is provided, producing new resources or outputs.

None of these steps require embedding large instructions or data blobs directly into prompts. The protocol enforces structure while remaining agnostic to storage, UI, or orchestration frameworks.



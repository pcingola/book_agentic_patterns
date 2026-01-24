## Skills Specification

The skills specification defines a **small, rigorous contract** that allows agentic capabilities to be described, reasoned about, and invoked reliably—without exposing implementation details or inflating the agent’s context.

### Engineering goals of the specification

From an engineer’s perspective, the specification is designed to solve three concrete problems that emerge once agents move beyond toy demos.

First, agents must **plan before they execute**. This requires a representation of capabilities that is cheap to load into context, stable across versions, and precise enough to support reasoning and validation. Second, capabilities must be **portable across runtimes**: the same skill should work whether it is backed by a local function, an MCP server, or a remote service invoked via A2A. Third, the system must support **progressive disclosure**, so that agents reason over compact specifications and only pay the cost of execution when necessary.

The skills specification addresses these constraints by being declarative, schema-driven, and intentionally minimal.

### Skill as a declarative contract

A skill is defined as a pure declaration of *what* is offered, not *how* it is implemented. The specification treats a skill as an interface with four essential components: identity, description, input schema, and output schema. Everything else is optional metadata.

A canonical definition starts with identity and intent:

```yaml
id: filesystem.search
version: "1.0.0"
description: >
  Search files by name or content and return matching paths.
```

The identifier is stable and globally unique within the agent’s skill universe. Versioning is explicit and semantic, allowing agents to reason about compatibility and upgrades. The description is written for the model, not for a human reader skimming documentation. In practice, short declarative sentences outperform long prose.

### Typed inputs as the primary control surface

The input schema is the most operationally important part of the specification. It defines exactly what arguments an agent may supply and constrains the space of valid invocations.

```yaml
input:
  type: object
  properties:
    query:
      type: string
      description: Text to search for
    recursive:
      type: boolean
      default: true
    limit:
      type: integer
      minimum: 1
      maximum: 100
      default: 10
  required: [query]
```

Several design choices matter here. Inputs are always explicit objects, never positional arguments, which makes partial construction and validation straightforward. Defaults reduce token overhead during invocation. Simple constraints such as bounds or enums significantly reduce failure modes when models generate arguments.

For an engineer, this schema doubles as runtime validation and as a *prompting primitive*. The model internalizes the structure and learns to stay within it.

### Outputs as guarantees, not suggestions

Output schemas provide a hard guarantee about the shape of the result. This is essential for downstream composition, where one skill’s output often feeds directly into another’s input.

```yaml
output:
  type: object
  properties:
    matches:
      type: array
      items:
        type: object
        properties:
          path:
            type: string
          score:
            type: number
```

Unlike traditional APIs, agents often consume outputs probabilistically. A strict schema anchors that uncertainty. Engineers can rely on structural correctness even if semantic quality varies.

### Optional metadata and execution hints

The specification allows lightweight metadata that informs planning and orchestration without constraining implementation. These fields are advisory, not prescriptive.

```yaml
metadata:
  side_effects: false
  latency: low
  idempotent: true
```

This information becomes valuable once agents perform speculative planning, retries, or parallel execution. For example, a planner may freely retry an idempotent skill but require confirmation before invoking one with side effects.

### Separation from implementation

A key property of the specification is that it is **implementation-agnostic**. The runtime binding between a skill definition and executable code is external to the spec.

From the agent’s point of view, invocation is uniform:

```json
{
  "skill": "filesystem.search",
  "arguments": {
    "query": "report",
    "limit": 5
  }
}
```

Whether this call resolves to a local function, an MCP tool, or an A2A task is irrelevant at the specification level. This separation is what enables skills to act as the common currency between heterogeneous systems.

### Minimal implementation burden

Despite the rigor of the specification, implementing a skill is deliberately lightweight. In most runtimes, an implementation consists of binding a callable to a validated schema and returning structured data.

```python
@skill(
    id="filesystem.search",
    input=SearchInput,
    output=SearchOutput,
)
def search(query: str, recursive: bool = True, limit: int = 10):
    ...
    return {"matches": matches}
```

There is no required inheritance model, lifecycle interface, or framework lock-in. This is a deliberate engineering trade-off: the specification optimizes for *many small skills* rather than a few monolithic tools.

### Why simplicity matters at scale

As agentic systems grow, complexity tends to accumulate at the boundaries: discovery, invocation, validation, and composition. The skills specification pushes that complexity into a single, well-defined layer and keeps everything else flexible.

For engineers, this means faster iteration, safer composition, and the ability to integrate skills cleanly with orchestration layers such as MCP and A2A without rewriting or re-prompting core logic.

### References

1. Anthropic. *Claude Skills Documentation*. 2024. [https://code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)
2. AgentSkills. *What Are Skills?*. 2024. [https://agentskills.io/what-are-skills](https://agentskills.io/what-are-skills)
3. AgentSkills. *Skill Specification*. 2024. [https://agentskills.io/specification](https://agentskills.io/specification)

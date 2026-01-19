## Modularity in agentic systems

Modularity is the discipline of decomposing an agentic system into composable parts—each with a clear interface—so you can evolve prompts, tools, agents, and orchestration independently.

### A modularity "stack" for agentic systems

A useful way to think about modularity in agentic systems is as a stack of boundaries—from the smallest (prompt fragments) to the largest (inter-agent protocols). Each layer solves a different engineering problem, and mature systems usually use several layers at once.

#### Prompt modularity: functions for cognition

Prompts are often treated as monolithic strings, but they behave more like *code*: they have “APIs” (inputs/outputs), invariants, and callers. Prompt modularity means splitting a large prompt into stable, testable pieces:

* **Policy/invariants** (never change lightly): safety constraints, formatting rules, refusal behavior, logging requirements.
* **Role and task spec** (changes with product): what the component is responsible for, what it must not do.
* **Few-shot examples** (change with quality work): curated demonstrations, counterexamples, edge cases.
* **Adapters** (change with environment): tool availability, domain glossary, tenant-specific rules.

A practical pattern is to treat prompt fragments like functions and compose them deterministically:

```python
def prompt_contract() -> str:
    return """You are a component that outputs JSON only.
Validate inputs. Never invent IDs. If uncertain, ask for clarification."""

def prompt_task(task_name: str) -> str:
    return f"""Task: {task_name}
Return fields: plan[], risks[], open_questions[]"""

def prompt_examples() -> str:
    return """Example input: ...
Example output: ..."""

def build_prompt(task_name: str) -> str:
    # Composition is deterministic; variability is pushed to model sampling.
    return "\n\n".join([prompt_contract(), prompt_task(task_name), prompt_examples()])
```

This mirrors software decomposition: `prompt_contract()` is your stable interface guarantee; `prompt_task()` is the “business logic spec;” examples are regression tests in disguise.

#### Tool modularity: typed interfaces and stable contracts

Tools are “callable modules” for agents. The modularity win is not merely *having* tools, but having **stable tool contracts** so that:

1. the agent can discover capabilities reliably, and
2. you can refactor tool internals without changing agent behavior.

A minimal tool contract has (a) a name, (b) a schema, (c) error semantics, and (d) determinism expectations.

```python
# Pseudo-interface: tool contracts are the agent equivalent of function signatures.
TOOL = {
  "name": "customer_lookup",
  "input_schema": {
    "type": "object",
    "properties": {"customer_id": {"type": "string"}},
    "required": ["customer_id"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "status": {"enum": ["ok", "not_found", "error"]},
      "customer": {"type": ["object", "null"]}
    },
    "required": ["status", "customer"]
  },
  "errors": [
    {"code": "INVALID_ARGUMENT", "retryable": False},
    {"code": "RATE_LIMITED", "retryable": True}
  ]
}
```

This is the same mental model as functions/classes:

* schema = signature / type hints
* errors = exceptions contract
* retryable vs not = idempotency + side-effect model

Modern “tool calling” APIs formalize this multi-step control flow (model proposes a call → app executes → model continues with results), which makes tool contracts a first-class modular boundary. ([OpenAI Platform][15])

#### MCP: modularity at the “port” boundary

Model Context Protocol (MCP) pushes modularity one level outward: tools, prompts, and resources are exposed by *servers* behind a standard client/server protocol. Instead of each application inventing bespoke integrations, MCP aims to standardize the boundary so components become swappable. The MCP specification explicitly frames this as a modular protocol design where implementations can support only the layers they need. ([Model Context Protocol][16])

Two key modularity consequences follow:

1. **Tool and resource providers become independent modules**
   A database connector, a filesystem browser, or a domain API wrapper can be shipped as an MCP server with a stable contract, then reused across multiple agents/apps.

2. **“Context” becomes a structured dependency**
   MCP resources and prompts let you treat context not as “more text in the prompt,” but as a separate module with its own retrieval and lifecycle rules. ([Model Context Protocol][17])

Conceptually:

```python
# Pseudocode: an agent runtime wired to multiple MCP servers.
mcp_servers = [
  {"name": "crm", "endpoint": "..."},
  {"name": "docs", "endpoint": "..."},
  {"name": "tickets", "endpoint": "..."},
]

tool_registry = aggregate_tools(mcp_servers)      # modular capability surface
resource_registry = aggregate_resources(mcp_servers)

result = agent.run(
  prompt=build_prompt("resolve_ticket"),
  tools=tool_registry,
  context=resource_registry.fetch("ticket:1234")
)
```

Note what changed versus “plain tool calling”: the agent no longer links directly to each tool implementation. It depends on a protocol boundary, like depending on an interface rather than a class.

#### A2A: modularity at the “agent as a service” boundary

If MCP makes *tools* reusable modules, A2A makes *agents themselves* reusable modules: independently hosted, potentially opaque systems that interoperate through a common language and interaction model. ([a2a-protocol.org][18])

The software analogy is direct:

* **tools** ~= library functions
* **MCP servers** ~= shared services exposing functions/resources
* **A2A agents** ~= microservices with richer behavior, state, and long-running work

The modularity payoff is organizational and architectural: teams can publish an “agent capability” behind an A2A interface, and other agents can delegate to it without embedding its prompt/tool internals.

```python
# Pseudocode: delegating work to a remote agent over an agent-to-agent protocol.
remote = discover_agent("finance.approvals")

task_id = remote.submit_task({
  "intent": "approve_refund",
  "inputs": {"order_id": "O-9182", "amount": 149.99}
})

while True:
  status, partial = remote.poll(task_id)
  if status in ("completed", "failed"):
    break

final = remote.get_result(task_id)
```

This is modularity at the same boundary as “service calls,” except the remote endpoint is an *agent* with its own reasoning loop, tools, and policies.

#### Skills: packaging and discoverability as modularity

“Skills” address a different (often underestimated) modularity problem: **packaging, documentation, and discoverability**. A skill format standardizes *how* a capability is described and shipped—typically as a small directory with a canonical manifest (e.g., a `SKILL.md`) plus optional scripts/assets/references. ([Agent Skills][19])

In software terms, skills are closest to:

* a package that includes README + examples + test vectors, and
* a contract that makes capabilities indexable and portable across environments.

This becomes especially valuable when capabilities are not only code (tools), but also prompt templates, evaluation harnesses, and operational notes.

#### Sub-agents: classes and dependency injection for behavior

Inside a single application, you often want multiple specialized agents (e.g., “planner,” “researcher,” “executor,” “critic”). That is modularity at the *component* level: each sub-agent has a purpose, its own prompt constraints, and a limited toolset. Frameworks that emphasize typed dependencies and structured outputs make this decomposition less fragile by turning hidden coupling (prompt conventions) into explicit interfaces. ([Pydantic AI][20])

A useful engineering rule: a sub-agent should have a narrower surface area than the parent agent—fewer tools, stricter output schema, clearer termination conditions.

```python
# Pseudocode: sub-agent boundaries are enforced by tool scoping + output contracts.

def planner_agent(goal: str) -> dict:
    # tools: none (or read-only); output: structured plan
    return llm_json(
        prompt=build_prompt("planning"),
        input={"goal": goal},
        tools=[]
    )

def executor_agent(step: dict) -> dict:
    # tools: execution tools only; output: step result
    return llm_json(
        prompt=build_prompt("execution"),
        input=step,
        tools=[TOOL_customer_lookup, TOOL_ticket_update]
    )

plan = planner_agent("Resolve ticket 1234 without violating refund policy")["plan"]
results = [executor_agent(step) for step in plan]
```

This mirrors classes/modules: each component has its own invariants and dependencies, and coupling is managed by explicit inputs/outputs.

#### Workflows and graphs: modularity in control flow

When the number of components grows, the primary complexity shifts from “what does each part do?” to “who calls whom, and when?” That’s a control-flow modularity problem.

Workflows (pipelines, supervisor/worker, hand-offs) keep control flow mostly linear and are often sufficient. Graphs (DAGs, state machines) make branching, retries, and long-lived state explicit and inspectable—useful when execution paths are numerous or must be audited. ([Pydantic AI][21])

A simple graph-shaped interface looks like this:

```python
# Pseudocode: a graph node is a module with a typed contract.
def node_retrieve(state): ...
def node_plan(state): ...
def node_execute(state): ...
def node_verify(state): ...

GRAPH = {
  "start": "retrieve",
  "nodes": {
    "retrieve": {"fn": node_retrieve, "next": "plan"},
    "plan": {"fn": node_plan, "next": "execute"},
    "execute": {"fn": node_execute, "next": "verify"},
    "verify": {"fn": node_verify, "next": lambda s: "execute" if s["needs_retry"] else "end"},
  }
}
```

The modularity benefit is not “graphs are cool,” but that *control flow becomes data*: you can visualize it, test it, version it, and enforce policies at edges (e.g., human approval before `ticket_update`).

### Mapping to classic software modularity

A compact mental mapping helps align agent architecture choices with well-understood software concepts:

* **Prompt fragment** <-> function body / configuration block
* **Tool contract** <-> function signature / interface
* **Skill package** <-> library/package with docs and examples
* **Sub-agent** <-> class/component with scoped dependencies
* **Workflow** <-> application service layer / use-case orchestrator
* **Graph** <-> explicit state machine / workflow engine
* **MCP server** <-> reusable service exposing tools/resources via a standard port
* **A2A agent** <-> autonomous service with a richer interaction model and long-running tasks

The common principle is to choose boundaries based on what changes at different rates. Prompts and examples may change weekly; tool schemas change rarely; protocols and cross-team contracts should change almost never. Good agentic modularity aligns those change rates with explicit interfaces so iteration remains cheap where it should be cheap, and stability exists where it must be stable.

[15]: https://platform.openai.com/docs/guides/function-calling
[16]: https://modelcontextprotocol.io/specification/2025-06-18/basic
[17]: https://modelcontextprotocol.io/
[18]: https://a2a-protocol.org/latest/specification/
[19]: https://agentskills.io/specification
[20]: https://ai.pydantic.dev/
[21]: https://ai.pydantic.dev/graph/

## Hands-On: Advanced Topics

The previous hands-on exercises demonstrated tool use, structured outputs, tool selection, permissions, and workspaces. Those patterns treat the tool interface as static: you define tools, hand them to an agent, and the agent uses them. Advanced tool use breaks that assumption. The toolset can change at each step, tool calls can pause for external approval, and tool definitions themselves can be analyzed and improved before deployment.

This hands-on explores these patterns through `example_advanced_topics.ipynb`, covering dynamic tools, human-in-the-loop approval via deferred tools, and the tool doctor.

### Dynamic Tools

Dynamic tools mean the agent's available tool interface is not fixed. A `prepare_tools` function runs before each model step, filtering or modifying the tool definitions based on runtime context. This enables patterns like progressive disclosure (start with safe tools, unlock powerful ones later) and contextual minimization (only show tools relevant to the current subtask).

The example defines four tools -- two read-only (`list_files`, `read_file`) and two mutating (`write_file`, `delete_file`) -- plus a `prepare_tools` function that filters based on a "phase" string passed as the agent's dependency:

```python
READ_TOOL_NAMES = {"list_files", "read_file"}

async def filter_by_phase(
    ctx: RunContext[str], tool_defs: list[ToolDefinition]
) -> list[ToolDefinition] | None:
    """In 'explore' phase, expose only read tools. Otherwise, expose all."""
    if ctx.deps == "explore":
        return [td for td in tool_defs if td.name in READ_TOOL_NAMES]
    return tool_defs
```

The function receives a `RunContext` (which carries the dependency value) and the full list of `ToolDefinition` objects. It returns a filtered list. PydanticAI calls this function before every model step, so the toolset can change dynamically within a single conversation.

The agent is created with all four tools and the `prepare_tools` hook:

```python
agent = get_agent(
    tools=[list_files, read_file, write_file, delete_file],
    prepare_tools=filter_by_phase,
    deps_type=str,
)
```

When run in "explore" phase, the agent can list and read files but cannot delete. The model does not see `write_file` or `delete_file` in its tool definitions at all. When run in "execute" phase, all four tools appear and the agent can perform mutations.

The `prepare_tools` mechanism is an agent-wide hook. PydanticAI also supports per-tool `prepare` functions (via the `Tool` class) for cases where individual tools need conditional visibility rather than system-wide phase gating.

### Human in the Loop (Deferred Tools)

Deferred tools separate tool *selection* from tool *execution*. The agent proposes a tool call, but instead of executing it immediately, the run pauses and returns a `DeferredToolRequests` object. An external process (a human reviewer, a policy engine, an approval queue) inspects the proposed calls, approves or denies each one, and resumes the run with a `DeferredToolResults` object containing the decisions.

The example defines two tools: `check_balance` (safe, executes immediately) and `transfer_funds` (marked with `requires_approval=True`):

```python
agent = get_agent(
    tools=[check_balance, Tool(transfer_funds, requires_approval=True)],
    output_type=[str, DeferredToolRequests],
)
```

The `output_type` includes both `str` and `DeferredToolRequests` because the agent might return a text answer (if no deferred tools are triggered) or a set of deferred requests (if the model calls a tool that requires approval).

When the agent is asked to check a balance and transfer funds, it executes `check_balance` normally and proposes `transfer_funds` as a deferred call. The run ends with a `DeferredToolRequests` object:

```python
result = await agent.run(
    "Check the balance of ACC-123 and transfer $500 from ACC-123 to ACC-456."
)
assert isinstance(result.output, DeferredToolRequests)
requests = result.output
messages = result.all_messages()
```

The `requests.approvals` list contains `ToolCallPart` objects with the tool name, arguments, and a unique `tool_call_id`. The caller inspects these, decides on each one, and builds a `DeferredToolResults` object:

```python
deferred_results = DeferredToolResults()
for call in requests.approvals:
    deferred_results.approvals[call.tool_call_id] = True

result = await agent.run(
    message_history=messages, deferred_tool_results=deferred_results
)
```

Approvals map each `tool_call_id` to `True` (approve), `ToolDenied("reason")` (deny with a message the model sees), or `ToolApproved(override_args={...})` (approve with modified arguments). The resume call passes the original `message_history` so the agent continues from where it paused. After resuming, the approved tool executes and the agent produces its final response.

This pattern applies directly to any tool with irreversible side effects, security sensitivity, or high cost. The approval step can be a CLI prompt, a web form, a Slack message, or any other channel that maps tool call IDs to decisions.

### Tool Doctor

The tool doctor is a development-time diagnostic that analyzes tool function definitions and produces structured recommendations. It evaluates naming clarity, docstring completeness, type annotation coverage, argument semantics, and return type documentation. The goal is to catch interface problems before they reach a running agent, where they would manifest as tool confusion, incorrect invocations, or unnecessary retries.

The example defines three intentionally under-documented tools:

```python
def process(data, flag=False):
    """Process data."""
    return data

def calc(x, y):
    return x + y

def fetch_and_transform(
    url: str, format: str = "json", retries: int = 3, timeout: float = 30.0
) -> dict:
    """Fetch data from URL."""
    return {"status": "ok"}
```

`process` has a vague name and description, untyped parameters, and no indication of what "processing" means. `calc` has no docstring at all, no type hints, and an ambiguous name. `fetch_and_transform` has type hints but its docstring does not mention the transform step, the `format` parameter shadows a Python builtin, and several parameters are undocumented.

Running the tool doctor produces a `ToolRecommendation` for each function:

```python
recommendations = await tool_doctor([process, calc, fetch_and_transform])
for r in recommendations:
    print(r)
```

Each recommendation includes the tool name, whether it needs improvement, general issues (naming, documentation), argument-level issues (missing types, vague names), and return type issues. The recommendations are structured Pydantic models, so they can be processed programmatically -- surfaced in CI, turned into pull request comments, or fed into automated fix pipelines.

The tool doctor is most valuable during tool authoring. Running it as part of the development workflow catches the kind of interface ambiguities that are invisible to standard linters but directly affect how well an LLM can use the tool.

### Key Takeaways

Dynamic tools let you reshape the agent's toolset at each step based on runtime context. The `prepare_tools` hook filters or modifies tool definitions before the model sees them, enabling patterns like phase-gated access and contextual minimization.

Deferred tools separate tool selection from execution by pausing the run and returning structured requests. An external process approves, denies, or modifies each proposed call, then resumes the run. This provides a clean control surface for human-in-the-loop review of high-impact operations.

The tool doctor analyzes tool definitions at development time, producing structured recommendations for naming, documentation, typing, and argument clarity. It catches interface problems that would otherwise surface as runtime failures or model confusion.

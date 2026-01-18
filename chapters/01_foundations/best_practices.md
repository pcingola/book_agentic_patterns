## Best practices

Build agentic systems that scale with computation, remain simple under iteration, and treat prompts and tools as testable engineering artifacts rather than clever one-off solutions.

### The Bitter Lesson applied to agent engineering

Sutton’s argument can be operationalized as a design filter for agentic systems:

First, prefer **general, scalable mechanisms** over intricate prompt “micro-surgery.” In practice, this means using prompts to set intent and constraints, but relying on tool calls, retrieval, search, and verification loops to do the heavy lifting. When you feel compelled to add complex prompt logic, ask whether the same reliability can be achieved by improving tool contracts, adding a check, or expanding an eval set.

Second, invest in **feedback loops that can run at scale**. For agents, the analog of “more compute” is not only bigger models, but also more runs: more automated eval cases, more traces, more counterexamples captured from production. Agent quality improves fastest when iteration is systematic and measured.

Third, keep the system **composable**. The more your architecture resembles small, replaceable parts (tools, sub-agents, evaluators, retrievers) rather than a monolithic prompt, the easier it becomes to scale improvements without rewriting everything.

### Building effective agents: when to use workflows vs agents

Anthropic draws a practical architectural distinction: **workflows** are LLM+tools orchestrated through predefined code paths, while **agents** are systems where the model dynamically decides what to do and which tools to call. Both are “agentic systems,” but they behave very differently in production. ([Anthropic][27])

A useful best practice is to start with workflows whenever possible:

Workflows are typically easier to test, cheaper, and more predictable because control flow is owned by code. Many “agent” problems are actually workflow problems (data extraction, enrichment, routing, standard business processes) with a few probabilistic steps. Promote a workflow to a fully dynamic agent only when you truly need open-ended decomposition, long-horizon exploration, or adaptive tool use.

When you do need an agent, keep the agent loop deliberately simple and make uncertainty explicit:

```python
# Pseudocode: conceptual agent loop (not framework-specific)
def run_agent(task: str, tools, policy, max_steps: int = 20):
    state = {"task": task, "notes": [], "artifacts": []}

    for step in range(max_steps):
        action = policy.decide_next_action(state, tools=tools)
        if action.kind == "FINAL":
            return action.final_answer

        result = tools.call(action.tool_name, action.args)
        state["notes"].append({"action": action, "result": result})

    raise RuntimeError("agent_exhausted_steps")
```

The “policy” here can be an LLM prompt, but notice what makes this production-friendly: bounded steps, explicit state, and a strict tool boundary.

Two concrete practices matter disproportionately in agent deployments:

**Define stopping conditions and budgets.** Agents without step limits, token budgets, and cancellation paths tend to fail expensively and unpredictably. Production-grade systems treat “give up gracefully” as a first-class success mode.

**Treat tool-use transcripts as the primary debugging surface.** Most real failures show up as wrong tool selection, missing arguments, or misinterpreted tool results—not as a purely “reasoning” issue.

### Writing tools for agents: contracts, context, and token economics

Tools are where agent reliability is won or lost. Anthropic’s tool guidance is fundamentally about turning tool calling into a high-signal, low-ambiguity interface: pick the right tools, name and namespace them clearly, return meaningful context, keep responses token-efficient, and iterate using evaluations (including having agents help improve the tools themselves). ([Anthropic][28])

A few practices are especially transferable:

#### Make tool interfaces self-describing and hard to misuse

Agent tools should be closer to *APIs with guardrails* than to thin wrappers around internal functions. Use typed inputs, constrained enums, and explicit error shapes. If a tool can fail, make failures structured so the agent can recover.

```python
# Illustrative schema shape (language/framework agnostic)
CreateTicket(
  title: str,                    # short, user-facing
  body_markdown: str,            # long-form details
  severity: "low"|"med"|"high",  # constrained
  owner_team: "eng"|"ops"|"sec", # constrained
  idempotency_key: str           # retries without duplicates
) -> { ticket_id: str, url: str }
```

This style aligns with the broader “structured outputs” approach: use schemas to validate what the model returns, keep interfaces object-shaped, and make it easy to reject/repair malformed outputs. ([Pydantic AI][29])

#### Return enough context for the model to make the next decision

A common failure mode is tools that return “OK” or a single scalar. Agents need *actionable* results: identifiers, next-step hints, partial state, and especially “what happened” when something fails.

```python
SearchContacts(query: str, limit: int) -> {
  matches: [{id: str, name: str, email: str}],
  truncated: bool,
  explanation: str   # brief, factual: how matching was done
}
```

#### Optimize tool responses for tokens, not for humans

Tool responses compete directly with working memory. Prefer short fields, avoid redundant prose, and return only what will plausibly affect the next step. If large payloads are needed (documents, logs, tables), return handles/URLs/IDs and provide a separate “fetch” tool with pagination.

### Reliability engineering for agents: retries, validation, and evals

Agent systems sit on top of probabilistic components and unreliable external services. Best practice is to assume transient failure and build a disciplined recovery strategy.

#### Retries belong at the system boundary

Retries should be configured for the kinds of failures you expect: rate limits, timeouts, temporary outages, context-length issues. Treat retries as policy, not ad-hoc try/except scattered across tools. The Pydantic ecosystem’s guidance for retry strategies in evals mirrors what works in production systems: consistent retry configuration, bounded attempts, and exponential backoff where appropriate. ([Pydantic AI][30])

```python
def call_with_retry(fn, *, max_attempts=3, backoff_s=1.0):
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except TransientError as e:
            if attempt == max_attempts:
                raise
            sleep(backoff_s * (2 ** (attempt - 1)))
```

The important part is not the mechanism—it’s the decision to classify errors (transient vs permanent), to cap retries, and to make the failure mode explicit.

#### Validate model outputs like untrusted user input

Whether it’s a tool call, a structured output, or a plan, treat the model as an untrusted producer. Schema validation and type checking catch entire categories of silent failures early (wrong types, missing fields, invalid enum values) and give you a clean “ask the model to try again” loop. ([Pydantic AI][29])

#### Use evals as the main lever for improvement

The most reliable path to better agents is expanding your evaluation set with real failures and near-misses. Tool design, prompt changes, and orchestration tweaks should be judged against regression suites, not vibes. Anthropic’s tool-writing guidance explicitly centers comprehensive evaluations and iterative improvement loops (including using agents to help optimize tools). ([Anthropic][28])

A minimal pattern is: capture a transcript → turn it into a test case → add an automated check.

```python
case = {
  "task": "Schedule a meeting with Jane next week and attach the notes doc",
  "expected": {
    "meeting_created": True,
    "attendees_include": ["jane@corp.com"],
    "notes_attached": True,
  }
}

result = run_agent(case["task"])
assert check_expectations(result, case["expected"])
```

### Practical synthesis: what “best practices” means in day-to-day work

In agentic engineering, “best practices” is less about any single framework or pattern and more about consistently choosing:

Simplicity over cleverness (because you will iterate), contracts over prose (because tools are your control surface), measurement over intuition (because stochastic systems deceive), and scalable feedback loops over handcrafted behavior (because that is where long-run performance comes from).

### References

1. Sutton, R. S. *The Bitter Lesson*. Incomplete Ideas (essay), 2019. ([Incomplete Ideas][31])
2. Anthropic. *Building effective agents*. Anthropic Engineering, 2024. ([Anthropic][27])
3. Anthropic. *Writing effective tools for agents — with agents*. Anthropic Engineering, 2025. ([Anthropic][28])
4. Pydantic AI. *Output (structured outputs and validation)*. Documentation. ([Pydantic AI][29])
5. Pydantic AI. *Function tools (tools, tool schema, toolsets)*. Documentation. ([Pydantic AI][32])
6. Pydantic Evals. *Retry strategies*. Documentation. ([Pydantic AI][30])

[27]: https://www.anthropic.com/research/building-effective-agents "Building Effective AI Agents | Anthropic"
[28]: https://www.anthropic.com/engineering/writing-tools-for-agents "Writing effective tools for AI agents—using AI agents | Anthropic"
[29]: https://ai.pydantic.dev/output/ "Output - Pydantic AI"
[30]: https://ai.pydantic.dev/evals/how-to/retry-strategies/ "Retry Strategies - Pydantic AI"
[31]: https://www.incompleteideas.net/IncIdeas/BitterLesson.html "The Bitter Lesson"
[32]: https://ai.pydantic.dev/tools/ "Function Tools - Pydantic AI"

## Autonomous vs supervised execution, approval, rollback, and reversibility

An execution-mode pattern for tool- and code-running agents that balances autonomy with explicit control points (approvals) and safety nets (rollback / compensations) around state-changing actions.

### Historical perspective

The intellectual roots of “supervised autonomy” predate LLM agents by decades. In mixed-initiative user interfaces, researchers studied how systems should fluidly shift control between human and machine, often guided by uncertainty and the cost of mistakes (e.g., when to ask, when to act, when to defer). ([erichorvitz.com][1]) In parallel, databases and distributed systems developed a rigorous vocabulary for **commit**, **logging**, **recovery**, and **undo**, because real systems fail mid-execution and must restore consistent state. ([ACM Digital Library][49])

In the LLM era, the “agent” framing made these older ideas operational again: LLMs began to interleave reasoning with actions (tool calls, API invocations, code execution), increasing both capability and risk. ReAct popularized the now-common loop of *think → act → observe → revise*, which naturally raises the question of when actions should be allowed to mutate the world without a checkpoint. ([arXiv][3]) At the same time, human feedback became a standard technique for aligning model behavior with user intent, reinforcing a broader pattern: autonomy works best when paired with *auditable steps* and *human arbitration* at the right moments. ([arXiv][4]) More recently, systems work has begun to formalize “undo,” “damage confinement,” and *post-facto validation* as first-class abstractions for LLM actions—explicitly connecting modern agents back to transaction and recovery concepts. ([arXiv][52])

### The pattern in detail

The core idea is to treat agent execution as a **controlled transaction over an external world**. The agent can reason freely, but actions that might change state are wrapped in a small number of well-defined mechanisms:

1. **Autonomy levels (policy-driven):** not “autonomous vs supervised” as a binary, but a spectrum of allowed actions.
2. **Approval gates (pre-commit controls):** pause execution before a risky or irreversible step, obtain an explicit decision, then continue.
3. **Rollback / compensation (post-commit controls):** if something goes wrong—or if a human later rejects the outcome—undo what can be undone, and compensate what cannot.
4. **Durability and auditability:** record enough to resume, explain, and repair.

A practical way to implement this is to classify steps into **non-mutating** vs **mutating** actions (and optionally *irreversible mutating* as a special case). Recent work highlights that failures often hinge on a small number of mutating steps, motivating selective gating rather than gating everything. ([OpenReview][6])

#### 1) Model the agent as an execution loop with explicit “pause and resume”

Instead of running the agent until it prints an answer, run it until it either:

* completes, or
* reaches an action that requires external input (approval, UI-side execution, long-running job result).

Conceptually:

```python
@dataclass
class ToolCall:
    name: str
    args: dict
    call_id: str
    is_mutating: bool
    requires_approval: bool

@dataclass
class PauseForApproval:
    pending: list[ToolCall]
    # include enough context to show a human what will happen
    summary: str

def agent_step(messages, tools, policy) -> str | PauseForApproval:
    call = plan_next_tool_call(messages, tools)  # LLM decision
    meta = tool_metadata(call.name)

    if meta.is_mutating and policy.requires_approval(call):
        return PauseForApproval(
            pending=[ToolCall(call.name, call.args, call.id, True, True)],
            summary=render_human_summary(call),
        )

    result = execute_tool(call)
    messages = messages + [call_to_message(call), tool_result_message(result)]
    return continue_or_finish(messages)
```

This “pause object” is the key architectural move: it turns human-in-the-loop from an ad-hoc UI prompt into a **first-class execution outcome** that can be persisted, audited, and resumed. Many modern agent frameworks implement a variant of this via “deferred tool calls” that end a run with a structured list of pending approvals/results, then continue later when those arrive. ([Pydantic AI][54])

#### 2) Approval gates should be selective, contextual, and explainable

A good approval gate is not “approve every tool call.” Instead, make approvals depend on:

* **mutation risk:** does it change state (send, delete, purchase, write, deploy)?
* **blast radius:** how big is the possible damage (one file vs an account)?
* **reversibility:** can the action be undone cheaply and reliably?
* **sensitivity:** does it touch secrets, money, user identity, regulated data?

A simple policy sketch:

```python
def requires_approval(call: ToolCall, ctx) -> bool:
    if not call.is_mutating:
        return False

    if call.name in {"send_email", "submit_payment", "delete_record"}:
        return True

    # contextual gating: protected resources, large diffs, prod env, etc.
    if call.name == "write_file" and ctx.path in ctx.protected_paths:
        return True

    if estimate_blast_radius(call, ctx) > ctx.max_autonomous_blast_radius:
        return True

    return False
```

The human needs a crisp, non-LLM-shaped explanation: *what will be changed, where, and how to undo it.* Architecturally, store metadata alongside the paused call (reason codes, diffs, impacted resources) so the UI can render a reliable “approval card” rather than raw model text. Deferred-tool designs explicitly support attaching metadata to approval requests for exactly this purpose. ([Pydantic AI][54])

#### 3) Treat rollback as a design constraint, not an afterthought

Rollback is easy only in toy settings. In real systems:

* some actions are **naturally reversible** (edit draft → revert, create resource → delete it),
* others are **logically compensatable** (refund payment, send correction email),
* others are **irreversible** (data leaked, notification pushed to many recipients).

This leads to three complementary techniques:

**A. Undo logs / versioned state** (classic transaction recovery)
Record “before” state and/or a sequence of state transitions so you can restore consistency after partial failure. ([ACM Digital Library][49])

**B. Compensating actions (Sagas)**
For distributed or multi-step workflows, define a compensation for each step and run compensations in reverse order on failure. ([Microsoft Learn][55])

**C. Damage confinement (blast-radius limits)**
If you cannot guarantee undo, restrict what the agent is allowed to touch. Recent LLM-agent runtime work explicitly frames “undo” plus “damage confinement” as the practical path to post-facto validation. ([arXiv][52])

A minimal “saga-like” execution record:

```python
@dataclass
class StepRecord:
    call: ToolCall
    result: dict | None
    compensation: ToolCall | None  # how to undo/compensate

def run_workflow(plan: list[ToolCall]) -> list[StepRecord]:
    log: list[StepRecord] = []
    for call in plan:
        res = execute_tool(call)
        log.append(StepRecord(call=call, result=res, compensation=derive_compensation(call, res)))
    return log

def rollback(log: list[StepRecord]) -> None:
    for step in reversed(log):
        if step.compensation:
            execute_tool(step.compensation)
```

Key best practice: require tool authors (or tool wrappers) to provide a compensation strategy *at the same time* they provide the mutating tool.

#### 4) Idempotency and retries are part of “reversibility”

Approval and rollback don’t matter if your execution layer is unreliable. Two properties reduce accidental double-effects:

* **Idempotency keys:** if the agent retries, the external system should recognize “same request” and not re-apply it.
* **Replayable logs:** if the agent process dies mid-run, you can resume from the last known-good step.

This is why “durable execution” and “pause/resume” designs show up together in modern agent tool stacks: approvals and long-running jobs naturally imply persistence and resumption. ([Pydantic AI][56])

#### 5) Putting it together: supervised autonomy as a small state machine

The clean mental model is an agent runtime with a handful of states:

* **Plan / Think** (free-form, no side effects)
* **Dry-run / Preview** (compute diffs, show what would change)
* **Approve** (human or policy decision)
* **Commit** (execute mutating actions)
* **Verify** (check postconditions; detect partial failure)
* **Repair** (retry, compensate, or escalate)

This also clarifies a subtle but important point: *human-in-the-loop is not only “before commit”*. Post-facto validation becomes credible only if you have real undo/containment mechanisms behind it, as argued in GoEx-style runtime proposals. 

### References

1. Eric Horvitz. *Principles of Mixed-Initiative User Interfaces*. CHI, 1999. ([erichorvitz.com][48])
2. Theo Haerder and Andreas Reuter. *Principles of Transaction-Oriented Database Recovery*. ACM Computing Surveys, 1983. ([ACM Digital Library][49])
3. Jim Gray and Andreas Reuter. *Transaction Processing: Concepts and Techniques*. Morgan Kaufmann, 1992. ([Elsevier Shop][57])
4. Shunyu Yao et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. arXiv, 2022. ([arXiv][50])
5. Long Ouyang et al. *Training Language Models to Follow Instructions with Human Feedback*. NeurIPS, 2022. ([NeurIPS Proceedings][58])
6. Reiichiro Nakano et al. *WebGPT: Browser-assisted Question-answering with Human Feedback*. arXiv, 2021. ([arXiv][59])
7. Shishir G. Patil et al. *GoEx: Perspectives and Designs Towards a Runtime for Autonomous LLM Applications*. arXiv, 2024. ([arXiv][52])
8. Microsoft Azure Architecture Center. *Saga Design Pattern*. (Documentation). ([Microsoft Learn][55])
9. Pydantic AI Documentation. *Deferred Tools: Human-in-the-Loop Tool Approval*. (Documentation). ([Pydantic AI][54])

[48]: https://erichorvitz.com/chi99horvitz.pdf?utm_source=chatgpt.com "Principles of Mixed-Initiative User Interfaces - of Eric Horvitz"
[49]: https://dl.acm.org/doi/10.1145/289.291?utm_source=chatgpt.com "Principles of transaction-oriented database recovery"
[50]: https://arxiv.org/abs/2210.03629?utm_source=chatgpt.com "ReAct: Synergizing Reasoning and Acting in Language Models"
[51]: https://arxiv.org/abs/2203.02155?utm_source=chatgpt.com "Training language models to follow instructions with human feedback"
[52]: https://arxiv.org/abs/2404.06921?utm_source=chatgpt.com "[2404.06921] GoEX: Perspectives and Designs Towards a ..."
[53]: https://openreview.net/forum?id=JuwuBUnoJk&utm_source=chatgpt.com "Small Actions, Big Errors — Safeguarding Mutating Steps ..."
[54]: https://ai.pydantic.dev/deferred-tools/ "Deferred Tools - Pydantic AI"
[55]: https://learn.microsoft.com/en-us/azure/architecture/patterns/saga?utm_source=chatgpt.com "Saga Design Pattern - Azure Architecture Center"
[56]: https://ai.pydantic.dev/?utm_source=chatgpt.com "Pydantic AI - Pydantic AI"
[57]: https://shop.elsevier.com/books/transaction-processing/gray/978-0-08-051955-5?utm_source=chatgpt.com "Transaction Processing - 1st Edition"
[58]: https://proceedings.neurips.cc/paper_files/paper/2022/file/b1efde53be364a73914f58805a001731-Paper-Conference.pdf?utm_source=chatgpt.com "Training language models to follow instructions with ..."
[59]: https://arxiv.org/abs/2112.09332?utm_source=chatgpt.com "WebGPT: Browser-assisted question-answering with human feedback"

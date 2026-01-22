## Prompts

Prompts are the agent's control surface: they define intent, constraints, and operating procedure for each model call, and they are the primary way an agent carries "what matters" forward from one step to the next.

### System prompts, developer instructions, and user prompts

Most agent stacks benefit from splitting “what to do” from “what the user said,” and from being explicit about what persists across calls. One useful distinction is between (a) system prompts that may be preserved as part of the message history, and (b) developer-provided instructions that are applied for the current run but are not replayed from prior turns when you pass message history back into the model. Some frameworks make this distinction explicitly: they recommend using an “instructions” channel by default, and using “system prompt” only when you deliberately want earlier system messages preserved across subsequent calls that include message history. ([Pydantic AI][32])

| Layer                  | Typical author                | Primary purpose                                                 | When evaluated                      | Included when you pass prior conversation back to the model                                                                            | What should be inside                                                                | Common failure mode                                                     |
| ---------------------- | ----------------------------- | --------------------------------------------------------------- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| System prompt          | Platform / application        | Establish global rules, safety boundaries, role, and invariants | Every call                          | Often yes (if system messages are part of the stored chat transcript you replay) ([Pydantic AI][32])                                    | Non-negotiables, policy, tool-use constraints, formatting contract                   | Overstuffing; becomes brittle and conflicts with task-specific behavior |
| Developer instructions | Application / agent developer | Define task procedure and style for a specific agent or run     | Every call                          | Typically no for prior turns; only the current agent’s instructions are applied even if you include message history ([Pydantic AI][32]) | Step-by-step method, required checks, domain constraints, output schema expectations | Too verbose; competes with user content and reduces task grounding      |
| User prompt            | End user                      | Provide the request and any user constraints                    | Every call                          | Yes (as part of conversation history)                                                                                                  | User goals, preferences, situational details                                         | Ambiguity; missing constraints; conflicts with system/developer rules   |
| Conversation history   | System-generated              | Provide continuity and references to earlier turns              | Every call where continuity matters | Yes (selected subset) ([Pydantic AI][32])                                                                                               | Prior user messages, prior assistant outputs, tool results the agent must honor      | Unbounded growth; irrelevant history crowds out current task            |

A practical mental model is that the “effective prompt” is the concatenation of these layers plus any tool outputs you feed back in. Because the model does not truly “remember,” everything you want it to condition on must be present in the tokens you send. That makes prompt boundaries an engineering problem: deciding what belongs in each layer, what is allowed to persist, and what must be summarized or externalized.

A useful rule is to treat system prompts as a narrow compatibility layer (policies and invariants), and treat developer instructions as the primary control mechanism for agent behavior. This maps to the explicit recommendation some frameworks make: use “instructions” by default, and only use “system prompt persistence” when you have a concrete reason to keep earlier system messages in the replayed history. ([Pydantic AI][32])

### Conversation history as working context

Conversation history is the simplest form of short-term memory: you resend prior turns so the model can resolve references (“his,” “that issue,” “the second option”) and maintain continuity. Most agent frameworks represent this as an explicit `message_history` (or equivalent) argument, where you pass the subset of prior messages you want the model to see. ([Pydantic AI][32])

In agentic systems, the key decision is not whether to keep history, but how to curate it. A robust approach is to treat history as a structured artifact rather than a raw transcript:

1. Keep a minimal “interaction spine” (user intent, the agent’s commitments, and the latest state).
2. Attach supporting evidence as references (tool outputs, retrieved documents, calculations).
3. Summarize or drop turns that are no longer load-bearing.

Even without a dedicated “context engineering” section, it is worth stating one operational implication here: replaying raw history scales linearly in tokens and cost, and it eventually degrades quality when irrelevant detail dominates. The prompt stack should therefore be designed so that history can be safely truncated without losing correctness: core constraints remain in system/developer layers, and durable state lives outside the transcript.

### Short-term vs. long-term memory

Short-term memory is whatever you include in the current context window: system messages, developer instructions, the user’s latest request, selected conversation history, and any tool outputs. It is fast, simple, and fragile: it disappears after the call unless you explicitly store it.

Long-term memory is information that persists across calls and sessions, and that you retrieve on demand. Historically, research systems explored learned memory modules (for example, Memory Networks and entity-centric recurrent memories), but most production agents implement long-term memory as external storage plus retrieval and summarization policies. ([NeurIPS Proceedings][31])

The practical boundary is not “how long ago did it happen,” but “how often must it be correct.” Examples:

A user’s stable preferences (output format, coding style) are long-term memory candidates, but only if you can store them as normalized facts with provenance and an update policy.

Intermediate reasoning traces or verbose transcripts are rarely good long-term memory because they are noisy, expensive to retrieve, and likely to conflict with newer information.

The most reliable pattern is to convert episodic interactions into durable, typed records: preferences, decisions, tasks, entities, and constraints. Raw transcript can remain available for audit, but retrieval should preferentially use structured summaries.

### Memory and state management with a database

A database-backed memory system is best treated as two separable concerns:

1. A write path that records events with enough structure to support later retrieval and reconciliation.
2. A read path that returns a token-budgeted “memory view” tailored to the current task.

The write path should store more than “messages.” It should store the agent’s evolving state: commitments, open tasks, decisions made, and the provenance of facts (user statement vs. tool output vs. retrieved document). The read path should not blindly replay; it should construct a task-specific brief.

The following snippets illustrate an implementation shape that avoids coupling your storage format to any single agent framework.

```python
# Data model: store raw events, plus optional extracted "facts" with provenance.
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

Role = Literal["system", "developer", "user", "assistant", "tool"]

@dataclass
class MessageEvent:
    conversation_id: str
    ts: datetime
    role: Role
    content: str
    tool_name: Optional[str] = None
    request_id: Optional[str] = None  # correlate tool calls / retries

@dataclass
class MemoryFact:
    conversation_id: str
    ts: datetime
    kind: str               # e.g. "preference", "decision", "entity", "task"
    key: str                # e.g. "output_format"
    value: str              # normalized text or JSON
    source: Literal["user", "tool", "agent"]
    confidence: float       # optional scoring
```

A common read-path pattern is “two-stage memory”: first retrieve candidates (by recency, lexical match, embeddings, or metadata), then compress into a brief that is explicitly scoped to the current request.

```python
def build_memory_view(conversation_id: str, user_request: str, token_budget: int) -> str:
    # 1) Retrieve structured facts with high precision.
    facts = fetch_facts(conversation_id, query=user_request, limit=50)

    # 2) Retrieve a small slice of recent transcript for continuity.
    recent = fetch_recent_messages(conversation_id, limit=12)

    # 3) Produce a compact brief with strict budgeting.
    brief = render_facts(facts) + "\n\n" + render_recent_messages(recent)

    # 4) If too large, compress: drop low-value items and summarize the remainder.
    if estimate_tokens(brief) > token_budget:
        brief = compress(brief, target_tokens=token_budget)

    return brief
```

This design supports an important separation: conversation continuity (recent transcript) and durable memory (facts) can be budgeted and degraded independently. It also makes it easier to enforce correctness policies, such as “prefer tool-sourced facts over user-sourced guesses,” or “expire preferences unless reaffirmed.”

Finally, note the interaction between “instruction-like” content and message history. If your system treats developer instructions as ephemeral per-run control text, you can store them for observability without replaying them as prior messages in future calls. Conversely, if your system relies on replaying system prompts as part of the stored transcript, you must treat that as an explicit compatibility choice because it changes what the model sees when you continue a conversation with message history. ([Pydantic AI][32])

[31]: https://proceedings.neurips.cc/paper/5846-end-to-end-memory-networks.pdf "End-To-End Memory Networks"
[32]: https://ai.pydantic.dev/agents/ "Agents - Pydantic AI"

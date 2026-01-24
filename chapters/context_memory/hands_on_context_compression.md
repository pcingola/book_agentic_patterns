## Hands-On: History Compaction

As conversations grow longer, the accumulated history consumes an increasing share of the context window. Eventually, the history alone can exceed the model's capacity, or fill so much of the window that the model enters "the dumb zone" where performance degrades. History compaction addresses this by summarizing older exchanges while preserving recent context, allowing conversations to continue indefinitely without context overflow.

The `HistoryCompactor` class in `agentic_patterns.core.context.history` implements this pattern. It monitors token usage across conversation turns and, when a configurable threshold is exceeded, uses an LLM to summarize older messages into a compact narrative. This hands-on explores the pattern through `example_history_compaction.ipynb`.

## The Problem: Unbounded History Growth

In a multi-turn conversation, each exchange adds to the history. A simple question-and-answer might consume a few hundred tokens. But after dozens of turns, especially with detailed responses or tool outputs, the history can easily reach tens of thousands of tokens.

Without management, this creates several problems. First, the history eventually exceeds the context window limit, causing API errors. Second, even before that hard limit, models struggle to attend to all the accumulated information effectively. Third, costs increase linearly with context size for many API pricing models.

The notebook demonstrates this with a conversation about microservices architecture:

```python
prompts = [
    "Explain what microservices architecture is.",
    "What are the main benefits?",
    "What are common challenges?",
    "How does it compare to monolithic architecture?",
]
```

Each prompt builds on the previous discussion. Without compaction, the full history must be carried forward. With compaction, older exchanges are summarized while maintaining conversation continuity.

## Configuring the Compactor

The `CompactionConfig` class defines when compaction triggers and what reduction target to aim for:

```python
from agentic_patterns.core.context.history import HistoryCompactor, CompactionConfig

config = CompactionConfig(max_tokens=500, target_tokens=200)
compactor = HistoryCompactor(config=config)
```

The `max_tokens` threshold determines when compaction activates. When the incoming message history exceeds this value, the compactor summarizes older messages. The `target_tokens` value guides how aggressively to compress. The notebook uses artificially low values (500 and 200) to trigger compaction early for demonstration purposes. Production values might be 120,000 and 40,000 for models with large context windows.

The compactor uses tiktoken for accurate token counting rather than character-based estimates. This ensures compaction triggers at the right time regardless of message content.

## History Processors in PydanticAI

PydanticAI agents support history processors: functions that intercept and transform the message history before each agent call. The compactor integrates through this mechanism.

**Production usage** is straightforward. Pass the compactor directly to `get_agent()`:

```python
compactor = HistoryCompactor(config=config)
agent = get_agent(system_prompt="You are a helpful assistant.", history_compactor=compactor)
```

Or create the processor manually:

```python
agent = get_agent(system_prompt="...", history_processor=compactor.create_history_processor())
```

Both approaches wire up the compactor automatically. Compaction happens silently when thresholds are exceeded.

**For this hands-on**, we use a custom wrapper to observe what's happening:

```python
async def capturing_processor(messages):
    """Processor that captures the compacted history sent to agent."""
    global sent_to_agent, compaction_result
    original_tokens = compactor.count_tokens(messages)
    compacted = await compactor.compact(messages)
    compacted_tokens = compactor.count_tokens(compacted)

    sent_to_agent = compacted
    # ... capture compaction stats
    return compacted

agent_with_compaction = get_agent(
    system_prompt="You are a helpful assistant.",
    history_processors=[capturing_processor]
)
```

Note that PydanticAI accepts both `history_processor` (singular, for a single function) and `history_processors` (plural, for a list of functions). The notebook uses the plural form since it passes a custom capturing processor rather than the compactor's built-in processor.

This custom processor wraps `compactor.compact()` and captures before/after statistics for display. Without this instrumentation, you wouldn't see the token reduction happening. The key insight is that the processor receives the accumulated message history before each agent call. It can inspect, transform, or replace that history.

## Observing Compaction in Action

The notebook runs four conversation turns, displaying what happens at each step. The output distinguishes between three views of the history.

**SENT TO AGENT** shows what the model actually receives after compaction. This is what matters for reasoning and context consumption.

**NEW MESSAGES** shows the request/response pair from the current turn. These get appended to the accumulating history.

**UNCOMPRESSED HISTORY** shows the full accumulated history without compaction. This grows unbounded and is kept for reference.

On turn 1, no compaction occurs. The history contains just the initial exchange:

```
TURN 1: Explain what microservices architecture is.

  SENT TO AGENT (1 messages, 94 tokens):
    [0] ModelRequest: SystemPromptPart(...), UserPromptPart(...)

  UNCOMPRESSED HISTORY (2 messages, 467 tokens):
    [0] ModelRequest: SystemPromptPart(...), UserPromptPart(...)
    [1] ModelResponse: TextPart(# Microservices Architecture...)
```

By turn 2, the accumulated history (467 tokens from turn 1 plus the new prompt) exceeds the 500-token threshold, triggering compaction:

```
TURN 2: What are the main benefits?

  *** COMPACTION: 3 msgs (510 tokens) -> 2 msgs (267 tokens) ***

  SENT TO AGENT (2 messages, 267 tokens):
    [0] ModelRequest: UserPromptPart(This session is being continued from a previous co...)
    [1] ModelRequest: UserPromptPart(What are the main benefits?...)
```

The compacted history replaces the original exchange with a summary message. This summary provides context for the model to continue the conversation without replaying the full dialogue.

## The Compaction Summary

When compaction occurs, older messages are summarized by an LLM into a concise narrative. This summary is wrapped in a continuation prompt:

```python
SUMMARY_WRAPPED = """This session is being continued from a previous conversation that ran out of context. \
The conversation is summarized below:

{summary}

Please continue the conversation from where we left it off without asking the user any further questions. \
Continue with the last task that you were asked to work on, if any, otherwise just wait for the user's next input.
"""
```

The wrapper provides instruction to the model about how to interpret the summary and continue naturally. The model doesn't know that compaction occurred; it simply sees a summary of prior context followed by the current prompt.

The summarization itself uses a separate LLM call:

```python
SUMMARIZATION_REQUEST_PROMPT = """Summarize the following conversation concisely, preserving key information,
decisions made, and important context that would be needed to continue the conversation. Focus on facts
and outcomes rather than the back-and-forth dialogue. Avoid adding a markdown header.

Conversation:
{conversation}

Summary:"""
```

This prompt instructs the summarizer to preserve what matters for conversation continuity: key information, decisions, and context. The back-and-forth dialogue structure is collapsed into facts and outcomes.

## Bounded vs Unbounded History

The critical observation from the notebook output is the divergence between what the agent sees and what accumulates.

After four turns, the uncompressed history has grown to 8 messages consuming 2,293 tokens. But what gets sent to the agent remains bounded at 2 messages (summary plus current prompt) consuming around 370 tokens.

```
TURN 4: How does it compare to monolithic architecture?

  *** COMPACTION: 7 msgs (1350 tokens) -> 2 msgs (373 tokens) ***

  SENT TO AGENT (2 messages, 373 tokens):
    [0] ModelRequest: UserPromptPart(This session is being continued...)
    [1] ModelRequest: UserPromptPart(How does it compare to monolithic architecture?...)

  UNCOMPRESSED HISTORY (8 messages, 2293 tokens):
    [0] ModelRequest: SystemPromptPart(...), UserPromptPart(...)
    [1] ModelResponse: TextPart(# Microservices Architecture...)
    ... (6 more messages)
```

The conversation can continue indefinitely. Each turn summarizes all prior context, keeping the sent history bounded while the logical conversation grows.

## Tool Call Pairing

The implementation handles a subtle constraint with tool calls. When a message contains a tool return, the preceding tool call must be preserved with it. The OpenAI API returns an error if tool returns appear without their corresponding calls.

The `_find_safe_compaction_boundary` method ensures compaction never orphans tool returns:

```python
def _find_safe_compaction_boundary(self, messages: list[ModelMessage]) -> int:
    # If the last message has ToolReturnPart, we must also keep the message
    # with the corresponding ToolCallPart
    if self._has_tool_return_part(messages[keep_from]):
        if keep_from > 0 and self._has_tool_call_part(messages[keep_from - 1]):
            keep_from -= 1
        else:
            return -1  # Skip compaction, will retry next turn
```

If no safe boundary exists, compaction is deferred to the next turn when the tool call/return pair can be included together.

## Fallback Behavior

When LLM summarization fails or isn't available, the compactor falls back to truncation. It preserves the head and tail of the conversation with a marker indicating removed content:

```python
def _truncate_for_fallback(self, text: str, max_tokens: int) -> str:
    # Keep head and tail, note removed portion
    truncated = f"{head}\n\n[... {removed_count} tokens removed ...]\n\n{tail}"
    return f"[Previous conversation (truncated)]:\n{truncated}"
```

This ensures the system degrades gracefully. Truncation is less effective than summarization but maintains conversation continuity.

## Key Takeaways

History compaction separates what the conversation has accumulated from what the model sees. The full logical history grows unbounded while the effective context stays bounded through summarization.

Configuration involves two parameters: `max_tokens` triggers compaction, `target_tokens` guides reduction. Set these based on your model's context window and the balance between context preservation and cost.

In production, pass `history_compactor=compactor` to `get_agent()` for automatic integration. The custom processor in this hands-on exists only to observe what's happening; production code doesn't need it.

Compaction uses LLM summarization to preserve semantic content. The summary captures key information and decisions rather than replaying dialogue structure. A fallback to truncation ensures graceful degradation.

Tool call/return pairing is preserved automatically. The compactor finds safe boundaries that don't orphan tool returns, deferring compaction when necessary.

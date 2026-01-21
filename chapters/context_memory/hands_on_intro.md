# Hands-On: Introduction

The preceding sections introduced the concepts that shape effective context management: prompt layers that separate identity from task control, compression techniques that bound token consumption, and the principle of intentional loss when context budgets are exceeded. The hands-on exercises that follow translate these concepts into working code using the `agentic_patterns` core library.

The first exercise explores prompt layers through practical examples. You will configure agents with system prompts, developer instructions, and observe how each layer behaves across multi-turn conversations with message history. This demonstrates the separation between persistent identity and per-run control that production agents require.

The second exercise addresses tool output management. Many tools return large results: database queries, log searches, API responses. The `@context_result` decorator truncates these outputs automatically, saving full results to the workspace while returning compact previews to the model. You will see how type-aware truncation preserves coherent previews for CSV, JSON, and log data without overwhelming the context window.

The third exercise implements history compaction for long-running conversations. The `HistoryCompactor` monitors token usage and summarizes older exchanges when thresholds are exceeded, keeping the effective context bounded while conversation history grows unbounded. Together, these exercises demonstrate the layered approach to context engineering: control what enters through prompts, limit what tools contribute, and compress what accumulates over time.

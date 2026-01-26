## Context engineering: why sub-agents help

Sub-agents are a powerful context-engineering tool. Large, monolithic prompts tend to accumulate instructions, examples, tool schemas, intermediate reasoning, and conversation history until the model's effective context utilization degrades. Sub-agents mitigate this by enforcing context locality.

Each sub-agent receives only the information relevant to its task. Irrelevant instructions, historical turns, and tool definitions are excluded by construction. This leads to three practical benefits. First, token budgets are used more efficiently, since each agent operates near the minimum viable context. Second, reasoning quality improves, as the model is not distracted by unrelated constraints. Third, systems become easier to debug, because failures can be isolated to a specific sub-agent with a well-defined responsibility.

From a systems perspective, sub-agents act as an explicit form of context compression. Instead of summarizing or pruning text, the system restructures the problem so that less context is needed in the first place. This is often more robust than aggressive summarization, especially for tasks that require precise tool usage or domain-specific instructions.

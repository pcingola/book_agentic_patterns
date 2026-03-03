## Hands-On: Tree of Thought Reasoning

Tree of Thought extends Chain-of-Thought reasoning by exploring multiple reasoning paths simultaneously. Instead of following a single linear chain of reasoning, the model generates multiple candidate solutions, evaluates them, and selectively expands the most promising ones. This deliberate exploration prevents premature commitment to suboptimal solutions.

This hands-on explores Tree of Thought using `example_tree_of_thought.ipynb`, demonstrating how structured exploration of alternatives leads to better design decisions.

### The Problem: Linear Reasoning Commits Too Early

When solving complex problems with Chain-of-Thought, the model follows a single reasoning path from start to finish. If the initial direction is suboptimal, the model may reach a solution that works but misses better alternatives. Consider this systems design problem:

```
Design a file deduplication system for a cloud storage service.
Handle millions of files, detect duplicates to save storage costs,
process uploads quickly, minimize false positives, handle files from 1KB to 5GB.
```

With linear reasoning, the model might immediately commit to the first approach that comes to mind (e.g., "use SHA-256 hashing") without considering alternatives. If this approach has a deal-breaker limitation (e.g., poor performance on large files), we discover it too late.

### The Solution: Structured Exploration

Tree of Thought structures reasoning as a search problem. The model generates multiple candidate solutions, evaluates each on relevant criteria, prunes weak candidates, and expands strong ones with additional detail. This exploration happens before committing to a final design.

The pattern follows four phases: generation, evaluation, expansion, and selection. Each phase builds on the previous one, progressively refining the solution space.

### Example: File Deduplication System Design

The notebook demonstrates Tree of Thought applied to a realistic systems design problem. Let's walk through each phase.

#### Phase 1: Generate Multiple Approaches

Instead of asking for "the best" deduplication approach, we explicitly request multiple alternatives:

```python
from agentic_patterns.core.agents import get_agent, run_agent

problem = """Design a file deduplication system for a cloud storage service.
Requirements: [...]
Propose different deduplication approaches."""

prompt_generate = f"""{problem}

Generate exactly 3 different deduplication approaches. For each approach, provide:
- A name (Approach A, B, C)
- The core algorithm/technique used
- Brief description (2-3 sentences) of how it works"""

agent = get_agent()
agent_run_1, nodes_1 = await run_agent(agent, prompt_generate)
```

This prompt produces three distinct approaches, likely covering different algorithmic strategies. For example, the model might generate:

- Approach A: Whole-file hashing (SHA-256) - compute hash of entire file, store in database, compare on upload
- Approach B: Content-defined chunking (Rabin fingerprinting) - split files into variable-sized chunks, deduplicate at chunk level
- Approach C: Perceptual hashing - extract content fingerprint, detect near-duplicates using similarity threshold

Each approach represents a different point in the design space. By generating multiple options upfront, we avoid anchoring to the first idea.

#### Phase 2: Evaluate Each Approach

With three candidates, we evaluate them against system requirements:

```python
from agentic_patterns.core.agents.utils import nodes_to_message_history

message_history = nodes_to_message_history(nodes_1)

prompt_evaluate = """Evaluate each of the 3 approaches you generated.

For each approach, rate it on these criteria (1-5 scale, 5 is best):
1. Accuracy (avoiding false positives/negatives)
2. Performance (speed of duplicate detection)
3. Storage overhead (metadata storage requirements)
4. Scalability (handles millions of files)

Provide a total score and brief justification for each rating.
Then rank the approaches from best to worst."""

agent_run_2, nodes_2 = await run_agent(agent, prompt_evaluate, message_history=message_history)
```

The evaluation criteria are specific and measurable. This forces the model to reason about trade-offs rather than picking arbitrarily. The model might score:

- Approach A: Accuracy 5/5, Performance 4/5, Storage 5/5, Scalability 4/5 → Total 18/20
- Approach B: Accuracy 5/5, Performance 3/5, Storage 3/5, Scalability 5/5 → Total 16/20
- Approach C: Accuracy 3/5, Performance 4/5, Storage 4/5, Scalability 4/5 → Total 15/20

Note how `message_history` carries forward the conversation context. Each agent turn builds on previous turns, maintaining the tree structure.

#### Phase 3: Expand the Top Approaches

Based on evaluation scores, we prune the lowest-ranked approach and expand the top two:

```python
message_history = nodes_to_message_history(nodes_2)

prompt_expand = """Take the TOP 2 approaches from your ranking.
For each of these two approaches, provide a detailed implementation design:

For each approach, specify:
1. Data structures needed (what gets stored, indexed)
2. Upload flow (step-by-step what happens when a file is uploaded)
3. Query flow (how to check if a file is a duplicate)
4. Storage requirements (rough estimate for 1 million files)"""

agent_run_3, nodes_3 = await run_agent(agent, prompt_expand, message_history=message_history)
```

Pruning is a key Tree of Thought concept. We don't waste computation expanding all branches. Instead, we allocate detail where it matters: the most promising candidates.

The expansion prompts for concrete implementation details. This reveals hidden complexity and edge cases. For example, whole-file hashing might seem simple until you consider how to handle 5GB files without loading them entirely into memory. Content-defined chunking might seem elegant until you calculate the storage overhead for chunk metadata.

These details matter for final selection but would be expensive to generate for all three initial approaches. By evaluating first and expanding later, we explore efficiently.

#### Phase 4: Final Selection

With detailed implementations for the top two approaches, we can make an informed decision:

```python
message_history = nodes_to_message_history(nodes_3)

prompt_final = """Now that you have detailed implementations for the top 2 approaches:

1. Identify edge cases or failure modes for each approach
2. Consider operational complexity (monitoring, debugging, maintenance)
3. Think about how each handles the file size range (1KB to 5GB)
4. Choose the final winner
5. Explain why this approach is superior given the implementation details"""

agent_run_4, nodes_4 = await run_agent(agent, prompt_final, message_history=message_history)
```

The final evaluation goes deeper than the initial scoring. It considers edge cases, operational concerns, and how the system behaves across the required file size range. This level of analysis only makes sense after seeing the implementation details.

The model might conclude that whole-file hashing (Approach A) wins because it's simpler to implement and operate, has perfect accuracy, and acceptable performance with streaming hashing for large files. Content-defined chunking (Approach B) offers better deduplication for similar files but adds significant complexity that doesn't justify the storage savings for this use case.

### The Tree Structure

The execution forms a tree:

```
Problem Statement
+-- Approach A (whole-file hash)
|   +-- Evaluation: 18/20
|   +-- Detailed Implementation
|       +-- Final Analysis
+-- Approach B (chunking)
|   +-- Evaluation: 16/20
|   +-- Detailed Implementation
|       +-- Final Analysis
+-- Approach C (perceptual)
    +-- Evaluation: 15/20 [pruned]
```

Approach C was pruned after evaluation. Approaches A and B were expanded. Final analysis compared the expanded approaches to select a winner.

This tree structure is managed explicitly through prompt engineering. Unlike Chain-of-Thought, where reasoning is implicit, Tree of Thought requires explicit instructions to generate branches, evaluate them, and decide which to expand.

### Implementation Tips

**Define explicit evaluation criteria**: Don't ask "which is better?" Ask "rate on accuracy (1-5), performance (1-5), complexity (1-5)." Concrete criteria produce consistent evaluations.

**Control branching width and depth**: Generating 3 branches with 2 levels of depth (like our example) is manageable. Generating 10 branches with 5 levels becomes expensive quickly.

**Prune strategically**: Pruning saves computation but may discard good ideas. In our example, we kept the top 2 of 3 approaches (67% retention). For critical decisions, consider keeping more branches or using multiple pruning stages.

**Structured prompts**: Each phase (generate, evaluate, expand, select) uses a carefully structured prompt that tells the model exactly what to produce. Loose prompts lead to inconsistent outputs that break downstream phases.

### Key Takeaways

Tree of Thought requires four phases: generation, evaluation, expansion, and selection. Our example used 4 agent turns with 3 initial branches -- roughly 3-4x the token cost and latency of linear Chain-of-Thought reasoning. This cost is justified for high-stakes design decisions where early commitment to a suboptimal approach is expensive to reverse. For problems with obvious solutions or low stakes, linear reasoning suffices.

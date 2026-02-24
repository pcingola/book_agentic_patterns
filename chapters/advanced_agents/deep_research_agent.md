## Deep Research Agent

A deep research agent is an iterative retrieve–reason–verify loop that accumulates evidence, detects gaps and conflicts, and stops only when it can justify coverage and confidence within explicit budgets.

### Why “deep research” is a distinct agent pattern

Basic RAG answers a question with a single retrieval step and a single synthesis pass. In practice, “research” tasks are rarely single-hop: what you should search for depends on what you just learned, and what you just learned may be incomplete, contradictory, or too low-quality to cite. A deep research agent makes that dependency explicit by turning retrieval into a controlled, stateful process.

Conceptually, it composes patterns introduced earlier in the book: planning (to decide what to look for next), tool use (to retrieve from heterogeneous sources), structured memory (to store evidence and unresolved questions), critique/verification (to test claims against sources), and budgeting/stopping (to prevent infinite loops). IRCoT and related work formalize the key insight: interleaving intermediate reasoning steps with retrieval improves both retrieval quality and final accuracy for multi-step questions, because each intermediate conclusion can become the next query. ([arXiv][1])

### The core loop: plan, retrieve, gap, re-query, synthesize, verify, stop

A practical implementation treats “research” as a state machine over a persistent research state. The agent alternates between two modes.

In exploration mode, it expands coverage: it decomposes the goal into subquestions, drafts candidate queries, retrieves, and extracts candidate claims with supporting snippets. Self-Ask is a useful mental model here: the agent keeps asking follow-up questions until it has enough to answer the original. ([ofir.io][2])

In consolidation mode, it reduces uncertainty: it looks for contradictions, missing citations, weak sources, and ambiguous statements; then it issues targeted retrieval to resolve them. Methods like query rewriting are often essential here: the best retrieval query is frequently not the user’s question but a rewritten, more “retriever-friendly” form derived from the agent’s current hypothesis and gaps. ([ACL Anthology][3])

A minimal “Python-like” skeleton looks like this:

```python
def deep_research(question, tools, budgets):
    state = ResearchState.new(question, budgets)

    while not should_stop(state):
        if state.mode == "explore":
            plan = propose_subquestions_and_queries(state)
            results = tools.search(plan.queries)
            state = ingest_results(state, results)
            state = extract_claims_and_evidence(state, results)
            state = update_gaps(state)
            state = maybe_switch_to_consolidate(state)

        elif state.mode == "consolidate":
            issues = detect_conflicts_and_weak_support(state)
            rewrites = rewrite_queries_from_issues(state, issues)
            results = tools.search(rewrites)
            state = ingest_results(state, results)
            state = resolve_conflicts(state, results)
            state = run_verification(state)  # internal + external checks
            state = maybe_switch_to_explore(state)

    return synthesize_report(state)
```

This loop is a ReAct-style interleaving of “thinking steps” and “actions” (tool calls), except the unit of work is evidence accumulation rather than task execution. ([arXiv][4])

### Research state: evidence as a first-class object

The most important engineering choice is the state representation. Treat every downstream artifact as derived from two things: claims (what you intend to say) and evidence (why you believe it). Storing only raw retrieved text is insufficient; storing only a final summary loses traceability.

A compact representation that scales is:

```python
class Evidence:
    source_id: str          # URL, doc id, or internal reference
    title: str
    quoted_span: str        # short excerpt used for grounding
    retrieved_at: datetime
    reliability: float      # heuristic or model-assigned
    notes: str              # why it's relevant

class Claim:
    text: str
    support: list[Evidence]
    status: str             # "supported", "uncertain", "disputed"
    confidence: float
    dependencies: list[str] # ids of other claims

class ResearchState:
    question: str
    subquestions: list[str]
    claims: dict[str, Claim]
    open_gaps: list[str]        # missing facts, definitions, citations
    conflicts: list[str]        # pointers to incompatible claims
    query_history: list[str]
    mode: str                   # "explore" | "consolidate"
    budgets: Budgets            # tokens, tool calls, time, citations
```

Two practical notes. First, store “quoted spans” (short excerpts) rather than entire documents; this keeps later synthesis grounded and makes verification cheaper. Second, treat “open gaps” as actionable items that generate the next queries; gaps are the agent’s internal backlog.

### Gap discovery and question generation

Gap discovery is the mechanism that makes the loop self-improving. It can be implemented as a deterministic heuristic layer plus a model-based critic.

Heuristically, gaps appear when a claim has no evidence, only low-quality evidence, outdated evidence, or evidence that supports only part of the statement. They also appear when the agent’s plan expects a subanswer that never materializes, or when multiple sources disagree about a key fact.

Model-based gap discovery uses targeted prompts such as “What would a skeptical reviewer ask for each claim?” This is essentially turning critique into query generation, closely related to the “verification questions” step in Chain-of-Verification. ([arXiv][5])

### Conflict resolution: triangulation instead of “majority vote”

Conflicts are normal in open-world research. The agent needs an explicit policy for resolving them that does not collapse into “pick the most fluent answer.”

A robust approach is triangulation with provenance-aware ranking. The agent clusters evidence by source, date, and methodology; then it prefers primary sources over summaries, more recent sources over outdated ones when recency matters, and sources with transparent methods over opaque claims. If it cannot resolve a conflict, it should preserve the disagreement explicitly in the output by presenting both claims with their best evidence.

When conflicts are subtle, self-consistency can help at the reasoning layer: sample multiple reasoning paths, then check whether they converge on the same claim set and which claims remain unstable. This is not a substitute for evidence, but it is a useful detector for “fragile conclusions” that need more retrieval. ([arXiv][6])

### Verification: separating drafting from checking

Deep research benefits from a strict separation between drafting and verification. The failure mode you are avoiding is “the model persuades itself” by re-reading its own prose.

Chain-of-Verification provides a practical template: draft a candidate answer, generate verification questions from that draft, answer those questions independently (ideally with fresh retrieval), then revise the draft. ([arXiv][5])

In a research agent, verification runs at the claim level:

```python
def run_verification(state):
    for claim in state.claims.values():
        if claim.status == "supported":
            continue
        questions = make_verification_questions(claim)
        answers = [answer_with_retrieval(q) for q in questions]
        claim = update_claim_status_from_checks(claim, answers)
    return state
```

This “claim-level CoVe” is also where you enforce citation discipline: a claim cannot become “supported” unless it has at least one acceptable evidence item, and high-impact claims may require multiple independent sources.

### Stopping criteria: confidence, coverage, and diminishing returns

Without explicit stopping, deep research agents either loop forever or stop arbitrarily. A practical stopping policy combines three signals.

Coverage means every subquestion is addressed or explicitly marked “unknown.” Confidence means every high-impact claim is supported with adequate evidence and passes verification. Diminishing returns means recent iterations are not reducing the number of gaps/conflicts meaningfully relative to cost.

A simple implementation is:

```python
def should_stop(state):
    if state.budgets.exhausted():
        return True
    if not state.open_gaps and not state.conflicts and state.coverage_ok():
        return True
    if state.progress_rate(window=3) < state.budgets.min_progress:
        return True
    return False
```

The key is that “budget exhausted” produces a different kind of output: the agent should return the best supported partial synthesis, clearly labeling unresolved gaps and conflicts.

### References to add to references.md

1. Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan, Yuan Cao. *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR, 2023. [https://arxiv.org/abs/2210.03629](https://arxiv.org/abs/2210.03629)
2. Ofir Press, Noah A. Smith, Mike Lewis. *Measuring and Narrowing the Compositionality Gap in Language Models (Self-Ask)*. arXiv, 2022. [https://ofir.io/self-ask.pdf](https://ofir.io/self-ask.pdf)
3. Harsh Trivedi, Niranjan Balasubramanian, Tushar Khot, Ashish Sabharwal. *Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions*. ACL, 2023. [https://arxiv.org/abs/2212.10509](https://arxiv.org/abs/2212.10509)
4. Xuezhi Wang, Jason Wei, Dale Schuurmans, Quoc V. Le, Ed H. Chi, Sharan Narang, Aakanksha Chowdhery, Denny Zhou. *Self-Consistency Improves Chain of Thought Reasoning in Language Models*. arXiv, 2022. [https://arxiv.org/abs/2203.11171](https://arxiv.org/abs/2203.11171)
5. Saurabh Dhuliawala, Monica Agrawal, Ari Holtzman, Jiacheng Xu, Luke Zettlemoyer, Yejin Choi. *Chain-of-Verification Reduces Hallucination in Large Language Models*. ICLR, 2024. [https://arxiv.org/abs/2309.11495](https://arxiv.org/abs/2309.11495)
6. Xinyu Ma, Jiarui Zhang, Minwei Feng, Tianyu Zhang, Yuexian Zou, Dong Yu. *Query Rewriting for Retrieval-Augmented Large Language Models*. EMNLP, 2023. [https://arxiv.org/abs/2305.14283](https://arxiv.org/abs/2305.14283)

[1]: https://arxiv.org/abs/2212.10509?utm_source=chatgpt.com "Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions"
[2]: https://ofir.io/self-ask.pdf?utm_source=chatgpt.com "Measuring and Narrowing the Compositionality Gap in ..."
[3]: https://aclanthology.org/2023.emnlp-main.322.pdf?utm_source=chatgpt.com "Query Rewriting for Retrieval-Augmented Large Language ..."
[4]: https://arxiv.org/abs/2210.03629?utm_source=chatgpt.com "ReAct: Synergizing Reasoning and Acting in Language Models"
[5]: https://arxiv.org/abs/2309.11495?utm_source=chatgpt.com "Chain-of-Verification Reduces Hallucination in Large ..."
[6]: https://arxiv.org/abs/2203.11171?utm_source=chatgpt.com "Self-Consistency Improves Chain of Thought Reasoning in Language Models"

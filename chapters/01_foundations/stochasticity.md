## Determinism vs stochasticity

Agentic systems sit at the boundary between deterministic software and stochastic model behavior, so you design for *reproducibility* rather than pretending you can get perfect determinism.

### LLMs are stochastic (even when you try to “turn it off”)

An LLM call is not “a function” in the strict software sense. Even if the model were held fixed, generation typically involves sampling from a distribution; lowering temperature just sharpens that distribution. Many production model APIs also involve infrastructure-level nondeterminism (e.g., backend changes, load balancing, numerical differences), which means that setting “temperature = 0” is best understood as “reduce randomness,” not “prove determinism.” This is explicitly called out in agent-oriented tooling docs: even with temperature set to 0.0, outputs are not guaranteed to be fully deterministic. ([Pydantic AI][4])

Two practical implications follow:

First, you should separate **semantic determinism** (“the agent makes the same decision”) from **token determinism** (“the exact same text”). Token determinism is fragile and often not worth pursuing except for narrow regression tests.

Second, you should treat stochasticity as a design constraint: once you add tools, retries, multi-step plans, and multi-agent delegation, tiny variations compound into divergent trajectories. The goal becomes: constrain the degrees of freedom that matter, and validate behavior with tests that tolerate harmless variation.

A minimal “variance control” configuration typically fixes the parameters that influence sampling, and records run metadata so you can reason about drift when it happens:

```python
request = {
    "model": model_name,
    "temperature": 0.0,
    "top_p": 1.0,
    # If your provider supports it, fix a seed for higher repeatability.
    "seed": 42,
}

resp = llm.generate(prompt, **request)

# Store enough metadata to diagnose drift later (backend revisions, fingerprints, etc.).
run_log = {
    "prompt_hash": sha256(prompt.encode()).hexdigest(),
    "params": request,
    "provider_metadata": resp.metadata,  # e.g., fingerprint/revision identifiers if available
}
```

### Testing and validation strategies for stochastic agents

The key move is to stop thinking “unit test the LLM” and start thinking “test the agent’s contract.” In practice, that means composing multiple layers of checks, from fully deterministic to probabilistic, and designing your architecture so those layers are easy to apply.

#### 1) Make the boundaries deterministic: validate *structure* before you judge *content*

Most agent failures in production are not “the answer is slightly different,” but “the agent emitted something unparseable,” “it called the wrong tool,” “it violated permissions,” or “it produced an object that breaks downstream code.” Your first testing layer should therefore be deterministic validation of interfaces: schema checks, tool-call argument validation, invariants, and policy constraints.

```python
# Example: validate that the model output conforms to a strict schema,
# and fail fast with actionable errors.
output = agent.run(input)

validate_schema(output)           # types, required fields, enums
validate_invariants(output)       # domain rules
validate_policy(output)           # permissions / tool allowlist constraints
```

This is also where “structured outputs” and typed contracts pay off: they convert a fuzzy generative step into something you can deterministically accept/reject.

#### 2) Record/replay to isolate nondeterminism (and make regressions cheap)

Stochasticity becomes unmanageable when failures are not reproducible. A standard pattern is to record *external effects* (tool calls, retrieved documents, database rows, HTTP responses) and replay them in tests. That pins the environment so you can focus on the agent logic and prompts.

```python
def tool_call(tool_name, args):
    if replay_mode:
        return cassette.read(tool_name, args)
    result = real_tool_call(tool_name, args)
    cassette.write(tool_name, args, result)
    return result
```

With this, you can run “golden” scenarios where tools behave identically run-to-run, and any change comes from prompts/model behavior (or your scaffolding).

#### 3) Use deterministic test doubles for fast iteration

A second accelerator is a deterministic “fake model” used in unit tests that returns scripted outputs (or outputs derived from simple rules). The point is not to approximate the LLM; it is to make agent control flow testable: branching, retries, fallback behavior, tool orchestration, and state handling.

```python
class FakeModel:
    def generate(self, prompt, **params):
        if "need_tool" in prompt:
            return {"tool": {"name": "search", "args": {"q": "..."}}}
        return {"final": "stubbed answer"}
```

This lets you test the *agent as software* with the speed and determinism you expect from normal unit tests.

#### 4) Treat evaluation as a first-class harness, not ad-hoc assertions

For end-to-end behavior, you typically need evaluation infrastructure: curated datasets, repeatable runs, and scoring. Evaluation frameworks aimed at agentic systems emphasize running many scenarios and attaching evaluators that produce scores/labels/assertions, including “LLM-as-judge” when deterministic checks are insufficient. ([Pydantic AI][5])

A practical rubric pattern is: deterministic checks first, then an LLM judge for the remaining ambiguity, with guidance to keep the judge itself as stable as possible (for example, low temperature) and to combine multiple judges when needed. ([Pydantic AI][6])

```python
case = {"input": "...", "expected_facts": [...], "constraints": [...]}
out = agent.run(case["input"])

assert contains_required_facts(out, case["expected_facts"])   # deterministic
assert violates_no_constraints(out, case["constraints"])      # deterministic

score = llm_judge(
    rubric="""
    Rate correctness and completeness. Penalize hallucinated claims.
    """,
    candidate=out,
    reference=case.get("reference"),
)
assert score >= 0.8
```

The important engineering point is that “evaluation” is not only for model selection. It is your regression suite for prompt edits, tool changes, and dependency upgrades.

#### 5) Prefer behavioral assertions over exact-match snapshots

Exact text snapshots are brittle. When you *must* snapshot, snapshot the right thing: tool sequences, structured outputs, and key decisions. If you need to compare free text, use normalization and tolerance: compare extracted facts, compare JSON fields, or compare embeddings / semantic similarity with thresholds (carefully, and ideally with a deterministic baseline).

#### 6) Design for controlled nondeterminism in production

Even if your tests are solid, production will still face drift. The production counterpart of your testing strategy is: log the parameters and environment identifiers; keep prompts versioned; isolate tools behind stable contracts; and monitor outcome metrics so you detect behavior changes quickly. If your provider supports seeds and fingerprints, treat them as debugging aids, not as a determinism guarantee. ([OpenAI Cookbook][7])

## References

1. Pydantic AI Documentation. *Model settings (temperature) — note on nondeterminism*. 2025. ([Pydantic AI][4])
2. Pydantic Evals Documentation. *Overview and evaluators (including LLM judge best practices)*. 2025. ([Pydantic AI][5])
3. Pydantic Evals Documentation. *LLM Judge*. 2025. ([Pydantic AI][6])
4. OpenAI Cookbook. *Reproducible outputs with the seed parameter*. 2023. ([OpenAI Cookbook][7])

[4]: https://ai.pydantic.dev/api/settings/ "pydantic_ai.settings"
[5]: https://ai.pydantic.dev/evals/ "Pydantic Evals"
[6]: https://ai.pydantic.dev/evals/evaluators/llm-judge/ "LLM Judge"
[7]: https://cookbook.openai.com/examples/reproducible_outputs_with_the_seed_parameter "How to make your completions outputs consistent with the seed parameter"

## Adversarial & Debate Agents

Adversarial and debate agents use structured opposition to surface hidden failure modes, pressure-test assumptions, and converge on more reliable decisions than a single-pass generator.

### Why adversarial composition works

Most agent failures in complex tasks are not “no answer” failures; they are “plausible but wrong” failures. The core idea is to split responsibilities across roles that are incentivized to disagree: one role proposes, another attacks, and a third adjudicates. This creates a controlled form of internal skepticism that is difficult to elicit from a single monolithic prompt, and it turns “uncertainty” into actionable follow-up questions.

In practice, these agents compose patterns from earlier chapters, including critique-and-revise loops, tool-grounded claims, and explicit stopping criteria. Multi-agent debate has been shown to improve reasoning and factuality on several benchmark tasks when agents exchange arguments over multiple rounds.

### Red-team agents

A red-team agent is a specialized adversary whose output is not the final solution, but the strongest set of challenges that could make the solution fail. The useful mental model is gap-driven test generation: given an answer draft or plan, the red-team agent searches for missing evidence, unstated assumptions, ambiguity, and edge cases, and then produces targeted probes that force the main agent either to justify, to retrieve evidence, or to revise.

A reliable red-team agent is constrained by a threat model. Without an explicit threat model, the red-team will either under-attack or over-attack. Modern red-teaming practice emphasizes matching tests to the system’s intended use, interfaces, and attacker capabilities. The red-team interaction is best structured as a two-stage contract: first generate attacks, then score whether each attack is answered with evidence. If evidence is missing, the system creates a concrete retrieval action or experiment rather than allowing debate to continue abstractly.

```python
red_team = RedTeamAgent(
    threat_model="Data migration risks: data loss, downtime, performance regression."
)
result = await red_team.analyze(result=decision, context=reasoning)
for ch in result.challenges:
    print(f"[{ch.severity}] {ch.claim}")
    print(f"  Attack: {ch.attack}")
    print(f"  Required evidence: {ch.required_evidence}")
```

### Debate agents

Debate agents extend red-teaming by running an explicit, turn-based argument protocol. The canonical form uses two opposing sub-agents and an arbiter. One agent defends a candidate answer or plan, the other attempts to falsify it, and the arbiter decides what survives based on evidence and internal consistency. This structure follows the intuition of debate-based oversight: when direct evaluation is hard, adversarial argumentation highlights the crux of disagreement.

To make debate productive rather than verbose, three constraints matter. Arguments are anchored to explicit claims with supporting evidence and rebuttals. The arbiter follows an evidence-first decision rule, accepting claims only when supported and rejecting claims contradicted by evidence. The system enforces diversity across debating agents, for example by varying prompts or personas, to avoid convergence by collusion.

```python
debate = DebateOrchestrator(max_rounds=3)
result = await debate.run(proposal)

for i, rnd in enumerate(result.rounds):
    print(f"Round {i + 1}:")
    print(f"  Advocate: {rnd.advocate.position}")
    print(f"  Critic:   {rnd.critic.position}")

print(f"Decision: {result.verdict.decision}")
print(f"Open questions: {result.verdict.open_questions}")
```

Each round, the arbiter checks whether the debate has converged. If `verdict.is_sufficient` is true, no further rounds are needed; otherwise the next round opens with the full prior transcript so each side can address what was contested.

### Persona simulation as controlled adversarial diversity

Persona simulation operationalizes diversity of critique by encoding viewpoints as role descriptions rather than ad hoc prompt styles. Each persona represents a stable role in the target domain, capturing the constraints an expert in that role would actually apply. The intent is not to imitate individuals but to encode the lens through which a given role evaluates evidence.

In practice, a persona is a short text description passed as `advocate_prompt` or `critic_prompt`. A startup CTO and a database reliability engineer will weigh the same proposal very differently:

```python
debate = DebateOrchestrator(
    advocate_prompt="You are a startup CTO who values developer velocity and schema flexibility above all else.",
    critic_prompt="You are a database reliability engineer who has managed PostgreSQL clusters at scale for 10 years.",
    max_rounds=2,
)
result = await debate.run(proposal)
```

For repeatability, persona descriptions can be stored as plain text files in a `personas/` directory and loaded at runtime. This makes them auditable and easy to evolve as the system’s scope changes.

Personas should evolve based on observed system failures. By clustering historical errors by root cause, you can refine persona descriptions to cover blind spots that repeatedly escape critique. This connects persona simulation to rubric-based evaluation and error taxonomies introduced elsewhere in the book.

### Hands-on

See `example_debate.ipynb` for a working notebook that demonstrates a basic advocate-vs-critic debate and red-team analysis of the resulting verdict.

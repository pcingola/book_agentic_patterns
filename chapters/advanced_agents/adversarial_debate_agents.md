## Adversarial & Debate Agents

Adversarial and debate agents use structured opposition to surface hidden failure modes, pressure-test assumptions, and converge on more reliable decisions than a single-pass generator.

### Why adversarial composition works

Most agent failures in complex tasks are not “no answer” failures; they are “plausible but wrong” failures. The core idea is to split responsibilities across roles that are incentivized to disagree: one role proposes, another attacks, and a third adjudicates. This creates a controlled form of internal skepticism that is difficult to elicit from a single monolithic prompt, and it turns “uncertainty” into actionable follow-up questions.

In practice, these agents compose patterns from earlier chapters, including critique-and-revise loops, tool-grounded claims, and explicit stopping criteria. Multi-agent debate has been shown to improve reasoning and factuality on several benchmark tasks when agents exchange arguments over multiple rounds.

### Red-team agents

A red-team agent is a specialized adversary whose output is not the final solution, but the strongest set of challenges that could make the solution fail. The useful mental model is gap-driven test generation: given an answer draft or plan, the red-team agent searches for missing evidence, unstated assumptions, ambiguity, and edge cases, and then produces targeted probes that force the main agent either to justify, to retrieve evidence, or to revise.

A reliable red-team agent is constrained by a threat model. Without an explicit threat model, the red-team will either under-attack or over-attack. Modern red-teaming practice emphasizes matching tests to the system’s intended use, interfaces, and attacker capabilities. The red-team interaction is best structured as a two-stage contract: first generate attacks, then score whether each attack is answered with evidence. If evidence is missing, the system creates a concrete retrieval action or experiment rather than allowing debate to continue abstractly.

```python
def red_team(answer_draft, context, threat_model):
    attacks = Challenger(threat_model).generate_attacks(
        claim_set=extract_claims(answer_draft),
        context=context,
    )
    return attacks

def respond_with_evidence(answer_draft, attacks, tools):
    for attack in attacks:
        evidence = retrieve_or_compute(attack.required_evidence, tools)
        answer_draft = revise(answer_draft, attack, evidence)
    return answer_draft
```

### Debate agents

Debate agents extend red-teaming by running an explicit, turn-based argument protocol. The canonical form uses two opposing sub-agents and an arbiter. One agent defends a candidate answer or plan, the other attempts to falsify it, and the arbiter decides what survives based on evidence and internal consistency. This structure follows the intuition of debate-based oversight: when direct evaluation is hard, adversarial argumentation highlights the crux of disagreement.

To make debate productive rather than verbose, three constraints matter. Arguments are anchored to a shared claim graph, so that claims, supports, and refutations are explicit and can be tied to tool results. The arbiter follows an evidence-first decision rule, accepting claims only when they are supported by retrieved or computed evidence and rejecting claims contradicted by evidence. The system enforces diversity across the debating agents, for example by varying prompts, personas, context slices, or even model families, to avoid convergence by collusion.

```python
def debate(question, tools, max_rounds=3):
    pro = Advocate(role="pro", objective="defend the best current answer with evidence")
    con = Skeptic(role="con", objective="find failure modes and counterexamples")
    judge = Arbiter(rule="evidence-first", output="decision + required followups")

    state = DebateState(question=question, claims=[])
    for _ in range(max_rounds):
        state = state.apply(pro.turn(state))
        state = state.apply(con.turn(state))
        contested = state.contested_claims()
        state = state.attach_evidence(run_tools_for(contested, tools))
        decision = judge.decide(state)
        state = state.apply(decision)
        if decision.is_sufficient():
            break

    return judge.final_answer(state)
```

### Persona simulation as controlled adversarial diversity

Persona simulation operationalizes diversity of critique by encoding viewpoints as durable, inspectable artifacts rather than ad hoc prompt styles. Each persona represents a stable role in the target domain, with explicit objectives, acceptance criteria for evidence, and required challenges it must raise. The intent is not to imitate individuals, but to encode the constraints an expert in that role would apply.

Personas are derived from authoritative sources for the role being simulated, such as standards documents, review guidelines, incident postmortems, or domain-specific best practices. This research phase grounds personas in real evaluation criteria rather than stylistic role-play. For example, a security reviewer persona can be derived from threat modeling frameworks and vulnerability disclosure practices, while a clinical domain expert persona can be derived from regulatory review checklists and methodological standards in biomedical research.

Each persona is stored as a versioned artifact in the repository, such as `personas/security_reviewer.md`, and loaded by the runtime as a constraint specification for a sub-agent. The persona file is a compact narrative specification of what the agent must optimize for, what it must challenge by default, and what constitutes acceptable evidence. This makes personas auditable and evolvable as the system’s scope changes.

```python
class Persona:
    def __init__(self, name, objectives, required_challenges, evidence_policy):
        self.name = name
        self.objectives = objectives
        self.required_challenges = required_challenges
        self.evidence_policy = evidence_policy

def load_persona(path):
    spec = parse_markdown(path)
    return Persona(
        name=spec.title,
        objectives=spec.objectives,
        required_challenges=spec.required_challenges,
        evidence_policy=spec.evidence_policy,
    )

security_reviewer = load_persona("personas/security_reviewer.md")

agent = CriticAgent(
    persona=security_reviewer,
    instruction="Review the current plan and surface security-relevant failure modes."
)
```

At runtime, persona constraints are enforced structurally. Each persona must produce at least one falsifiable challenge, must either attach evidence or open a retrieval task for any rejected claim, and must classify issues in a way that downstream orchestration can act on. This prevents personas from degenerating into generic critique and makes their output evaluable.

```python
def persona_turn(agent, state):
    critique = agent.generate(state)
    assert critique.contains_falsifiable_claim()
    assert critique.references_evidence() or critique.opens_retrieval_task()
    return critique
```

Personas should evolve based on observed system failures. By clustering historical errors by root cause, you can refine persona constraints to cover blind spots that repeatedly escape critique. This connects persona simulation to rubric-based evaluation and error taxonomies introduced earlier in the book. Over time, the persona library becomes part of the system’s governance surface, encoding which viewpoints the system is designed to respect and which classes of failure it is systematically trained to surface.

## References

1. Geoffrey Irving, Paul Christiano, Dario Amodei. *AI Safety via Debate*. arXiv, 2018. [https://arxiv.org/abs/1805.00899](https://arxiv.org/abs/1805.00899)
2. Yilun Du, Shuang Li, Antonio Torralba, Joshua B. Tenenbaum, Igor Mordatch. *Improving Factuality and Reasoning in Language Models through Multiagent Debate*. arXiv, 2023. [https://arxiv.org/abs/2305.14325](https://arxiv.org/abs/2305.14325)
3. A. Madaan, et al. *Self-Refine: Iterative Refinement with Self-Feedback*. arXiv, 2023. [https://arxiv.org/abs/2303.17651](https://arxiv.org/abs/2303.17651)
4. Noah Shinn, Federico Cassano, Ashwin Gopinath, Karthik R. Narasimhan, Shunyu Yao. *Reflexion: Language Agents with Verbal Reinforcement Learning*. NeurIPS, 2023. [https://arxiv.org/abs/2303.11366](https://arxiv.org/abs/2303.11366)
5. Yuntao Bai, et al. *Constitutional AI: Harmlessness from AI Feedback*. arXiv, 2022 (rev. 2023). [https://arxiv.org/abs/2212.08073](https://arxiv.org/abs/2212.08073)
6. Anthropic. *Challenges in Red Teaming AI Systems*. Anthropic News, 2024. [https://www.anthropic.com/news/challenges-in-red-teaming-ai-systems](https://www.anthropic.com/news/challenges-in-red-teaming-ai-systems)
7. Center for Security and Emerging Technology (CSET). *AI Red-Teaming Design: Threat Models and Tools*. CSET, 2025. [https://cset.georgetown.edu/article/ai-red-teaming-design-threat-models-and-tools/](https://cset.georgetown.edu/article/ai-red-teaming-design-threat-models-and-tools/)

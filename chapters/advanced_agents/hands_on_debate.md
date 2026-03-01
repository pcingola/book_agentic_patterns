## Hands-On: Debate Agent

This exercise (`example_debate.ipynb`) demonstrates the full adversarial debate pattern using `DebateOrchestrator` and `RedTeamAgent`.

### Basic debate

Instantiate a `DebateOrchestrator` and run it against a proposal. The orchestrator manages advocate and critic turns internally; you only supply the proposal and the number of rounds.

```python
from agentic_patterns.core.agents import DebateOrchestrator, RedTeamAgent

proposal = "Our e-commerce platform should migrate from PostgreSQL to MongoDB."

debate = DebateOrchestrator(max_rounds=2)
result = await debate.run(proposal)
```

`result.rounds` contains each round's advocate and critic turns. Each turn holds a list of `Argument` objects with a `claim`, supporting `evidence`, and any `rebuttals` raised by the other side.

### Persona-driven debate

Pass `advocate_prompt` and `critic_prompt` to simulate specific domain viewpoints:

```python
debate = DebateOrchestrator(
    advocate_prompt="You are a startup CTO who values developer velocity above all else.",
    critic_prompt="You are a database reliability engineer with 10 years of PostgreSQL experience.",
    max_rounds=2,
)
result = await debate.run(proposal)
```

The prompts are prepended to each side's instructions, so the same structured output format applies regardless of persona.

### Red-team analysis

Apply `RedTeamAgent` to the debate verdict to surface risks that survived the debate:

```python
red_team = RedTeamAgent(
    threat_model="Database migration risks: data loss, downtime, performance regression, skill gaps."
)
rt_result = await red_team.analyze(
    result=result.verdict.decision,
    context=result.verdict.reasoning,
)
```

`rt_result.challenges` is a ranked list of `Challenge` objects, each with a `claim`, an `attack`, a `severity`, and the `required_evidence` that would resolve it.

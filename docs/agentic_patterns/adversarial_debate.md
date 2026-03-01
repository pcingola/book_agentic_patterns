# Adversarial & Debate Agents

Two reusable adversarial orchestration patterns in `agentic_patterns.agents`: red-team analysis and structured debate. Both use `get_agent()` with structured output types and `load_prompt()` for prompt templates. They do not use `OrchestratorAgent` -- these are fixed protocols, not LLM-driven orchestration.

Prompts live in `prompts/adversarial/`.


## Red-Team Agent

`RedTeamAgent` generates adversarial challenges against a result, constrained by a threat model. It produces a ranked list of `Challenge` objects, each identifying a claim, attack vector, severity, and the evidence needed to resolve it.

```python
from agentic_patterns.core.agents import RedTeamAgent

red_team = RedTeamAgent(
    threat_model="Data loss, downtime, performance regression, vendor lock-in."
)
result = await red_team.analyze(
    result="We recommend migrating to MongoDB.",
    context="Current system handles 10K transactions/sec on PostgreSQL.",
)
for ch in result.challenges:
    print(f"[{ch.severity}] {ch.claim}: {ch.attack}")
```


## Debate Orchestrator

`DebateOrchestrator` runs a multi-round advocate-vs-critic debate with an arbiter that renders a verdict after each round. The loop: advocate argues, critic counters, arbiter decides whether the debate is sufficient. Early termination when `verdict.is_sufficient` is true.

```python
from agentic_patterns.core.agents import DebateOrchestrator

debate = DebateOrchestrator(max_rounds=2)
result = await debate.run("Migrate from PostgreSQL to MongoDB")
print(result.verdict.decision)
print(result.verdict.open_questions)
```

Persona simulation is achieved by passing role descriptions as `advocate_prompt` and `critic_prompt`:

```python
debate = DebateOrchestrator(
    advocate_prompt="You are a startup CTO who values developer velocity.",
    critic_prompt="You are a database reliability engineer with 10 years of PostgreSQL experience.",
    max_rounds=2,
)
```


## API Reference

### `agentic_patterns.agents.red_team`

| Name | Kind | Description |
|---|---|---|
| `Challenge` | Pydantic model | claim, attack, severity, required_evidence |
| `RedTeamResult` | Pydantic model | challenges: list[Challenge], summary: str |
| `RedTeamAgent(threat_model, config_name)` | Class | Red-team analysis agent |
| `RedTeamAgent.analyze(result, context)` | Method | Returns RedTeamResult |

### `agentic_patterns.agents.debate`

| Name | Kind | Description |
|---|---|---|
| `Argument` | Pydantic model | claim, evidence, rebuttals: list[str] |
| `DebateTurn` | Pydantic model | position: str, arguments: list[Argument] |
| `Verdict` | Pydantic model | decision, reasoning, accepted/rejected claims, open_questions, is_sufficient |
| `DebateRound` | Pydantic model | advocate: DebateTurn, critic: DebateTurn |
| `DebateResult` | Pydantic model | proposal, rounds: list[DebateRound], verdict: Verdict |
| `DebateOrchestrator(advocate_prompt, critic_prompt, config_name, max_rounds)` | Class | Multi-round debate orchestrator |
| `DebateOrchestrator.run(proposal)` | Method | Returns DebateResult |


## Examples

See `agentic_patterns/examples/advanced_agents/example_debate.ipynb` for a hands-on walkthrough covering basic debate, persona-driven debate, and red-team analysis of debate results.

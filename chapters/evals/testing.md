## Testing

Testing establishes confidence that agentic systems behave as intended across code changes, model updates, and evolving environments, despite inherent stochasticity. Building on the historical evolution discussed earlier, this section examines classical testing layers through an agentic lens.

#### Classical testing layers, revisited for agentic systems

Smoke tests are the most basic validation step. In agentic systems, a smoke test typically verifies that an agent can start, load its configuration, register tools, and complete a trivial task without crashing. This is often used as a deployment gate to catch obvious integration failures such as missing credentials or incompatible schemas.

Unit tests remain focused on small, deterministic components. In agentic architectures, this usually means tools, parsers, routing logic, and state management code. These components should be tested with strict assertions, since they are expected to behave deterministically given fixed inputs. For example, a tool wrapper can be validated independently of the model:

```python
def test_currency_tool():
    result = convert_currency(amount=10, from_="USD", to="EUR", rate=0.9)
    assert result == 9.0
```

Integration tests validate that multiple components interact correctly. For agents, this often means running a model invocation together with one or two real tools and asserting on structured outputs or side effects, such as database writes. At this level, exact text matching is usually avoided in favor of schema validation or semantic checks.

System tests exercise the agent as a whole in a controlled environment. This includes realistic prompts, full toolchains, and representative context. The goal is to ensure that the system satisfies high-level requirements, such as “the agent can complete a support ticket end-to-end using the approved tools.”

End-to-end tests extend this further by running the agent in conditions that closely resemble production, often including external services and asynchronous workflows. These tests are slower and more brittle but are critical for catching failures that only appear when all pieces are connected.

Stress and load tests evaluate behavior under pressure. For agentic systems, this includes concurrency, long conversations, large contexts, and high tool-call volumes. These tests often surface issues related to rate limits, memory growth, and degraded model performance under constrained budgets.

#### Deterministic versus non-deterministic testing

A key distinction in agentic systems is between deterministic components and non-deterministic behavior driven by models. Tools, orchestrators, and protocol layers should be tested with traditional deterministic techniques. Agents, by contrast, require probabilistic thinking.

Instead of asserting that an agent produces a specific string, tests typically assert properties: that the output conforms to a schema, that required steps were executed, or that unsafe actions were not taken. Repeated runs may be used to estimate stability, for example verifying that a workflow succeeds in 95% of runs under fixed conditions.

This distinction strongly suggests a layered strategy: maximize deterministic testing below the model boundary, and minimize the surface area where stochastic behavior can cause flakiness.

#### Evals versus benchmarks

In the context of agentic systems, it is useful to separate *evals* from *benchmarks*. Evals focus on correctness relative to a specific task or workflow. They answer questions such as whether an agent followed the right steps, used the correct tools, or produced outputs that satisfy domain constraints.

Benchmarks, by contrast, probe capability limits. They are designed to compare models or agents across standardized tasks and often emphasize aggregate performance rather than pass/fail correctness. While benchmarks are valuable for model selection and research, they are usually insufficient for validating production systems. This chapter treats benchmarks as complementary, but distinct, from evals, which will be explored in detail later.

#### Testing as a foundation for evals

Testing provides the scaffolding on which evals are built. Without reliable unit and integration tests, eval failures become difficult to interpret, since they may reflect basic bugs rather than model or reasoning issues. A practical rule is that evals should assume that deterministic layers are already well-tested, allowing eval results to focus on agent behavior rather than infrastructure correctness.

At an introductory level, testing can be seen as answering the question “does this system work at all?” Evals refine this into “does this system work well, consistently, and for the right reasons?” The remainder of this chapter builds on that foundation.


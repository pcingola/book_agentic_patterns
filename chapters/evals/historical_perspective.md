## Historical perspective

Modern “evals” for agents sit at the intersection of two older traditions: (1) software testing, where we try to detect regressions and enforce contracts in deterministic systems, and (2) empirical evaluation, where we measure performance statistically under uncertainty. Agentic systems combine both: they are software pipelines with explicit interfaces (tools, APIs, workflows) and stochastic components (models) whose behavior must be measured rather than “proven correct” in the classic sense.

### From program correctness to practical testing discipline (1960s–1990s)

Early computer science treated correctness as a central goal, but quickly acknowledged a hard limit: testing can expose failures, yet cannot establish correctness in the same way a proof can. This idea is crisply captured in Dijkstra’s well-known observation that testing can show the presence of bugs, not their absence. ([UT Austin Computer Science][1])

By the late 1970s, software testing matured into an engineering discipline with systematic test design techniques, separating concerns such as unit-level checks, integration risks, and system-level behavior. A key theme from this era is that good tests are not “more assertions,” but carefully chosen cases that maximize fault detection under realistic constraints (time, budget, complexity). ([lira.epac.to][2])

In the 1990s, unit testing frameworks and “test first” practices operationalized these ideas into everyday development workflows. The rise of xUnit-style frameworks (with JUnit becoming the canonical example in the Java ecosystem) made tests cheap to write, cheap to run, and easy to automate—setting the stage for large-scale regression testing as a default expectation rather than a luxury. ([Runestone Academy][3])

### Automation and regression as the default (2000s)

As software systems grew, the evaluation problem became less about writing individual tests and more about continuously running them. Continuous Integration popularized the idea that every change should be validated by an automated pipeline, repeatedly, in an environment that approximates production constraints. This is where “regression testing” became a cultural default: you do not only check whether the new change works, you continuously ensure that old capabilities still work. ([martinfowler.com][4])

This period is important for agent evals because it established the operational pattern we still reuse: an evaluation harness that runs on every commit, produces comparable metrics, and fails fast when a change introduces unacceptable drift.

### Benchmarks, leaderboards, and “dataset-driven” progress (1990s–2010s)

In parallel, empirical evaluation in information retrieval and machine learning developed its own standardized practices. A canonical example is TREC (started in 1992), which institutionalized shared tasks, standardized datasets, and common scoring so that progress could be measured across research groups. ([TREC][5])

Computer vision later amplified this dynamic with ImageNet/ILSVRC, where a single benchmark catalyzed both methodological progress and community-wide comparability. Even outside vision, ImageNet became a template for how benchmarks shape research priorities: define tasks, define data, define scoring, publish leaderboards, iterate. ([arXiv][6])

The key historical shift here is that “evaluation” became a product: a benchmark suite plus an execution harness plus a leaderboard. That package created incentives for reproducibility and accelerated iteration—but also introduced predictable failure modes, such as overfitting to benchmarks and optimizing the metric rather than the underlying capability.

### From task metrics to general language benchmarks (late 2010s–early 2020s)

As language models became general-purpose, evaluation moved from single tasks to multi-task suites designed to summarize broad capability. GLUE (2018) and SuperGLUE (2019) formalized this approach: instead of arguing about one dataset, the community argued about a bundle of datasets, one scoring interface, and one aggregate metric. ([arXiv][7])

Soon after, benchmarks shifted again to probe breadth and difficulty at scale. MMLU (2020) emphasized broad academic and professional coverage with a standardized multiple-choice format, explicitly framing evaluation as “measuring what the model knows and can reason about,” not just whether it can fit a particular dataset. ([arXiv][8])
BIG-bench (2022) pushed further by assembling many tasks intended to be beyond the frontier, aiming to characterize scaling behavior and emergent capabilities rather than only track incremental improvements. ([arXiv][9])

At the same time, the evaluation community broadened what “good” means. HELM (2022) is emblematic: it treats evaluation as multi-metric (accuracy, robustness, fairness, toxicity, efficiency, etc.) and scenario-driven (different use cases), making tradeoffs explicit instead of hiding them behind a single leaderboard number. ([arXiv][10])

This matters for agent builders because real products rarely fail on “accuracy” alone. They fail on brittleness, cost, latency, unsafe actions, missing guardrails, or silent degradation across versions. The historical arc is a gradual expansion from single-metric correctness toward multi-dimensional fitness.

### The “LLM era” problem: evaluating open-ended outputs (2023–)

Chat-style assistants and agentic workflows broke many older assumptions. When the output is free-form text, there may be no single ground-truth label; when the system is interactive, success depends on multi-step trajectories, tool calls, and environment state.

Two major responses emerged:

First, “LLM as a judge” became a practical evaluation primitive for open-ended tasks, enabling scalable comparisons where humans are too slow or expensive. Work such as MT-Bench (and related comparisons against human preferences) studied how to use model judges, and documented judge pathologies like position bias and verbosity bias—highlighting that judge-based evals are themselves stochastic systems that must be calibrated and monitored. ([arXiv][11])

Second, the field shifted toward realistic, end-to-end environments that directly test whether an agent completes tasks, not whether it produces plausible text. Benchmarks such as WebArena (realistic web interactions), AgentBench (multi-environment “LLM as agent” evaluation), and SWE-bench (real-world software engineering issues) treat evaluation as running the agent inside a constrained world and scoring functional success. ([arXiv][12])

This is the historical bridge to modern agent evals: evaluation becomes closer to systems testing than model testing. The “unit of evaluation” is not a completion; it is a trajectory with tool calls, intermediate states, and externally validated outcomes.

### Why agent evals look like “testing + measurement”

Agents force a synthesis of software-testing ideas (contracts, regression, controlled environments) and empirical-evaluation ideas (sampling variance, distribution shift, multi-metric scoring). Two consequences follow:

First, the harness becomes as important as the metric. If you cannot replay tool interactions, freeze environments, and record artifacts, then you cannot reliably attribute regressions to changes in prompts, models, tools, or data.

Second, deterministic checks and stochastic checks must coexist. Tool interfaces, schemas, and safety gates can often be tested deterministically. Model reasoning quality and long-horizon planning cannot; they require repeated trials, statistical summaries, and careful baselining.

A minimal historical “lesson” is that the most durable evaluation practice is not a particular benchmark, but the workflow: define contracts, automate regression, make metrics comparable across time, and treat evaluation itself as production infrastructure.

### Code sketch: the evolution from assertions to harnesses

The historical shift shows up concretely in how teams write evaluation code. A classic unit test is a strict assertion:

```python
def test_currency_formatting():
    assert format_usd(12.5) == "$12.50"
```

Agent evals often wrap a harness around stochastic behavior, separating deterministic invariants (“must be valid JSON”, “must not call forbidden tools”) from scored quality:

```python
def run_case(agent, case, *, n_trials=5, seed=0):
    scores = []
    for i in range(n_trials):
        rng_seed = seed + i
        trace = agent.run(case.input, seed=rng_seed)

        # Deterministic invariants (testing mindset)
        assert trace.output.is_valid_json
        assert "forbidden_tool" not in trace.tools_called

        # Scored criteria (evaluation mindset)
        scores.append(score_case(case, trace))

    return {
        "case_id": case.id,
        "mean": sum(scores) / len(scores),
        "min": min(scores),
        "max": max(scores),
    }
```

This structure mirrors the historical convergence: tests guard contracts; evals measure performance under variance; both feed a regression pipeline.

### Code sketch: LLM-as-judge as an evaluation instrument

When outputs are open-ended, the “judge” is part of the measurement system and should be treated like any other non-deterministic dependency: versioned, prompted, and sanity-checked.

```python
JUDGE_RUBRIC = """
You are grading an assistant response.

Score each dimension 1-5:
- Correctness (facts and constraints)
- Completeness (covers required items)
- Safety (no unsafe instructions)
- Clarity (well-structured, unambiguous)

Return strict JSON:
{"correctness": int, "completeness": int, "safety": int, "clarity": int, "overall": int}
"""

def judge_output(judge_model, prompt, assistant_output):
    judge_input = {
        "rubric": JUDGE_RUBRIC,
        "task_prompt": prompt,
        "assistant_output": assistant_output,
    }
    return judge_model.generate_json(judge_input)  # version + prompt must be pinned
```

Historically, this is analogous to earlier standardized scoring scripts in shared-task evaluations—except the scorer is now a model, so calibration and drift monitoring become essential.

## References (references.md)

1. Edsger W. Dijkstra. *Notes on Structured Programming (EWD 249)*. In: J. N. Buxton and B. Randell (eds.), *Software Engineering Techniques* (NATO Conference proceedings), 1970. ([UT Austin Computer Science][1])
2. Glenford J. Myers, Corey Sandler, Tom Badgett. *The Art of Software Testing*. Wiley, originally 1979 (revised editions later). ([lira.epac.to][2])
3. Martin Fowler. *Continuous Integration*. ThoughtWorks / martinfowler.com, originally 2001 (updated 2006; later revisions). ([martinfowler.com][4])
4. NIST. *Text REtrieval Conference (TREC) Overview*. NIST, started 1992. ([TREC][5])
5. Olga Russakovsky et al. *ImageNet Large Scale Visual Recognition Challenge*. IJCV, 2015. ([arXiv][6])
6. Alex Wang et al. *GLUE: A Multi-Task Benchmark and Analysis Platform for Natural Language Understanding*. arXiv, 2018. ([arXiv][7])
7. Alex Wang et al. *SuperGLUE: A Stickier Benchmark for General-Purpose Language Understanding Systems*. NeurIPS, 2019. ([arXiv][13])
8. Dan Hendrycks et al. *Measuring Massive Multitask Language Understanding*. arXiv, 2020. ([arXiv][8])
9. Aarohi Srivastava et al. *Beyond the Imitation Game: Quantifying and extrapolating the capabilities of language models (BIG-bench)*. arXiv, 2022. ([arXiv][9])
10. Percy Liang et al. *Holistic Evaluation of Language Models (HELM)*. arXiv, 2022. ([arXiv][10])
11. Lianmin Zheng et al. *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*. arXiv, 2023. ([arXiv][11])
12. Shuyan Zhou et al. *WebArena: A Realistic Web Environment for Building Autonomous Agents*. arXiv, 2023. ([arXiv][12])
13. Xiangrui Liu et al. *AgentBench: Evaluating LLMs as Agents*. arXiv, 2023. ([arXiv][14])
14. Carlos E. Jimenez et al. *SWE-bench: Can Language Models Resolve Real-world GitHub Issues?*. ICLR, 2024. ([ICLR Proceedings][15])

[1]: https://www.cs.utexas.edu/~EWD/transcriptions/EWD02xx/EWD249/EWD249.html?utm_source=chatgpt.com "Notes on Structured Programming (EWD 249)"
[2]: https://lira.epac.to/DOCS-TECH/Engineering%20and%20Management/Software%20Testing/The%20Art%20of%20Software%20Testing%20-%20Second%20Edition.pdf?utm_source=chatgpt.com "The Art of Software Testing, Second Edition"
[3]: https://runestone.academy/ns/books/published/bridgesds/sec-UnitTest.html?utm_source=chatgpt.com "2.5 Unit Testing"
[4]: https://martinfowler.com/articles/continuousIntegration.html?utm_source=chatgpt.com "Continuous Integration"
[5]: https://trec.nist.gov/overview.html?utm_source=chatgpt.com "Text REtrieval Conference (TREC) Overview"
[6]: https://arxiv.org/abs/1409.0575?utm_source=chatgpt.com "ImageNet Large Scale Visual Recognition Challenge"
[7]: https://arxiv.org/abs/1804.07461?utm_source=chatgpt.com "GLUE: A Multi-Task Benchmark and Analysis Platform for Natural Language Understanding"
[8]: https://arxiv.org/abs/2009.03300?utm_source=chatgpt.com "Measuring Massive Multitask Language Understanding"
[9]: https://arxiv.org/abs/2206.04615?utm_source=chatgpt.com "Beyond the Imitation Game: Quantifying and extrapolating the capabilities of language models"
[10]: https://arxiv.org/abs/2211.09110?utm_source=chatgpt.com "Holistic Evaluation of Language Models"
[11]: https://arxiv.org/abs/2306.05685?utm_source=chatgpt.com "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena"
[12]: https://arxiv.org/abs/2307.13854?utm_source=chatgpt.com "WebArena: A Realistic Web Environment for Building Autonomous Agents"
[13]: https://arxiv.org/abs/1905.00537?utm_source=chatgpt.com "SuperGLUE: A Stickier Benchmark for General-Purpose Language Understanding Systems"
[14]: https://arxiv.org/abs/2308.03688?utm_source=chatgpt.com "[2308.03688] AgentBench: Evaluating LLMs as Agents"
[15]: https://proceedings.iclr.cc/paper_files/paper/2024/file/edac78c3e300629acfe6cbe9ca88fb84-Paper-Conference.pdf?utm_source=chatgpt.com "SWE-BENCH: CAN LANGUAGE MODELS RESOLVE ..."

## Historical Perspective

Software testing did not emerge as a mature, structured discipline alongside early programming; it evolved slowly and unevenly as software systems became larger, more expensive, and harder to reason about. In the 1950s and 1960s, testing was inseparable from debugging. Programs were executed primarily to demonstrate that they worked on a small number of example inputs, and failures were fixed as they appeared. There was little notion of systematic test design, automation, or repeatability, largely because software itself was small, bespoke, and tightly coupled to hardware.

During the late 1960s and 1970s, as software projects began to fail at scale, testing started to be discussed explicitly as a risk-reduction activity. This period produced the first formal discussions of test planning, test case design, and the idea that running a program could reveal defects rather than prove correctness. These ideas influenced practice, but they did not immediately translate into fine-grained automated testing. Most testing was still manual, scenario-driven, and performed late in the development cycle, often by separate QA teams.

Through the 1980s and much of the 1990s, testing in industry remained largely system-level and end-to-end. Programs were validated by running them in realistic workflows and checking whether expected behaviors occurred. Component-level testing existed in principle, but tooling support was minimal, automation was rare, and the cost of writing and maintaining fine-grained tests often outweighed perceived benefits. The absence of widely adopted testing frameworks meant that “unit testing” was more a methodological idea than a routine engineering practice.

The shift toward automated, component-level testing accelerated only in the late 1990s and early 2000s, driven by several converging factors: the rise of modular and object-oriented design, faster machines that made test execution cheap, continuous integration practices, and the appearance of accessible testing frameworks. From this point onward, layered testing—smoke, unit, integration, system, and stress testing—became a practical reality rather than a theoretical taxonomy. Determinism remained a core assumption: given the same inputs and state, the system should behave identically, enabling strict assertions and reliable regression tests.

Machine learning systems disrupted this assumption without eliminating the need for testing. Models trained on data exhibit non-deterministic behavior, sensitivity to sampling, and performance that is best evaluated statistically. As a result, testing expanded to include dataset-based validation, tolerance ranges, and aggregate metrics, while still relying heavily on deterministic tests for data pipelines, feature extraction, and serving infrastructure.

Agentic systems push this evolution further. An agent combines stochastic model reasoning with deterministic code, external tools, long-lived state, and multi-step workflows. Testing such systems therefore requires a clear separation of concerns. Deterministic components—tools, planners, routers, protocol handlers, and persistence layers—should be tested using classical techniques with strict assertions. Agent behavior, by contrast, cannot be validated through exact output matching. Instead, tests assert properties: that outputs conform to schemas, that required tools were invoked, that safety constraints were respected, or that workflows completed successfully within defined bounds.

This distinction also clarifies the role of evals and benchmarks. Testing establishes that the system is wired correctly and fails in predictable ways. Evals, introduced later in this chapter, focus on whether agents behave correctly and reliably under realistic tasks and prompts. Benchmarks probe capability limits and comparative performance, but are not substitutes for correctness testing. In agentic systems, rigorous testing of deterministic layers is what makes higher-level eval results interpretable rather than noisy or misleading.

## References

1. Myers, G. J. *The Art of Software Testing*. Wiley, 1979.
2. Beizer, B. *Software Testing Techniques*. Van Nostrand Reinhold, 1990.
3. Perry, W. E. *Effective Methods for Software Testing*. Wiley, 1995.
4. Amershi, S. et al. *Software Engineering for Machine Learning: A Case Study*. ICSE, 2019.
5. Breck, E. et al. *The ML Test Score: A Rubric for ML Production Readiness*. Google Research, 2017.

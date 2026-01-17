## Book Outline

This chapter introduces the structure, intent, and learning philosophy of the book, establishing a clear mental model for how the material is organized and how it should be used.

### Structure of the Book

The book is organized to move from foundational concepts to production-grade systems, mirroring how real-world agentic platforms are designed, implemented, and operated. Early chapters establish definitions, mental models, and historical context: what agents are, what distinguishes agentic systems from conventional software, and why planning, tool use, memory, and feedback loops matter. From there, the text progressively introduces architectural patterns, execution models, and interoperability standards, followed by deeper dives into orchestration, context management, evaluation, security, and operations.

Rather than treating topics in isolation, chapters are intentionally interdependent. Concepts introduced early—such as tasks, skills, tools, and state—are revisited and refined as the system grows in capability and complexity. Later chapters assume familiarity with earlier abstractions and focus on trade-offs, failure modes, and scaling considerations that only become visible in non-trivial deployments. The result is a cohesive narrative rather than a reference manual: each chapter exists to support the construction and understanding of a complete agentic system.

### Intended Audience

This book is written for engineers building agentic systems, not for readers seeking a high-level overview of AI or large language models. The assumed audience is comfortable with programming, distributed systems concepts, APIs, and schemas, and has at least some experience deploying production software. Familiarity with Python, JSON-based protocols, asynchronous execution, and modern backend architectures is assumed throughout.

The book does not attempt to abstract away engineering complexity. Instead, it makes that complexity explicit, framing agentic systems as a new class of software systems with their own constraints and failure modes. Readers are expected to engage critically with design choices, understand why certain abstractions exist, and reason about trade-offs between correctness, cost, latency, safety, and scalability.

### Learning Approach: Theory and Hands-On Practice

The learning approach deliberately combines theoretical grounding with practical implementation. Core ideas are motivated by research literature and prior systems—such as planning algorithms, reinforcement learning concepts, and human-in-the-loop control—but are always tied back to concrete engineering patterns. When a concept is introduced, it is followed by examples, pseudo-code, or real-world design sketches that show how the idea manifests in working systems.

Hands-on sections emphasize partial implementations rather than toy examples. Code snippets are used to illustrate interfaces, contracts, and control flow, while full implementations are assumed to live in accompanying repositories. This approach reflects how agentic systems are built in practice: by composing well-defined components rather than writing monolithic scripts. The goal is not to teach a specific framework, but to equip the reader with transferable patterns that apply across ecosystems and tooling choices.

### A Running Enterprise-Grade Example

Throughout the book, all major concepts are grounded in a single, evolving example: an enterprise-grade agentic platform designed for organizational use. We will be building a "Manus"-like agentic system suitable for both large enterprise and start-up companies. Conceptually, this system resembles an internal "AI operations layer" for a company—capable of planning work, delegating tasks across specialized agents, interacting with internal tools and data, and operating under governance, security, and compliance constraints.

This running example is intentionally ambitious. It includes multiple agents with distinct responsibilities, long-running tasks, shared state, tool orchestration, human approval gates, and auditability requirements. Early chapters introduce a minimal version of the system, while later chapters incrementally add capabilities such as task persistence, inter-agent protocols, skill modularization, observability, and policy enforcement. By the end of the book, the reader will have seen how a realistic agentic platform can be assembled from first principles, and how architectural decisions made early on influence the system’s behavior at scale.

The purpose of this example is not to prescribe a single “correct” architecture, but to provide a concrete anchor for discussion. Abstract ideas become easier to reason about when they are consistently mapped onto the same system, and design trade-offs become clearer when their consequences are traced across multiple chapters.

### References

1. Russell, S., Norvig, P. *Artificial Intelligence: A Modern Approach*. Pearson, 2021.
2. Wooldridge, M. *An Introduction to MultiAgent Systems*. Wiley, 2009.
3. Sutton, R. S., Barto, A. G. *Reinforcement Learning: An Introduction*. MIT Press, 2018.
4. Amodei, D. et al. *Concrete Problems in AI Safety*. arXiv, 2016.
5. OpenAI. *Planning and Acting with Large Language Models*. OpenAI research blog, 2023.

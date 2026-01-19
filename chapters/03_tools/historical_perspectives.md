## Historical Perspectives

Tool use in agentic systems draws from several distinct research traditions that converged with the emergence of large language models. Understanding these roots clarifies why modern tool-use patterns take the forms they do.

The separation between reasoning and acting is foundational to artificial intelligence. Early symbolic agents modeled actions as operators with preconditions and effects, enabling systems to plan sequences of steps before execution. These systems assumed agents could invoke well-defined procedures to change or query the environment, then continue reasoning based on results. The agent's "tools" were operators in a known, fixed action space. As systems grew more complex, research in the 1990s and early 2000s expanded toward automated service composition and semantic web services, where agents dynamically selected services based on declarative descriptions rather than hard-coded logic.

This need to manage state across reasoning steps led to architectural innovations. In the 1980s, blackboard architectures made the separation between transient reasoning and persistent state explicit: multiple specialized components cooperated indirectly by reading from and writing to a shared data store, rather than communicating through tightly coupled message passing. Cognitive architectures such as Soar and ACT-R reinforced this distinction between short-term working memory and longer-lived declarative or procedural memory, demonstrating that sophisticated agents required mechanisms for externalizing state beyond what could be held in immediate reasoning.

Parallel to these developments in agent architecture, security research was establishing foundational concepts that would later become essential for tool-using agents. Capability-based security, developed in the 1970s and 1980s, represented authority as explicit, unforgeable capabilities rather than implicit global rights. Sandboxing and access control in operating systems formalized read/write/execute distinctions to contain damage from faulty or malicious programs. When early autonomous agents emerged in planning and robotics research, permissions were mostly implicit because agents operated in closed worlds with trusted sensors and actuators. This assumption would break down as agents began interacting with external APIs, databases, and the open internet.

The question of when agents should act autonomously versus when they should defer to humans also has deep roots. Research on mixed-initiative interfaces in the late 1990s studied interruptibility, uncertainty-aware escalation, and keeping the human in control. Interactive machine learning formalized feedback loops where people correct, guide, or approve model behavior during operation rather than only at training time. These ideas map directly onto modern tool-using agents: the model proposes an external action, and a human can confirm, deny, or revise it before any irreversible side-effect occurs.

The shift to neural sequence models in the 2010s disrupted the balance between fluency and structure. Models became exceptionally good at producing fluent text, but the explicit structure that software systems depend on largely disappeared. For a time, this was acceptable because models were mostly used as assistants or interfaces for humans. As soon as models began to act as components inside larger systems—calling APIs, producing plans, or controlling workflows—the lack of structure became a liability. Early approaches relied on informal conventions where models produced natural-language descriptions of intended actions, and downstream code attempted to infer meaning using heuristics or pattern matching. These systems were brittle, opaque, and difficult to debug.

Two research threads gradually converged to address this structure gap. Work on semantic parsing and program induction explored mapping language to executable structures with explicit meaning, while advances in typed data validation emphasized schemas and contracts as a foundation for reliability. Research on retrieval-augmented generation, program synthesis, and constrained decoding showed that neural models could be guided to produce well-formed logical forms, programs, and data structures. Practical engineering converged on schemas and typed interfaces as the robust way to integrate probabilistic models into deterministic systems.

With the emergence of large language models capable of reliably producing structured outputs, these ideas became operational. Around 2022-2023, agent systems began replacing textual "action descriptions" with structured tool calls validated against explicit schemas, and tool use shifted from a prompting convention to an architectural pattern. The decisive shift came with models that could reliably emit structured outputs and conditionally decide to use them: a model that can reason, decide to act, observe the result, and iterate is qualitatively different from one that only generates text. This transition also highlighted new failure modes—unintended side effects, prompt injection, and data exfiltration through tools—leading to renewed emphasis on explicit permission models, especially in enterprise and safety-critical contexts.

As tool-using agents moved from research prototypes to production deployments, the need for stable interaction protocols became apparent. Early desktop and IDE-style agent deployments around 2023-2024 initially relied on embedding tool descriptions directly into prompts and parsing structured outputs. While workable for short-lived interactions, this approach showed its limits as sessions became longer, tools more numerous, and state more complex. The architectural inspiration for protocols like MCP came largely from the Language Server Protocol (LSP), introduced in 2016, which demonstrated that a clean separation between a client and a capability provider could be achieved using a small set of protocol primitives. This generalized the idea from editor-language tooling interaction to model-environment interaction, providing the infrastructural layer required to make agentic behavior robust over time.

### References

1. Russell, S., Norvig, P. *Artificial Intelligence: A Modern Approach*. Prentice Hall, 1995.
2. McIlraith, S., Son, T. C., Zeng, H. *Semantic Web Services*. IEEE Intelligent Systems, 2001.
3. Lampson, B. *Protection*. ACM SIGOPS Operating Systems Review, 1971.
4. Dennis, J. B., Van Horn, E. C. *Programming Semantics for Multiprogrammed Computations*. Communications of the ACM, 1966.
5. Miller, M. S. *Capability-Based Security*. PhD Thesis, Johns Hopkins University, 2006.
6. Eric Horvitz. *Principles of Mixed-Initiative User Interfaces*. CHI, 1999.
7. Saleema Amershi, et al. *Power to the People: The Role of Humans in Interactive Machine Learning*. AI Magazine, 2014.
8. Newell, A. *The Knowledge Level*. Artificial Intelligence, 1982.
9. Engelmore, R., Morgan, A. *Blackboard Systems*. Addison-Wesley, 1988.
10. Laird, J. *The Soar Cognitive Architecture*. MIT Press, 2012.
11. Zettlemoyer, L., Collins, M. *Learning to Map Sentences to Logical Form*. UAI, 2005.
12. Wong, Y. W., Mooney, R. J. *Learning for Semantic Parsing with Statistical Machine Translation*. NAACL, 2006.
13. Yin, P., Neubig, G. *A Syntactic Neural Model for General-Purpose Code Generation*. ACL, 2017.
14. Lewis, P. et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS, 2020.
15. Schick, T. et al. *Toolformer: Language Models Can Teach Themselves to Use Tools*. NeurIPS, 2023.
16. Yao, S. et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR, 2023.
17. Microsoft. *Language Server Protocol Specification*. 2016.
18. Anthropic. *Model Context Protocol*. Technical documentation, 2024.

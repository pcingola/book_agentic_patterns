## Relationship to A2A and AgentSkills

Sub-agents are a local composition mechanism; protocols and skill specifications generalize this idea across process and organizational boundaries.

The A2A Protocol defines how agents communicate over a network, including discovery, task lifecycles, and streaming results. A sub-agent call within a single process can be seen as the degenerate case of A2A: synchronous, trusted, and low-latency. Designing sub-agents with clear inputs and outputs makes it straightforward to later "lift" them into remote A2A agents without changing their conceptual contract.

AgentSkills provides a complementary abstraction by standardizing how agent capabilities are described, packaged, and reused. A sub-agent often implements a skill: a named capability with documented inputs, outputs, and behavioral guarantees. Conversely, a published skill can be instantiated as a sub-agent inside a larger system. This symmetry encourages modular design, where local sub-agents, reusable skills, and remote A2A agents all share the same conceptual interface.

Taken together, sub-agents, A2A, and AgentSkills form a continuum. Sub-agents optimize local composition and context management. Skills define reusable capability boundaries. A2A enables those boundaries to extend across machines, teams, or organizations.

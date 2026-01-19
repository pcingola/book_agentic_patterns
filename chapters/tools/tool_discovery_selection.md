## Tool Discovery and Selection

Tool discovery and selection is the pattern by which an agent determines which external capabilities are relevant to a task and decides which of them to invoke in order to make progress toward its goal.

### The pattern explained

At its core, tool discovery and selection separates *capability awareness* from *capability execution*. An agent reasons over descriptions of available tools—what they do, what inputs they require, what outputs they produce, and what constraints they impose—without being tightly coupled to their implementations. This allows the agent to treat tools as interchangeable capabilities rather than fixed function calls.

In simple systems, a single agent may both select and invoke tools. However, as tool catalogs grow, this approach becomes inefficient. Presenting hundreds or thousands of tools to an agent increases context length, dilutes attention, and raises the likelihood of incorrect selection. To address this, tool discovery and selection can be structured as a two-stage agent process.

In the first stage, a *tool-selection agent* performs global reasoning over the task and the full set of available tools. This agent does not execute tools. Its responsibility is to analyze the task requirements and identify which capabilities are potentially relevant. The output of this stage is a structured filter: a restricted subset of tools, possibly accompanied by constraints such as read-only access or domain limitations. This step may be cached or reused across similar tasks, since it is concerned with capability matching rather than execution details.

In the second stage, a *task-execution agent* is invoked with the original task and only the restricted tool set produced by the first stage. From this agent’s perspective, the reduced set of tools defines the entire action space. Because irrelevant tools are absent from its context, the agent can reason more efficiently, produce more reliable tool invocations, and avoid unintended or unsafe actions. This agent applies standard tool-use patterns—deciding when to act, invoking tools with structured inputs, and incorporating outputs into its ongoing reasoning.

This separation mirrors long-standing architectural principles in AI and distributed systems: planning versus acting, control plane versus execution plane, and global reasoning versus local decision-making. Tool discovery becomes an explicit, inspectable step, rather than an implicit side effect of prompting.

### Why the pattern matters

Treating tool discovery and selection as a first-class pattern enables agentic systems to scale. New tools can be added without overwhelming execution agents, safety and permission policies can be enforced during selection, and context length can be tightly controlled. Most importantly, agents remain adaptable: they reason over *what capabilities exist* independently of *how those capabilities are used*.

As agents evolve into long-running systems operating over large and dynamic tool ecosystems, this pattern becomes essential. Without explicit tool discovery and selection, tool use degrades into ad hoc prompting. With it, tool use becomes a deliberate, structured, and scalable component of agentic behavior.


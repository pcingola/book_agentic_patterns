## Hands-On: Graph-Based Orchestration

Graphs model agent execution as explicit state machines where nodes represent work units and edges define transitions. Unlike linear chains or simple workflows, graphs support branching, cycles, and conditional transitions that are inspectable and verifiable.

This hands-on explores graph-based orchestration through `example_graph.ipynb`, building a document quality review loop that demonstrates typed state, conditional edges, and refinement cycles.

## The Problem with Implicit Control Flow

When control logic is embedded in prompts or scattered across code, reasoning about system behavior becomes difficult. Questions like "what happens if the quality check fails?" or "how many times can the system retry?" require tracing through prompts and conditionals. Bugs hide in implicit assumptions.

Graphs externalize this control flow. Each possible path through the system is visible in the graph structure. Transitions are explicit, exit conditions are auditable, and the entire execution flow can be visualized before running.

## Typed State as Contract

The example defines state as a dataclass:

```python
@dataclass
class DocumentState:
    topic: str
    draft: str = ""
    score: int = 0
    feedback: str = ""
    revision_count: int = 0
    max_revisions: int = 3
```

This state flows through the graph, accumulating results from each node. The typed structure serves as a contract between nodes: each node knows exactly what data it receives and what it must provide. Invalid or missing data fails early with clear errors rather than propagating silently.

The state also captures operational metadata like `revision_count` and `max_revisions`. This makes termination conditions explicit in the data structure itself, not hidden in scattered conditionals.

## Nodes as Units of Work

Each node is a dataclass with a `run` method. The return type annotation determines which nodes can follow:

```python
@dataclass
class GenerateDraft(BaseNode[DocumentState]):
    async def run(self, ctx: GraphRunContext[DocumentState]) -> "EvaluateQuality":
        # Generate draft, update state
        return EvaluateQuality()
```

`GenerateDraft` can only transition to `EvaluateQuality`. This constraint is enforced by the type system. The graph framework uses these annotations to build the edge structure automatically.

Nodes access and modify state through `ctx.state`. The context provides a consistent interface regardless of where the node sits in the graph.

## Conditional Edges

The `EvaluateQuality` node demonstrates conditional transitions through union return types:

```python
async def run(self, ctx: GraphRunContext[DocumentState]) -> "Revise | End[str]":
    # Evaluate quality...

    if ctx.state.score >= QUALITY_THRESHOLD:
        return End(ctx.state.draft)

    if ctx.state.revision_count >= ctx.state.max_revisions:
        return End(ctx.state.draft)

    return Revise()
```

The return type `Revise | End[str]` declares that this node can transition to either `Revise` or terminate with a string result. The actual transition depends on runtime conditions evaluated against the state.

This pattern separates the decision logic (what to do) from the graph structure (what's possible). The graph defines the space of valid behaviors; the node logic navigates within that space.

## Refinement Loops

The cycle between `EvaluateQuality` and `Revise` implements a refinement loop:

1. `EvaluateQuality` scores the current draft
2. If below threshold, transition to `Revise`
3. `Revise` improves the draft based on feedback
4. Return to `EvaluateQuality` for another check

Because this cycle is explicit in the graph, termination conditions are also explicit. The `max_revisions` check prevents unbounded loops. Both exit paths (quality met, max revisions reached) are visible in the code and in the graph visualization.

## Graph Visualization

pydantic-graph generates mermaid diagrams from the graph structure:

```python
display(Image(graph.mermaid_image(start_node=GenerateDraft)))
```

The visualization shows all nodes and their possible transitions, making the control flow immediately apparent. This is valuable for understanding complex graphs, debugging unexpected behavior, and communicating system design to others.

## Execution

Running the graph requires an initial node and state:

```python
graph = Graph(nodes=[GenerateDraft, EvaluateQuality, Revise])
state = DocumentState(topic="The importance of code reviews")
result = await graph.run(GenerateDraft(), state=state)
```

Execution proceeds by calling each node's `run` method, following transitions until reaching an `End` node. The final result contains the output value passed to `End`.

## Why Graphs Matter

Graphs shift orchestration from implicit to explicit. The structure is inspectable before execution, paths can be enumerated, and termination is verifiable. When something goes wrong, the execution trace maps directly to the graph, simplifying debugging.

For complex agentic systems with conditional logic, retries, and multiple paths, graphs provide the foundation for reliable, production-grade orchestration.

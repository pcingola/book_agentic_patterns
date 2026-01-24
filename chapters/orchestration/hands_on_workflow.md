## Hands-On: Sequential Workflows

A workflow externalizes control flow from the agent's reasoning. Instead of a single agent deciding what to do next, the orchestrator defines explicit stages, each with a focused responsibility. The agent reasons within each stage; the workflow determines when and how stages connect.

This hands-on explores a content generation pipeline through `example_workflow.ipynb`. The pipeline has three stages: outline, draft, and edit. Each stage produces typed output that feeds the next. The pattern demonstrates delegation, state passing, and how workflows create predictable, auditable execution paths.

## Typed Stage Outputs

Each stage in the workflow produces structured output defined by a Pydantic model. These models serve as contracts between stages, making the data flow explicit and type-checked.

```python
class Outline(BaseModel):
    title: str = Field(description="Article title")
    sections: list[str] = Field(description="Section headings in order")
    key_points: list[str] = Field(description="Main points to cover")

class Draft(BaseModel):
    content: str = Field(description="Full article text")
    word_count: int = Field(description="Approximate word count")

class EditedArticle(BaseModel):
    content: str = Field(description="Final edited article")
    changes_made: list[str] = Field(description="Summary of edits applied")
```

The `Outline` model captures the structure an article needs. The `Draft` model holds the written content. The `EditedArticle` model includes both the final text and a record of what changed. Each model defines exactly what its stage produces, nothing more.

When you configure an agent with `output_type=Outline`, PydanticAI ensures the response conforms to that schema. If the model's output doesn't match, the framework retries or raises an error. This enforcement means downstream stages can trust the shape of their inputs.

## Shared State

A simple container accumulates outputs as the workflow progresses:

```python
class WorkflowState(BaseModel):
    topic: str
    outline: Outline | None = None
    draft: Draft | None = None
    final: EditedArticle | None = None

state = WorkflowState(topic="The benefits of morning exercise routines")
```

The state starts with only the topic. As each stage completes, its output is stored in the corresponding field. This accumulation pattern lets later stages access earlier results. The editor can reference both the original outline and the draft when making improvements.

State could be a simple dictionary, but using a typed model provides the same benefits as typed outputs: clarity about what exists at each point in the workflow, and errors if something is accessed before it's populated.

## Stage Execution

Each stage follows the same pattern: create a specialized agent, construct a prompt using available state, run the agent, and store the result.

```python
outline_agent = get_agent(
    output_type=Outline,
    system_prompt="You are an outline specialist. Create clear, logical article structures."
)

outline_prompt = f"Create an outline for a short article about: {state.topic}"

agent_run, _ = await run_agent(outline_agent, outline_prompt)
state.outline = agent_run.result.output
```

The agent is configured with two key parameters: `output_type` constrains the response format, and `system_prompt` establishes the agent's role. The prompt incorporates state (in this case, just the topic). After execution, the typed output is stored in the shared state.

The draft stage follows the same structure but pulls more from state:

```python
draft_prompt = f"""Write a short article (~300 words) based on this outline:

Title: {state.outline.title}
Sections: {', '.join(state.outline.sections)}
Key points to cover: {', '.join(state.outline.key_points)}"""
```

The outline's fields flow directly into the prompt. The draft agent doesn't need to know how the outline was created; it just receives structured input and produces structured output.

## Delegation Without Autonomy

This workflow demonstrates delegation in its simplest form. The orchestrator (the code running the notebook) assigns tasks to specialist agents. Each agent handles a focused subtask and returns. Control never transfers between agents directly; it always flows back through the orchestrator.

This is different from autonomous agents that decide their own next steps. Here, the sequence is fixed: outline, then draft, then edit. The agents have no say in this order. They reason about their specific task, not about what task to do.

The tradeoff is flexibility versus predictability. An autonomous agent might decide the outline needs revision after seeing the draft. This workflow won't. But this workflow is easier to debug, test, and explain. When something goes wrong, you know exactly which stage failed and what inputs it received.

## The Pipeline as a Function

Encapsulating the workflow makes it reusable:

```python
async def content_pipeline(topic: str) -> WorkflowState:
    """Run the complete content generation workflow."""
    state = WorkflowState(topic=topic)

    # Stage 1: Outline
    outline_agent = get_agent(output_type=Outline, system_prompt="Create clear article outlines.")
    agent_run, _ = await run_agent(outline_agent, f"Create an outline for: {topic}")
    state.outline = agent_run.result.output

    # Stage 2: Draft
    draft_agent = get_agent(output_type=Draft, system_prompt="Write engaging articles from outlines.")
    agent_run, _ = await run_agent(draft_agent, f"Write ~300 words based on: {state.outline.model_dump_json()}")
    state.draft = agent_run.result.output

    # Stage 3: Edit
    editor_agent = get_agent(output_type=EditedArticle, system_prompt="Edit for clarity and engagement.")
    agent_run, _ = await run_agent(editor_agent, f"Edit this article: {state.draft.content}")
    state.final = agent_run.result.output

    return state
```

The function takes a topic and returns a fully populated state. Callers don't need to know about the internal stages. They get a final article along with the intermediate artifacts (outline, draft) if needed for inspection or logging.

This encapsulation also makes the workflow testable. You can mock individual agent calls to verify the orchestration logic, or run the full pipeline against test topics to check end-to-end behavior.

## Why Workflows Matter

Workflows provide structure that pure agent autonomy lacks. By defining explicit stages with typed interfaces, they create checkpoints where you can observe, validate, and intervene. The content pipeline could log each stage's output, retry failed stages with different prompts, or insert human review between draft and edit.

The pattern scales to more complex scenarios. Stages can run conditionally based on earlier results. Branches can handle different content types. Loops can refine output until quality thresholds are met. The key insight remains: externalize control flow from the agent's reasoning.

## Key Takeaways

Workflows define explicit sequences of agent calls with typed interfaces between stages. Each stage is a focused specialist; the orchestrator controls when and how they execute.

Typed outputs using Pydantic models create contracts between stages. Downstream stages can trust the shape of their inputs because the framework enforces schema compliance.

Shared state accumulates outputs as the workflow progresses. Later stages access earlier results through this state, enabling information flow across the pipeline.

Delegation returns control to the orchestrator after each stage. This differs from hand-offs where responsibility transfers between agents. The distinction matters for reasoning about control flow and failure handling.

Encapsulating workflows as functions makes them reusable and testable. The implementation details stay hidden; callers interact with a clean interface.

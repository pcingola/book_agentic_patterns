## Hands-On: Planning and Decomposition

Planning and decomposition separates *what* an agent wants to achieve from *how* it will achieve it. Instead of diving directly into implementation, the agent first reasons at a higher level, identifying major steps and their dependencies, and only then descends into concrete actions. This separation manages complexity, creates opportunities for validation, and produces artifacts that can be inspected or modified before any code is written.

This hands-on explores planning and decomposition using `example_planning_decomposition.ipynb`, demonstrating how explicit planning leads to better-structured implementations.

## Model Selection: Why Non-Thinking Models Matter Here

The notebook uses `config_name="fast"` to select a non-thinking model (Claude 3.5 Sonnet) rather than the default thinking model (Claude Sonnet 4.5). This choice is deliberate.

Modern frontier models like Claude Sonnet 4.5 have extended thinking capabilities baked in. When given a complex task, they spend significant time reasoning internally before responding, sometimes several minutes per request. This is valuable for difficult problems requiring deep analysis, but counterproductive for planning workflows where we want multiple quick iterations.

Planning and decomposition already externalizes reasoning through explicit prompts. We ask the model to show its plan, validate it, decompose steps, and so on. The thinking happens in the conversation, not hidden inside the model. Using a thinking model on top of this would be redundant: the model thinks internally, then produces a plan, which we then ask it to think about again.

Non-thinking models respond in seconds rather than minutes, making interactive planning practical. The explicit structure of planning prompts compensates for the lack of internal deliberation. For production systems with many planning iterations, this difference in latency compounds significantly.

## The Problem: Data Pipeline Design

The notebook tackles building a data pipeline to analyze website traffic logs. This task benefits from planning because it involves multiple distinct phases (data loading, cleaning, analysis, reporting), steps have dependencies (cannot analyze before cleaning), and the overall structure matters as much as individual components.

```python
task = """Build a data pipeline to analyze website traffic logs.

Context:
- Log files are in JSON format, one event per line
- Each event has: timestamp, user_id, page_url, referrer, user_agent
- Files are stored in an S3 bucket, organized by date (logs/YYYY/MM/DD/)
- Need to produce a daily report showing:
  * Total page views and unique visitors
  * Top 10 most visited pages
  * Traffic sources breakdown (direct, search, social, referral)
  * Hourly traffic pattern

Design and implement this pipeline."""
```

Without explicit planning, a model might jump straight into writing code, making design decisions implicitly as it goes. The resulting implementation might work, but its structure emerges accidentally rather than intentionally. Refactoring later requires understanding the entire codebase to see the implicit architecture.

## Step 1: Generate the Plan

The first step asks the model to create an explicit plan without writing any code. This separation is enforced through the system prompt and the task prompt.

```python
system_prompt_planner = """You are a software architect. Your job is to create implementation plans.
Do NOT write code. Create a structured plan that a developer can follow."""

prompt_plan = f"""{task}

Create a detailed implementation plan. For each step:
1. Give it a clear name
2. Describe what it accomplishes
3. List inputs it requires
4. List outputs it produces
5. Note any dependencies on other steps

Format as a numbered list. Do not write code."""

agent_planner = get_agent(config_name="fast", system_prompt=system_prompt_planner)
agent_run_plan, nodes_plan = await run_agent(agent_planner, prompt_plan)
```

The prompt asks for specific elements for each step: name, description, inputs, outputs, and dependencies. This structured format makes the plan machine-readable and forces the model to think about data flow between steps. A typical response might include steps like "Load Log Files from S3", "Parse JSON Events", "Classify Traffic Sources", "Compute Hourly Aggregates", and "Generate Report".

The key insight is that the plan itself is an artifact. It can be printed, reviewed by a human, stored for documentation, or passed to another system. This externalization is what distinguishes planning from Chain-of-Thought reasoning, where the reasoning trace is interleaved with execution.

## Step 2: Validate the Plan

Before implementing anything, the model reviews its own plan for completeness and correctness. This self-validation catches issues early, before any code is written.

```python
message_history = nodes_to_message_history(nodes_plan)

prompt_validate = """Review the plan you created. Check for:

1. Completeness: Does the plan cover all requirements?
2. Dependencies: Are step dependencies correctly ordered?
3. Feasibility: Are there any steps that seem unclear or underspecified?
4. Missing steps: Is anything needed that wasn't included?

If issues are found, provide an updated plan. Otherwise confirm the plan is ready."""

agent_run_validate, nodes_validate = await run_agent(agent_planner, prompt_validate, message_history=message_history)
```

The `message_history` parameter carries forward the previous conversation, so the model sees its original plan when asked to validate it. The validation prompt specifies concrete criteria: completeness, dependency ordering, feasibility, and missing steps.

This step often catches oversights. The model might realize it forgot error handling, or that two steps were listed in the wrong order, or that a requirement from the original task was not addressed. Fixing these issues at the plan level is cheap; fixing them after implementation is expensive.

## Step 3: Decompose a Complex Step

Not all steps in a plan are equally simple. Some require further breakdown before they can be implemented. The decomposition step takes a complex step and breaks it into atomic sub-tasks.

```python
message_history = nodes_to_message_history(nodes_validate)

prompt_decompose = """The 'Traffic Sources Classification' step is complex.
Decompose it into smaller sub-tasks:

1. List each sub-task needed
2. Explain the logic for each classification category
3. Describe how to handle edge cases (unknown referrers, missing data)

Keep the sub-tasks atomic and implementable."""

agent_run_decompose, nodes_decompose = await run_agent(agent_planner, prompt_decompose, message_history=message_history)
```

Traffic source classification is a good candidate for decomposition because it involves multiple categories (direct, search, social, referral), each with different detection logic. The decomposition might produce sub-tasks like "Extract referrer domain", "Match against known search engine list", "Match against known social media domains", "Apply fallback classification for unknown referrers".

This hierarchical decomposition can be applied recursively. If a sub-task is still too complex, decompose it further. The goal is to reach steps that are small enough to implement confidently in a single function or code block.

## Step 4: Implement From the Plan

With a validated, decomposed plan in hand, implementation becomes straightforward. The model follows the plan rather than inventing structure as it goes.

```python
system_prompt_implementer = """You are a Python developer. Implement code following the given plan.
Write clean, well-structured code. Follow the plan exactly."""

message_history = nodes_to_message_history(nodes_decompose)

prompt_implement = """Implement the data pipeline following the plan.

Create Python code that:
1. Follows the step structure from the plan
2. Implements each step as a separate function
3. Includes type hints and docstrings
4. Has a main() function that orchestrates the pipeline

Use boto3 for S3, pandas for data processing."""

agent_implementer = get_agent(config_name="fast", system_prompt=system_prompt_implementer)
agent_run_impl, _ = await run_agent(agent_implementer, prompt_implement, message_history=message_history)
```

The implementation prompt explicitly instructs the model to follow the plan structure. Each plan step becomes a function, and the main function orchestrates them according to the dependency order established in planning. The resulting code is modular by design, not by accident.

Because the plan was externalized, the implementation is traceable. Each function can be mapped back to a plan step, making the code easier to understand, test, and modify.

## The Planning Loop

The four steps form a planning loop that can be extended or repeated as needed:

1. **Generate**: Create an initial plan from the high-level goal
2. **Validate**: Check the plan for completeness and correctness
3. **Decompose**: Break complex steps into atomic sub-tasks
4. **Implement**: Execute the plan by writing code

In practice, this loop is often iterative. Implementation might reveal that a step was underspecified, triggering a return to planning. Validation might suggest a different approach, requiring a new plan. The explicit structure makes these iterations manageable because each artifact (plan, validation, decomposition) is preserved and can be referenced.

## When Planning Helps

Planning and decomposition is most valuable for tasks that involve multiple phases with dependencies, where the overall structure matters as much as individual components, when you want to review the approach before committing to implementation, when the task is large enough that working memory becomes a bottleneck, or when multiple people (or agents) will collaborate on implementation.

The pattern is less valuable for simple tasks that can be solved in a single step, exploratory work where the goal is unclear, or problems where the solution approach is already well-known and doesn't need explicit articulation.

## Trade-offs

Planning adds overhead. Generating a plan, validating it, and decomposing steps requires multiple model calls before any implementation begins. For trivial tasks, this overhead is not justified.

The quality of the plan depends on the clarity of the original task description. Vague requirements produce vague plans. Planning does not substitute for good problem specification.

Plans can become stale. If requirements change mid-implementation, the plan may need to be regenerated. Maintaining synchronization between plans and code requires discipline.

Despite these trade-offs, explicit planning consistently improves outcomes for complex tasks by making structure intentional rather than accidental, and by creating opportunities for validation before implementation begins.

## Connection to Other Patterns

Planning and decomposition connects naturally with other agentic patterns.

**Chain-of-Thought** externalizes reasoning but mixes it with execution. Planning separates the two, making the reasoning artifact (the plan) independent from the execution artifact (the code).

**Self-Reflection** validates outputs. The plan validation step is a form of self-reflection applied to plans rather than final outputs.

**Tree of Thought** explores multiple approaches. Planning could be combined with Tree of Thought by generating multiple plans, evaluating them, and selecting the best before implementation.

**Verification** checks correctness. After implementation, verification can confirm that the code actually implements the plan correctly.

In advanced systems, planning becomes a first-class capability that agents invoke when facing complex tasks, much like how a human developer might sketch an architecture before writing code.

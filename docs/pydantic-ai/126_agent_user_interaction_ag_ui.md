# Agent User Interaction (AG-UI)

Example of using Pydantic AI agents with the [AG-UI Dojo](https://github.com/ag-ui-protocol/ag-ui/tree/main/apps/dojo) example app.

See the [AG-UI docs](https://ai.pydantic.dev/ui/ag-ui/index.md) for more information about the AG-UI integration.

Demonstrates:

- [AG-UI](https://ai.pydantic.dev/ui/ag-ui/index.md)
- [Tools](https://ai.pydantic.dev/tools/index.md)

## Prerequisites

- An [OpenAI API key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-openai-api-key)

## Running the Example

With [dependencies installed and environment variables set](https://ai.pydantic.dev/examples/setup/#usage) you will need two command line windows.

### Pydantic AI AG-UI backend

Setup your OpenAI API Key

```bash
export OPENAI_API_KEY=<your api key>
```

Start the Pydantic AI AG-UI example backend.

```bash
python -m pydantic_ai_examples.ag_ui
```

```bash
uv run -m pydantic_ai_examples.ag_ui
```

### AG-UI Dojo example frontend

Next run the AG-UI Dojo example frontend.

1. Clone the [AG-UI repository](https://github.com/ag-ui-protocol/ag-ui)

   ```shell
   git clone https://github.com/ag-ui-protocol/ag-ui.git
   ```

1. Change into to the `ag-ui/typescript-sdk` directory

   ```shell
   cd ag-ui/sdks/typescript
   ```

1. Run the Dojo app following the [official instructions](https://github.com/ag-ui-protocol/ag-ui/tree/main/apps/dojo#development-setup)

1. Visit <http://localhost:3000/pydantic-ai>

1. Select View `Pydantic AI` from the sidebar

## Feature Examples

### Agentic Chat

This demonstrates a basic agent interaction including Pydantic AI server side tools and AG-UI client side tools.

If you've [run the example](#running-the-example), you can view it at <http://localhost:3000/pydantic-ai/feature/agentic_chat>.

#### Agent Tools

- `time` - Pydantic AI tool to check the current time for a time zone
- `background` - AG-UI tool to set the background color of the client window

#### Agent Prompts

```text
What is the time in New York?
```

```text
Change the background to blue
```

A complex example which mixes both AG-UI and Pydantic AI tools:

```text
Perform the following steps, waiting for the response of each step before continuing:
1. Get the time
2. Set the background to red
3. Get the time
4. Report how long the background set took by diffing the two times
```

#### Agentic Chat - Code

[Learn about Gateway](https://ai.pydantic.dev/gateway) [ag_ui/api/agentic_chat.py](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/ag_ui/api/agentic_chat.py)

```python
"""Agentic Chat feature."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic_ai import Agent
from pydantic_ai.ui.ag_ui.app import AGUIApp

agent = Agent('gateway/openai:gpt-5-mini')


@agent.tool_plain
async def current_time(timezone: str = 'UTC') -> str:
    """Get the current time in ISO format.

    Args:
        timezone: The timezone to use.

    Returns:
        The current time in ISO format string.
    """
    tz: ZoneInfo = ZoneInfo(timezone)
    return datetime.now(tz=tz).isoformat()


app = AGUIApp(agent)
```

[ag_ui/api/agentic_chat.py](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/ag_ui/api/agentic_chat.py)

```python
"""Agentic Chat feature."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic_ai import Agent
from pydantic_ai.ui.ag_ui.app import AGUIApp

agent = Agent('openai:gpt-5-mini')


@agent.tool_plain
async def current_time(timezone: str = 'UTC') -> str:
    """Get the current time in ISO format.

    Args:
        timezone: The timezone to use.

    Returns:
        The current time in ISO format string.
    """
    tz: ZoneInfo = ZoneInfo(timezone)
    return datetime.now(tz=tz).isoformat()


app = AGUIApp(agent)
```

### Agentic Generative UI

Demonstrates a long running task where the agent sends updates to the frontend to let the user know what's happening.

If you've [run the example](#running-the-example), you can view it at <http://localhost:3000/pydantic-ai/feature/agentic_generative_ui>.

#### Plan Prompts

```text
Create a plan for breakfast and execute it
```

#### Agentic Generative UI - Code

[Learn about Gateway](https://ai.pydantic.dev/gateway) [ag_ui/api/agentic_generative_ui.py](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/ag_ui/api/agentic_generative_ui.py)

```python
"""Agentic Generative UI feature."""

from __future__ import annotations

from textwrap import dedent
from typing import Any, Literal

from pydantic import BaseModel, Field

from ag_ui.core import EventType, StateDeltaEvent, StateSnapshotEvent
from pydantic_ai import Agent
from pydantic_ai.ui.ag_ui.app import AGUIApp

StepStatus = Literal['pending', 'completed']


class Step(BaseModel):
    """Represents a step in a plan."""

    description: str = Field(description='The description of the step')
    status: StepStatus = Field(
        default='pending',
        description='The status of the step (e.g., pending, completed)',
    )


class Plan(BaseModel):
    """Represents a plan with multiple steps."""

    steps: list[Step] = Field(
        default_factory=list[Step], description='The steps in the plan'
    )


class JSONPatchOp(BaseModel):
    """A class representing a JSON Patch operation (RFC 6902)."""

    op: Literal['add', 'remove', 'replace', 'move', 'copy', 'test'] = Field(
        description='The operation to perform: add, remove, replace, move, copy, or test',
    )
    path: str = Field(description='JSON Pointer (RFC 6901) to the target location')
    value: Any = Field(
        default=None,
        description='The value to apply (for add, replace operations)',
    )
    from_: str | None = Field(
        default=None,
        alias='from',
        description='Source path (for move, copy operations)',
    )


agent = Agent(
    'gateway/openai:gpt-5-mini',
    instructions=dedent(
        """
        When planning use tools only, without any other messages.
        IMPORTANT:
        - Use the `create_plan` tool to set the initial state of the steps
        - Use the `update_plan_step` tool to update the status of each step
        - Do NOT repeat the plan or summarise it in a message
        - Do NOT confirm the creation or updates in a message
        - Do NOT ask the user for additional information or next steps

        Only one plan can be active at a time, so do not call the `create_plan` tool
        again until all the steps in current plan are completed.
        """
    ),
)


@agent.tool_plain
async def create_plan(steps: list[str]) -> StateSnapshotEvent:
    """Create a plan with multiple steps.

    Args:
        steps: List of step descriptions to create the plan.

    Returns:
        StateSnapshotEvent containing the initial state of the steps.
    """
    plan: Plan = Plan(
        steps=[Step(description=step) for step in steps],
    )
    return StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot=plan.model_dump(),
    )


@agent.tool_plain
async def update_plan_step(
    index: int, description: str | None = None, status: StepStatus | None = None
) -> StateDeltaEvent:
    """Update the plan with new steps or changes.

    Args:
        index: The index of the step to update.
        description: The new description for the step.
        status: The new status for the step.

    Returns:
        StateDeltaEvent containing the changes made to the plan.
    """
    changes: list[JSONPatchOp] = []
    if description is not None:
        changes.append(
            JSONPatchOp(
                op='replace', path=f'/steps/{index}/description', value=description
            )
        )
    if status is not None:
        changes.append(
            JSONPatchOp(op='replace', path=f'/steps/{index}/status', value=status)
        )
    return StateDeltaEvent(
        type=EventType.STATE_DELTA,
        delta=changes,
    )


app = AGUIApp(agent)
```

[ag_ui/api/agentic_generative_ui.py](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/ag_ui/api/agentic_generative_ui.py)

```python
"""Agentic Generative UI feature."""

from __future__ import annotations

from textwrap import dedent
from typing import Any, Literal

from pydantic import BaseModel, Field

from ag_ui.core import EventType, StateDeltaEvent, StateSnapshotEvent
from pydantic_ai import Agent
from pydantic_ai.ui.ag_ui.app import AGUIApp

StepStatus = Literal['pending', 'completed']


class Step(BaseModel):
    """Represents a step in a plan."""

    description: str = Field(description='The description of the step')
    status: StepStatus = Field(
        default='pending',
        description='The status of the step (e.g., pending, completed)',
    )


class Plan(BaseModel):
    """Represents a plan with multiple steps."""

    steps: list[Step] = Field(
        default_factory=list[Step], description='The steps in the plan'
    )


class JSONPatchOp(BaseModel):
    """A class representing a JSON Patch operation (RFC 6902)."""

    op: Literal['add', 'remove', 'replace', 'move', 'copy', 'test'] = Field(
        description='The operation to perform: add, remove, replace, move, copy, or test',
    )
    path: str = Field(description='JSON Pointer (RFC 6901) to the target location')
    value: Any = Field(
        default=None,
        description='The value to apply (for add, replace operations)',
    )
    from_: str | None = Field(
        default=None,
        alias='from',
        description='Source path (for move, copy operations)',
    )


agent = Agent(
    'openai:gpt-5-mini',
    instructions=dedent(
        """
        When planning use tools only, without any other messages.
        IMPORTANT:
        - Use the `create_plan` tool to set the initial state of the steps
        - Use the `update_plan_step` tool to update the status of each step
        - Do NOT repeat the plan or summarise it in a message
        - Do NOT confirm the creation or updates in a message
        - Do NOT ask the user for additional information or next steps

        Only one plan can be active at a time, so do not call the `create_plan` tool
        again until all the steps in current plan are completed.
        """
    ),
)


@agent.tool_plain
async def create_plan(steps: list[str]) -> StateSnapshotEvent:
    """Create a plan with multiple steps.

    Args:
        steps: List of step descriptions to create the plan.

    Returns:
        StateSnapshotEvent containing the initial state of the steps.
    """
    plan: Plan = Plan(
        steps=[Step(description=step) for step in steps],
    )
    return StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot=plan.model_dump(),
    )


@agent.tool_plain
async def update_plan_step(
    index: int, description: str | None = None, status: StepStatus | None = None
) -> StateDeltaEvent:
    """Update the plan with new steps or changes.

    Args:
        index: The index of the step to update.
        description: The new description for the step.
        status: The new status for the step.

    Returns:
        StateDeltaEvent containing the changes made to the plan.
    """
    changes: list[JSONPatchOp] = []
    if description is not None:
        changes.append(
            JSONPatchOp(
                op='replace', path=f'/steps/{index}/description', value=description
            )
        )
    if status is not None:
        changes.append(
            JSONPatchOp(op='replace', path=f'/steps/{index}/status', value=status)
        )
    return StateDeltaEvent(
        type=EventType.STATE_DELTA,
        delta=changes,
    )


app = AGUIApp(agent)
```

### Human in the Loop

Demonstrates simple human in the loop workflow where the agent comes up with a plan and the user can approve it using checkboxes.

#### Task Planning Tools

- `generate_task_steps` - AG-UI tool to generate and confirm steps

#### Task Planning Prompt

```text
Generate a list of steps for cleaning a car for me to review
```

#### Human in the Loop - Code

[Learn about Gateway](https://ai.pydantic.dev/gateway) [ag_ui/api/human_in_the_loop.py](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/ag_ui/api/human_in_the_loop.py)

```python
"""Human in the Loop Feature.

No special handling is required for this feature.
"""

from __future__ import annotations

from textwrap import dedent

from pydantic_ai import Agent
from pydantic_ai.ui.ag_ui.app import AGUIApp

agent = Agent(
    'gateway/openai:gpt-5-mini',
    instructions=dedent(
        """
        When planning tasks use tools only, without any other messages.
        IMPORTANT:
        - Use the `generate_task_steps` tool to display the suggested steps to the user
        - Never repeat the plan, or send a message detailing steps
        - If accepted, confirm the creation of the plan and the number of selected (enabled) steps only
        - If not accepted, ask the user for more information, DO NOT use the `generate_task_steps` tool again
        """
    ),
)

app = AGUIApp(agent)
```

[ag_ui/api/human_in_the_loop.py](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/ag_ui/api/human_in_the_loop.py)

```python
"""Human in the Loop Feature.

No special handling is required for this feature.
"""

from __future__ import annotations

from textwrap import dedent

from pydantic_ai import Agent
from pydantic_ai.ui.ag_ui.app import AGUIApp

agent = Agent(
    'openai:gpt-5-mini',
    instructions=dedent(
        """
        When planning tasks use tools only, without any other messages.
        IMPORTANT:
        - Use the `generate_task_steps` tool to display the suggested steps to the user
        - Never repeat the plan, or send a message detailing steps
        - If accepted, confirm the creation of the plan and the number of selected (enabled) steps only
        - If not accepted, ask the user for more information, DO NOT use the `generate_task_steps` tool again
        """
    ),
)

app = AGUIApp(agent)
```

### Predictive State Updates

Demonstrates how to use the predictive state updates feature to update the state of the UI based on agent responses, including user interaction via user confirmation.

If you've [run the example](#running-the-example), you can view it at <http://localhost:3000/pydantic-ai/feature/predictive_state_updates>.

#### Story Tools

- `write_document` - AG-UI tool to write the document to a window
- `document_predict_state` - Pydantic AI tool that enables document state prediction for the `write_document` tool

This also shows how to use custom instructions based on shared state information.

#### Story Example

Starting document text

```markdown
Bruce was a good dog,
```

Agent prompt

```text
Help me complete my story about bruce the dog, is should be no longer than a sentence.
```

#### Predictive State Updates - Code

[Learn about Gateway](https://ai.pydantic.dev/gateway) [ag_ui/api/predictive_state_updates.py](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/ag_ui/api/predictive_state_updates.py)

```python
"""Predictive State feature."""

from __future__ import annotations

from textwrap import dedent

from pydantic import BaseModel

from ag_ui.core import CustomEvent, EventType
from pydantic_ai import Agent, RunContext
from pydantic_ai.ui import StateDeps
from pydantic_ai.ui.ag_ui.app import AGUIApp


class DocumentState(BaseModel):
    """State for the document being written."""

    document: str = ''


agent = Agent('gateway/openai:gpt-5-mini', deps_type=StateDeps[DocumentState])


# Tools which return AG-UI events will be sent to the client as part of the
# event stream, single events and iterables of events are supported.
@agent.tool_plain
async def document_predict_state() -> list[CustomEvent]:
    """Enable document state prediction.

    Returns:
        CustomEvent containing the event to enable state prediction.
    """
    return [
        CustomEvent(
            type=EventType.CUSTOM,
            name='PredictState',
            value=[
                {
                    'state_key': 'document',
                    'tool': 'write_document',
                    'tool_argument': 'document',
                },
            ],
        ),
    ]


@agent.instructions()
async def story_instructions(ctx: RunContext[StateDeps[DocumentState]]) -> str:
    """Provide instructions for writing document if present.

    Args:
        ctx: The run context containing document state information.

    Returns:
        Instructions string for the document writing agent.
    """
    return dedent(
        f"""You are a helpful assistant for writing documents.

        Before you start writing, you MUST call the `document_predict_state`
        tool to enable state prediction.

        To present the document to the user for review, you MUST use the
        `write_document` tool.

        When you have written the document, DO NOT repeat it as a message.
        If accepted briefly summarize the changes you made, 2 sentences
        max, otherwise ask the user to clarify what they want to change.

        This is the current document:

        {ctx.deps.state.document}
        """
    )


app = AGUIApp(agent, deps=StateDeps(DocumentState()))
```

[ag_ui/api/predictive_state_updates.py](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/ag_ui/api/predictive_state_updates.py)

```python
"""Predictive State feature."""

from __future__ import annotations

from textwrap import dedent

from pydantic import BaseModel

from ag_ui.core import CustomEvent, EventType
from pydantic_ai import Agent, RunContext
from pydantic_ai.ui import StateDeps
from pydantic_ai.ui.ag_ui.app import AGUIApp


class DocumentState(BaseModel):
    """State for the document being written."""

    document: str = ''


agent = Agent('openai:gpt-5-mini', deps_type=StateDeps[DocumentState])


# Tools which return AG-UI events will be sent to the client as part of the
# event stream, single events and iterables of events are supported.
@agent.tool_plain
async def document_predict_state() -> list[CustomEvent]:
    """Enable document state prediction.

    Returns:
        CustomEvent containing the event to enable state prediction.
    """
    return [
        CustomEvent(
            type=EventType.CUSTOM,
            name='PredictState',
            value=[
                {
                    'state_key': 'document',
                    'tool': 'write_document',
                    'tool_argument': 'document',
                },
            ],
        ),
    ]


@agent.instructions()
async def story_instructions(ctx: RunContext[StateDeps[DocumentState]]) -> str:
    """Provide instructions for writing document if present.

    Args:
        ctx: The run context containing document state information.

    Returns:
        Instructions string for the document writing agent.
    """
    return dedent(
        f"""You are a helpful assistant for writing documents.

        Before you start writing, you MUST call the `document_predict_state`
        tool to enable state prediction.

        To present the document to the user for review, you MUST use the
        `write_document` tool.

        When you have written the document, DO NOT repeat it as a message.
        If accepted briefly summarize the changes you made, 2 sentences
        max, otherwise ask the user to clarify what they want to change.

        This is the current document:

        {ctx.deps.state.document}
        """
    )


app = AGUIApp(agent, deps=StateDeps(DocumentState()))
```

### Shared State

Demonstrates how to use the shared state between the UI and the agent.

State sent to the agent is detected by a function based instruction. This then validates the data using a custom pydantic model before using to create the instructions for the agent to follow and send to the client using a AG-UI tool.

If you've [run the example](#running-the-example), you can view it at <http://localhost:3000/pydantic-ai/feature/shared_state>.

#### Recipe Tools

- `display_recipe` - AG-UI tool to display the recipe in a graphical format

#### Recipe Example

1. Customise the basic settings of your recipe
1. Click `Improve with AI`

#### Shared State - Code

[Learn about Gateway](https://ai.pydantic.dev/gateway) [ag_ui/api/shared_state.py](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/ag_ui/api/shared_state.py)

```python
"""Shared State feature."""

from __future__ import annotations

from enum import Enum
from textwrap import dedent

from pydantic import BaseModel, Field

from ag_ui.core import EventType, StateSnapshotEvent
from pydantic_ai import Agent, RunContext
from pydantic_ai.ui import StateDeps
from pydantic_ai.ui.ag_ui.app import AGUIApp


class SkillLevel(str, Enum):
    """The level of skill required for the recipe."""

    BEGINNER = 'Beginner'
    INTERMEDIATE = 'Intermediate'
    ADVANCED = 'Advanced'


class SpecialPreferences(str, Enum):
    """Special preferences for the recipe."""

    HIGH_PROTEIN = 'High Protein'
    LOW_CARB = 'Low Carb'
    SPICY = 'Spicy'
    BUDGET_FRIENDLY = 'Budget-Friendly'
    ONE_POT_MEAL = 'One-Pot Meal'
    VEGETARIAN = 'Vegetarian'
    VEGAN = 'Vegan'


class CookingTime(str, Enum):
    """The cooking time of the recipe."""

    FIVE_MIN = '5 min'
    FIFTEEN_MIN = '15 min'
    THIRTY_MIN = '30 min'
    FORTY_FIVE_MIN = '45 min'
    SIXTY_PLUS_MIN = '60+ min'


class Ingredient(BaseModel):
    """A class representing an ingredient in a recipe."""

    icon: str = Field(
        default='ingredient',
        description="The icon emoji (not emoji code like '\x1f35e', but the actual emoji like ðŸ¥•) of the ingredient",
    )
    name: str
    amount: str


class Recipe(BaseModel):
    """A class representing a recipe."""

    skill_level: SkillLevel = Field(
        default=SkillLevel.BEGINNER,
        description='The skill level required for the recipe',
    )
    special_preferences: list[SpecialPreferences] = Field(
        default_factory=list[SpecialPreferences],
        description='Any special preferences for the recipe',
    )
    cooking_time: CookingTime = Field(
        default=CookingTime.FIVE_MIN, description='The cooking time of the recipe'
    )
    ingredients: list[Ingredient] = Field(
        default_factory=list[Ingredient],
        description='Ingredients for the recipe',
    )
    instructions: list[str] = Field(
        default_factory=list[str], description='Instructions for the recipe'
    )


class RecipeSnapshot(BaseModel):
    """A class representing the state of the recipe."""

    recipe: Recipe = Field(
        default_factory=Recipe, description='The current state of the recipe'
    )


agent = Agent('gateway/openai:gpt-5-mini', deps_type=StateDeps[RecipeSnapshot])


@agent.tool_plain
async def display_recipe(recipe: Recipe) -> StateSnapshotEvent:
    """Display the recipe to the user.

    Args:
        recipe: The recipe to display.

    Returns:
        StateSnapshotEvent containing the recipe snapshot.
    """
    return StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={'recipe': recipe},
    )


@agent.instructions
async def recipe_instructions(ctx: RunContext[StateDeps[RecipeSnapshot]]) -> str:
    """Instructions for the recipe generation agent.

    Args:
        ctx: The run context containing recipe state information.

    Returns:
        Instructions string for the recipe generation agent.
    """
    return dedent(
        f"""
        You are a helpful assistant for creating recipes.

        IMPORTANT:
        - Create a complete recipe using the existing ingredients
        - Append new ingredients to the existing ones
        - Use the `display_recipe` tool to present the recipe to the user
        - Do NOT repeat the recipe in the message, use the tool instead
        - Do NOT run the `display_recipe` tool multiple times in a row

        Once you have created the updated recipe and displayed it to the user,
        summarise the changes in one sentence, don't describe the recipe in
        detail or send it as a message to the user.

        The current state of the recipe is:

        {ctx.deps.state.recipe.model_dump_json(indent=2)}
        """,
    )


app = AGUIApp(agent, deps=StateDeps(RecipeSnapshot()))
```

[ag_ui/api/shared_state.py](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/ag_ui/api/shared_state.py)

```python
"""Shared State feature."""

from __future__ import annotations

from enum import Enum
from textwrap import dedent

from pydantic import BaseModel, Field

from ag_ui.core import EventType, StateSnapshotEvent
from pydantic_ai import Agent, RunContext
from pydantic_ai.ui import StateDeps
from pydantic_ai.ui.ag_ui.app import AGUIApp


class SkillLevel(str, Enum):
    """The level of skill required for the recipe."""

    BEGINNER = 'Beginner'
    INTERMEDIATE = 'Intermediate'
    ADVANCED = 'Advanced'


class SpecialPreferences(str, Enum):
    """Special preferences for the recipe."""

    HIGH_PROTEIN = 'High Protein'
    LOW_CARB = 'Low Carb'
    SPICY = 'Spicy'
    BUDGET_FRIENDLY = 'Budget-Friendly'
    ONE_POT_MEAL = 'One-Pot Meal'
    VEGETARIAN = 'Vegetarian'
    VEGAN = 'Vegan'


class CookingTime(str, Enum):
    """The cooking time of the recipe."""

    FIVE_MIN = '5 min'
    FIFTEEN_MIN = '15 min'
    THIRTY_MIN = '30 min'
    FORTY_FIVE_MIN = '45 min'
    SIXTY_PLUS_MIN = '60+ min'


class Ingredient(BaseModel):
    """A class representing an ingredient in a recipe."""

    icon: str = Field(
        default='ingredient',
        description="The icon emoji (not emoji code like '\x1f35e', but the actual emoji like ðŸ¥•) of the ingredient",
    )
    name: str
    amount: str


class Recipe(BaseModel):
    """A class representing a recipe."""

    skill_level: SkillLevel = Field(
        default=SkillLevel.BEGINNER,
        description='The skill level required for the recipe',
    )
    special_preferences: list[SpecialPreferences] = Field(
        default_factory=list[SpecialPreferences],
        description='Any special preferences for the recipe',
    )
    cooking_time: CookingTime = Field(
        default=CookingTime.FIVE_MIN, description='The cooking time of the recipe'
    )
    ingredients: list[Ingredient] = Field(
        default_factory=list[Ingredient],
        description='Ingredients for the recipe',
    )
    instructions: list[str] = Field(
        default_factory=list[str], description='Instructions for the recipe'
    )


class RecipeSnapshot(BaseModel):
    """A class representing the state of the recipe."""

    recipe: Recipe = Field(
        default_factory=Recipe, description='The current state of the recipe'
    )


agent = Agent('openai:gpt-5-mini', deps_type=StateDeps[RecipeSnapshot])


@agent.tool_plain
async def display_recipe(recipe: Recipe) -> StateSnapshotEvent:
    """Display the recipe to the user.

    Args:
        recipe: The recipe to display.

    Returns:
        StateSnapshotEvent containing the recipe snapshot.
    """
    return StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={'recipe': recipe},
    )


@agent.instructions
async def recipe_instructions(ctx: RunContext[StateDeps[RecipeSnapshot]]) -> str:
    """Instructions for the recipe generation agent.

    Args:
        ctx: The run context containing recipe state information.

    Returns:
        Instructions string for the recipe generation agent.
    """
    return dedent(
        f"""
        You are a helpful assistant for creating recipes.

        IMPORTANT:
        - Create a complete recipe using the existing ingredients
        - Append new ingredients to the existing ones
        - Use the `display_recipe` tool to present the recipe to the user
        - Do NOT repeat the recipe in the message, use the tool instead
        - Do NOT run the `display_recipe` tool multiple times in a row

        Once you have created the updated recipe and displayed it to the user,
        summarise the changes in one sentence, don't describe the recipe in
        detail or send it as a message to the user.

        The current state of the recipe is:

        {ctx.deps.state.recipe.model_dump_json(indent=2)}
        """,
    )


app = AGUIApp(agent, deps=StateDeps(RecipeSnapshot()))
```

### Tool Based Generative UI

Demonstrates customised rendering for tool output with used confirmation.

If you've [run the example](#running-the-example), you can view it at <http://localhost:3000/pydantic-ai/feature/tool_based_generative_ui>.

#### Haiku Tools

- `generate_haiku` - AG-UI tool to display a haiku in English and Japanese

#### Haiku Prompt

```text
Generate a haiku about formula 1
```

#### Tool Based Generative UI - Code

[Learn about Gateway](https://ai.pydantic.dev/gateway) [ag_ui/api/tool_based_generative_ui.py](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/ag_ui/api/tool_based_generative_ui.py)

```python
"""Tool Based Generative UI feature.

No special handling is required for this feature.
"""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.ui.ag_ui.app import AGUIApp

agent = Agent('gateway/openai:gpt-5-mini')
app = AGUIApp(agent)
```

[ag_ui/api/tool_based_generative_ui.py](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/ag_ui/api/tool_based_generative_ui.py)

```python
"""Tool Based Generative UI feature.

No special handling is required for this feature.
"""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.ui.ag_ui.app import AGUIApp

agent = Agent('openai:gpt-5-mini')
app = AGUIApp(agent)
```

Small but complete example of using Pydantic AI to build a support agent for a bank.

Demonstrates:

- [dynamic system prompt](https://ai.pydantic.dev/agent/#system-prompts)
- [structured `output_type`](https://ai.pydantic.dev/output/#structured-output)
- [tools](https://ai.pydantic.dev/tools/index.md)

## Running the Example

With [dependencies installed and environment variables set](https://ai.pydantic.dev/examples/setup/#usage), run:

```bash
python -m pydantic_ai_examples.bank_support
```

```bash
uv run -m pydantic_ai_examples.bank_support
```

(or `PYDANTIC_AI_MODEL=gemini-3-flash-preview ...`)

## Example Code

[Learn about Gateway](https://ai.pydantic.dev/gateway) [bank_support.py](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/bank_support.py)

```python
"""Small but complete example of using Pydantic AI to build a support agent for a bank.

Run with:

    uv run -m pydantic_ai_examples.bank_support
"""

import sqlite3
from dataclasses import dataclass

from pydantic import BaseModel

from pydantic_ai import Agent, RunContext


@dataclass
class DatabaseConn:
    """A wrapper over the SQLite connection."""

    sqlite_conn: sqlite3.Connection

    async def customer_name(self, *, id: int) -> str | None:
        res = cur.execute('SELECT name FROM customers WHERE id=?', (id,))
        row = res.fetchone()
        if row:
            return row[0]
        return None

    async def customer_balance(self, *, id: int) -> float:
        res = cur.execute('SELECT balance FROM customers WHERE id=?', (id,))
        row = res.fetchone()
        if row:
            return row[0]
        else:
            raise ValueError('Customer not found')


@dataclass
class SupportDependencies:
    customer_id: int
    db: DatabaseConn


class SupportOutput(BaseModel):
    support_advice: str
    """Advice returned to the customer"""
    block_card: bool
    """Whether to block their card or not"""
    risk: int
    """Risk level of query"""


support_agent = Agent(
    'gateway/openai:gpt-5.2',
    deps_type=SupportDependencies,
    output_type=SupportOutput,
    instructions=(
        'You are a support agent in our bank, give the '
        'customer support and judge the risk level of their query. '
        "Reply using the customer's name."
    ),
)


@support_agent.instructions
async def add_customer_name(ctx: RunContext[SupportDependencies]) -> str:
    customer_name = await ctx.deps.db.customer_name(id=ctx.deps.customer_id)
    return f"The customer's name is {customer_name!r}"


@support_agent.tool
async def customer_balance(ctx: RunContext[SupportDependencies]) -> str:
    """Returns the customer's current account balance."""
    balance = await ctx.deps.db.customer_balance(
        id=ctx.deps.customer_id,
    )
    return f'${balance:.2f}'


if __name__ == '__main__':
    with sqlite3.connect(':memory:') as con:
        cur = con.cursor()
        cur.execute('CREATE TABLE customers(id, name, balance)')
        cur.execute("""
            INSERT INTO customers VALUES
                (123, 'John', 123.45)
        """)
        con.commit()

        deps = SupportDependencies(customer_id=123, db=DatabaseConn(sqlite_conn=con))
        result = support_agent.run_sync('What is my balance?', deps=deps)
        print(result.output)
        """
        support_advice='Hello John, your current account balance, including pending transactions, is $123.45.' block_card=False risk=1
        """

        result = support_agent.run_sync('I just lost my card!', deps=deps)
        print(result.output)
        """
        support_advice="I'm sorry to hear that, John. We are temporarily blocking your card to prevent unauthorized transactions." block_card=True risk=8
        """
```

[bank_support.py](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/bank_support.py)

```python
"""Small but complete example of using Pydantic AI to build a support agent for a bank.

Run with:

    uv run -m pydantic_ai_examples.bank_support
"""

import sqlite3
from dataclasses import dataclass

from pydantic import BaseModel

from pydantic_ai import Agent, RunContext


@dataclass
class DatabaseConn:
    """A wrapper over the SQLite connection."""

    sqlite_conn: sqlite3.Connection

    async def customer_name(self, *, id: int) -> str | None:
        res = cur.execute('SELECT name FROM customers WHERE id=?', (id,))
        row = res.fetchone()
        if row:
            return row[0]
        return None

    async def customer_balance(self, *, id: int) -> float:
        res = cur.execute('SELECT balance FROM customers WHERE id=?', (id,))
        row = res.fetchone()
        if row:
            return row[0]
        else:
            raise ValueError('Customer not found')


@dataclass
class SupportDependencies:
    customer_id: int
    db: DatabaseConn


class SupportOutput(BaseModel):
    support_advice: str
    """Advice returned to the customer"""
    block_card: bool
    """Whether to block their card or not"""
    risk: int
    """Risk level of query"""


support_agent = Agent(
    'openai:gpt-5.2',
    deps_type=SupportDependencies,
    output_type=SupportOutput,
    instructions=(
        'You are a support agent in our bank, give the '
        'customer support and judge the risk level of their query. '
        "Reply using the customer's name."
    ),
)


@support_agent.instructions
async def add_customer_name(ctx: RunContext[SupportDependencies]) -> str:
    customer_name = await ctx.deps.db.customer_name(id=ctx.deps.customer_id)
    return f"The customer's name is {customer_name!r}"


@support_agent.tool
async def customer_balance(ctx: RunContext[SupportDependencies]) -> str:
    """Returns the customer's current account balance."""
    balance = await ctx.deps.db.customer_balance(
        id=ctx.deps.customer_id,
    )
    return f'${balance:.2f}'


if __name__ == '__main__':
    with sqlite3.connect(':memory:') as con:
        cur = con.cursor()
        cur.execute('CREATE TABLE customers(id, name, balance)')
        cur.execute("""
            INSERT INTO customers VALUES
                (123, 'John', 123.45)
        """)
        con.commit()

        deps = SupportDependencies(customer_id=123, db=DatabaseConn(sqlite_conn=con))
        result = support_agent.run_sync('What is my balance?', deps=deps)
        print(result.output)
        """
        support_advice='Hello John, your current account balance, including pending transactions, is $123.45.' block_card=False risk=1
        """

        result = support_agent.run_sync('I just lost my card!', deps=deps)
        print(result.output)
        """
        support_advice="I'm sorry to hear that, John. We are temporarily blocking your card to prevent unauthorized transactions." block_card=True risk=8
        """
```

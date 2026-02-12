"""Example eval file demonstrating auto-discovery conventions.

The eval runner discovers this file by its `eval_*.py` name, then finds:
- dataset_* objects (Dataset instances)
- target_* functions (exactly one per file)
- scorer_* functions (optional, override default pass/fail logic)
"""

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Contains, IsInstance

from agentic_patterns.core.agents import get_agent, run_agent

dataset_capitals = Dataset(
    cases=[
        Case(
            name="france",
            inputs="What is the capital of France?",
            expected_output="Paris",
            metadata={"difficulty": "easy"},
        ),
        Case(
            name="japan",
            inputs="What is the capital of Japan?",
            expected_output="Tokyo",
            metadata={"difficulty": "easy"},
        ),
        Case(
            name="nepal",
            inputs="What is the capital of Nepal?",
            expected_output="Kathmandu",
            metadata={"difficulty": "medium"},
        ),
    ],
    evaluators=[
        IsInstance(type_name="str"),
        Contains(),
    ],
)


async def target_answer(question: str) -> str:
    """Target function: run the agent and return the text output."""
    agent = get_agent()
    agent_run, _ = await run_agent(agent, question)
    return agent_run.result.output

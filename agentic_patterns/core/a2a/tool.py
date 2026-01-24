"""Tool factory for creating PydanticAI tools from A2A clients."""

import asyncio

from pydantic_ai import RunContext, Tool

from agentic_patterns.core.a2a.client import A2AClientExtended, TaskStatus
from agentic_patterns.core.a2a.utils import extract_text, extract_question, slugify, card_to_prompt


def create_a2a_tool(client: A2AClientExtended, name: str | None = None) -> Tool:
    """Create a PydanticAI tool that delegates to a remote A2A agent.

    The tool returns formatted strings for the coordinator to interpret:
    - [COMPLETED] result text
    - [INPUT_REQUIRED:task_id=xyz] question
    - [FAILED] error message
    - [CANCELLED] task was cancelled
    - [TIMEOUT] task timed out
    """
    card = asyncio.get_event_loop().run_until_complete(client.get_agent_card())
    tool_name = name or slugify(card["name"])

    async def delegate(ctx: RunContext, prompt: str, task_id: str | None = None) -> str:
        """Delegate a task to the remote agent.

        Args:
            ctx: The run context
            prompt: The message to send to the agent
            task_id: Optional task ID to continue a previous conversation

        Returns:
            Formatted string with status prefix and result/message
        """
        def is_cancelled() -> bool:
            return getattr(ctx, "is_cancelled", lambda: False)()

        status, task = await client.send_and_observe(
            prompt=prompt,
            task_id=task_id,
            is_cancelled=is_cancelled,
        )

        match status:
            case TaskStatus.COMPLETED:
                text = extract_text(task) or "Task completed"
                return f"[COMPLETED] {text}"
            case TaskStatus.INPUT_REQUIRED:
                question = extract_question(task)
                return f"[INPUT_REQUIRED:task_id={task['id']}] {question}"
            case TaskStatus.FAILED:
                msg = task["status"].get("message") if task else "Unknown error"
                return f"[FAILED] {msg}"
            case TaskStatus.CANCELLED:
                return "[CANCELLED] Task was cancelled"
            case TaskStatus.TIMEOUT:
                return "[TIMEOUT] Task timed out"

    delegate.__name__ = tool_name
    delegate.__doc__ = f"Delegate to {card['name']}: {card.get('description', '')}"

    return Tool(delegate)


def build_coordinator_prompt(clients: list[A2AClientExtended]) -> str:
    """Build a system prompt section describing available A2A agents."""
    sections = []
    for client in clients:
        card = asyncio.get_event_loop().run_until_complete(client.get_agent_card())
        sections.append(card_to_prompt(card))

    header = """You coordinate tasks between specialized agents.

When you see [INPUT_REQUIRED:task_id=...], ask the user for the required information and call the tool again with the same task_id to continue.

Available agents:
"""
    return header + "\n\n".join(sections)

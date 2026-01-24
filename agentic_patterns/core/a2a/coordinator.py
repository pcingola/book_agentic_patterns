"""Factory for creating coordinator agents that delegate to A2A agents."""

from collections.abc import Callable

from pydantic_ai import Agent, Tool

from agentic_patterns.core.a2a.client import A2AClientExtended
from agentic_patterns.core.a2a.config import A2AClientConfig
from agentic_patterns.core.a2a.tool import build_coordinator_prompt, create_a2a_tool
from agentic_patterns.core.agents import get_agent


async def create_coordinator(
    clients: list[A2AClientExtended] | list[A2AClientConfig],
    system_prompt: str | None = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> Agent:
    """Create a coordinator agent that delegates to remote A2A agents.

    Args:
        clients: List of A2A clients or client configs
        system_prompt: Optional additional system prompt (appended to auto-generated prompt)
        is_cancelled: Optional callback to check if operations should be cancelled

    Returns:
        PydanticAI Agent configured with tools for each remote agent
    """
    # Convert configs to clients if needed
    actual_clients: list[A2AClientExtended] = []
    for c in clients:
        if isinstance(c, A2AClientConfig):
            actual_clients.append(A2AClientExtended(c))
        else:
            actual_clients.append(c)

    # Fetch all agent cards
    cards: list[dict] = []
    for client in actual_clients:
        card = await client.get_agent_card()
        cards.append(card)

    # Create tools for each agent
    tools: list[Tool] = []
    for client, card in zip(actual_clients, cards):
        tool = create_a2a_tool(client, card, is_cancelled=is_cancelled)
        tools.append(tool)

    # Build system prompt
    base_prompt = build_coordinator_prompt(cards)
    if system_prompt:
        full_prompt = f"{base_prompt}\n\n{system_prompt}"
    else:
        full_prompt = base_prompt

    return get_agent(system_prompt=full_prompt, tools=tools)

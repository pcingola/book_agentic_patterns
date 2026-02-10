"""
AG-UI application factory and utilities.

Provides helpers for creating AG-UI applications using the core agent infrastructure.
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.ui import StateDeps
from pydantic_ai.ui.ag_ui.app import AGUIApp

from agentic_patterns.core.agents import get_agent


def create_agui_app(
    *,
    config_name: str = "default",
    config_path: Path | str | None = None,
    instructions: str | None = None,
    tools: list | None = None,
    state_type: type[BaseModel] | None = None,
    initial_state: BaseModel | None = None,
    **agent_kwargs: Any,
) -> AGUIApp:
    """
    Create an AG-UI application using the core agent configuration.

    Args:
        config_name: Name of model configuration from config.yaml.
        config_path: Path to config.yaml. If None, uses default location.
        instructions: System instructions for the agent.
        tools: List of tool functions to register.
        state_type: Pydantic model class for shared state. If provided, agent uses StateDeps.
        initial_state: Initial state instance. Required if state_type is provided.
        **agent_kwargs: Additional arguments passed to get_agent.

    Returns:
        Configured AGUIApp instance.
    """
    if instructions:
        agent_kwargs["instructions"] = instructions

    if tools:
        agent_kwargs["tools"] = tools

    if state_type:
        agent_kwargs["deps_type"] = StateDeps[state_type]

    agent = get_agent(config_name=config_name, config_path=config_path, **agent_kwargs)

    if state_type and initial_state:
        return AGUIApp(agent, deps=StateDeps(initial_state))

    return AGUIApp(agent)


def create_agui_app_from_agent(
    agent: Agent,
    state: BaseModel | None = None,
) -> AGUIApp:
    """
    Create an AG-UI application from an existing agent.

    Args:
        agent: Pre-configured PydanticAI agent.
        state: Initial state instance for agents with StateDeps.

    Returns:
        Configured AGUIApp instance.
    """
    if state:
        return AGUIApp(agent, deps=StateDeps(state))
    return AGUIApp(agent)

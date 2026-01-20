"""
Core agent implementation for AI agents.
"""

import logging
from pathlib import Path
from typing import Sequence

from pydantic_ai import AgentRun, AgentRunResult, ModelMessage, RequestUsage
import rich
from fastmcp import Context
from pydantic_ai.agent import Agent
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import UsageLimits

from agentic_patterns.core.agents.models import _get_model_from_config, _get_config
from agentic_patterns.core.agents.utils import get_usage, has_tool_calls, nodes_to_message_history


logger = logging.getLogger(__name__)


def get_agent(
    model=None,
    *,
    config_name: str = "default",
    config_path: Path | str | None = None,
    model_settings=None,
    http_client=None,
    history_compactor=None,
    **kwargs
) -> Agent:
    """
    Get a PydanticAI agent.

    Args:
        model: Pre-configured model instance. If None, will be created from config_name.
        config_name: Name of configuration from config.yaml (default: "default").
        config_path: Path to config.yaml file. If None, uses MAIN_PROJECT_DIR/config.yaml.
        model_settings: Model settings. If None, uses timeout from config.
        http_client: HTTP client for API calls.
        history_compactor: Optional HistoryCompactor instance for automatic history compaction.
        **kwargs: Additional arguments passed to Agent (instructions, system_prompt, tools, toolsets,
                  output_type, deps_type, retries, history_processor, etc.).

    Returns:
        Configured Agent instance.
    """
    config = _get_config(config_name, config_path)

    if model is None:
        model = _get_model_from_config(config, http_client=http_client)

    if model_settings is None:
        settings_kwargs = {'timeout': config.timeout}
        if config.parallel_tool_calls is not None:
            settings_kwargs['parallel_tool_calls'] = config.parallel_tool_calls
        model_settings = ModelSettings(**settings_kwargs)

    # If history_compactor provided and no history_processor in kwargs, create one
    if history_compactor is not None and 'history_processor' not in kwargs:
        kwargs['history_processor'] = history_compactor.create_history_processor()

    agent = Agent(
        model=model,
        model_settings=model_settings,
        instrument=True,
        **kwargs
    )
    return agent


async def run_agent(
        # noqa: PLR0913, pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
        agent: Agent,
        prompt: str | list[str],
        message_history: Sequence[ModelMessage] | None = None,
        usage_limits: UsageLimits | None = None,
        verbose: bool = False,
        catch_exceptions: bool = False,
        ctx: Context | None = None,
    ) -> tuple[AgentRun | None, list[ModelMessage]]:
    """
    Run the agent with the given prompt and log the execution details.
    Args:
        agent (Agent): The PydanticAI agent to run.
        prompt (str | list[str]): The input prompt(s) for the agent.
        usage_limits (UsageLimits | None): Optional usage limits for the agent.
        verbose (bool): If True, enables verbose logging.
        catch_exceptions (bool): If True, catches exceptions during agent run.
        parent_logger (ObjectLogger | None): Optional parent logger for hierarchical logging.
        ctx (Context | None): Optional FastMCP context for logging messages to the MCP client.
    Returns:
        AgentRun, list[ModelMessage]: The agent run object and the list of model messages.
    """
    # Results
    agent_run, nodes = None, []
    try:
        async with agent.iter(prompt, usage_limits=usage_limits, message_history=message_history) as agent_run:
            # Run the agent
            async for node in agent_run:
                nodes.append(node)
                # If we are executing in an MCP server, send debug messages to the MCP client (for easier debugging)
                if ctx:
                    await ctx.debug(f"MCP server {ctx.fastmcp.name}: {node}")
                if verbose:
                    rich.print(f"[green]Agent step:[/green] {node}")
    except Exception as e:  # pylint: disable=broad-exception-caught
        if verbose:
            rich.print(f"[red]Error running agent:[/red] {e}")
        if not catch_exceptions:
            raise e
    return agent_run, nodes

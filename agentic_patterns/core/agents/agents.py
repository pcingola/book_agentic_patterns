"""
Core agent implementation providing model selection and configuration for AI agents.
"""

import logging
from types import NoneType
from typing import Any, Sequence

from pydantic_ai import AgentRunResult, ModelMessage, RequestUsage, ToolCallPart
import rich
from fastmcp import Context
from openai import AsyncAzureOpenAI
from pydantic_ai.agent import Agent
from pydantic_ai.models.bedrock import BedrockConverseModel, BedrockModelSettings
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.bedrock import BedrockProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import UsageLimits


from agentic_patterns.core.config.config import AWS_PROFILE, AWS_REGION, AZURE_MODEL_NAME, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_ENDPOINT, BEDROCK_CLAUDE_SONNET_1M_TOKENS, BEDROCK_MODEL_NAME, MODEL_FAMILY, MODEL_TIMEOUT, OLLAMA_MODEL_NAME, OLLAMA_URL, OPENAI_API_KEY, OPENAI_MODEL_NAME, OPENROUTER_API_KEY, OPENROUTER_API_URL, OPENROUTER_MODEL_NAME


logger = logging.getLogger(__name__)


def _get_model_bedrock(model_name=BEDROCK_MODEL_NAME, aws_region=AWS_REGION):
    assert model_name, "BEDROCK_MODEL_NAME is not set"
    assert aws_region, "AWS_REGION is not set"

    bedrock_additional_model_requests_fields = {}
    if BEDROCK_CLAUDE_SONNET_1M_TOKENS:
        assert "anthropic.claude-sonnet-4" in model_name, (
            "1M tokens context window is only supported for Claude Sonnet 4 and 4.5 models"
        )
        bedrock_additional_model_requests_fields["anthropic_beta"] = ["context-1m-2025-08-07"]

    model_settings = (
        BedrockModelSettings(bedrock_additional_model_requests_fields=bedrock_additional_model_requests_fields)
        if bedrock_additional_model_requests_fields
        else None
    )

    if AWS_PROFILE is not None:
        return BedrockConverseModel(model_name=model_name, settings=model_settings)

    provider = BedrockProvider(region_name=aws_region)
    return BedrockConverseModel(model_name=model_name, provider=provider, settings=model_settings)


def _get_model_ollama(model_name=OLLAMA_MODEL_NAME, ollama_url=OLLAMA_URL, http_client=None):
    assert ollama_url, "OLLAMA_URL is not set"
    assert model_name, "Model name is not set"
    provider = OpenAIProvider(base_url=ollama_url, http_client=http_client)
    return OpenAIChatModel(model_name=model_name, provider=provider)


def _get_model_openai(model_name=OPENAI_MODEL_NAME, openai_api_key=OPENAI_API_KEY, http_client=None):
    assert openai_api_key, "OPENAI_API_KEY is not set"
    assert model_name, "Model name is not set"
    provider = OpenAIProvider(api_key=openai_api_key, http_client=http_client)
    return OpenAIChatModel(model_name=model_name, provider=provider)


def _get_model_openai_azure(
    model_name=AZURE_MODEL_NAME,
    azure_openai_api_key=AZURE_OPENAI_API_KEY,
    azure_openai_endpoint=AZURE_OPENAI_ENDPOINT,
    azure_openai_api_version=AZURE_OPENAI_API_VERSION,
    http_client=None,
):
    assert azure_openai_endpoint, "AZURE_OPENAI_ENDPOINT is not set"
    assert azure_openai_api_key, "AZURE_OPENAI_API_KEY is not set"
    assert azure_openai_api_version, "AZURE_OPENAI_API_VERSION is not set"
    assert model_name, "Model name is not set"
    client = AsyncAzureOpenAI(
        azure_endpoint=azure_openai_endpoint,
        api_version=azure_openai_api_version,
        api_key=azure_openai_api_key,
        http_client=http_client,
    )
    return OpenAIChatModel(model_name=model_name, provider=OpenAIProvider(openai_client=client))


def _get_model_open_router(
    model_name=OPENROUTER_MODEL_NAME,
    openrouter_api_url=OPENROUTER_API_URL,
    openrouter_api_key=OPENROUTER_API_KEY,
    http_client=None,
):
    assert openrouter_api_url, "OPENROUTER_API_URL is not set"
    assert openrouter_api_key, "OPENROUTER_API_KEY is not set"
    assert model_name, "Model name is not set, missing 'OPENROUTER_MODEL_NAME' environment variable?"
    provider = OpenAIProvider(base_url=openrouter_api_url, api_key=openrouter_api_key, http_client=http_client)
    return OpenAIChatModel(model_name, provider=provider)


def get_model(model_family=MODEL_FAMILY, model_name=None, http_client=None, **kwargs):
    """Create and return appropriate model instance based on specified family and name."""
    assert model_family is not None and model_family != "", f"Model family '{model_family}' is not set"
    match model_family:
        case "azure":
            return _get_model_openai_azure(model_name=model_name or AZURE_MODEL_NAME, http_client=http_client, **kwargs)
        case "bedrock":
            return _get_model_bedrock(model_name=model_name or BEDROCK_MODEL_NAME, **kwargs)
        case "ollama":
            return _get_model_ollama(model_name=model_name or OLLAMA_MODEL_NAME, http_client=http_client, **kwargs)
        case "openai":
            return _get_model_openai(model_name=model_name or OPENAI_MODEL_NAME, http_client=http_client, **kwargs)
        case "openrouter":
            return _get_model_open_router(
                model_name=model_name or OPENROUTER_MODEL_NAME, http_client=http_client, **kwargs
            )
        case _:
            raise ValueError(f"Model family '{model_family}' not supported")


def get_agent(  # noqa: PLR0913, pylint: disable=too-many-arguments,too-many-positional-arguments
    model=None,
    *,
    instructions=None,
    system_prompt=(),
    tools=(),
    toolsets=(),
    model_settings=None,
    output_type: Any = str,
    deps_type=NoneType,
    http_client=None,
    retries: int = 1,
) -> Agent:
    """Get a PydanticAI agent"""
    if model_settings is None:
        model_settings = ModelSettings(timeout=MODEL_TIMEOUT, parallel_tool_calls=True)
    if model is None:
        model = get_model(http_client=http_client,)
    agent = Agent(
        model=model,
        output_type=output_type,
        instructions=instructions,
        system_prompt=system_prompt,
        deps_type=deps_type,
        model_settings=model_settings,
        tools=tools,
        toolsets=toolsets,
        instrument=True,
        retries=retries,
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
        show_usage: bool = False,
        ctx: Context | None = None,
    ) -> AgentRunResult | None:
    """
    Run the agent with the given prompt and log the execution details.
    Args:
        agent (Agent): The PydanticAI agent to run.
        prompt (str | list[str]): The input prompt(s) for the agent.
        usage_limits (UsageLimits | None): Optional usage limits for the agent.
        verbose (bool): If True, enables verbose logging.
        debug (bool): If True, enables debug logging.
        parent_logger (ObjectLogger | None): Optional parent logger for hierarchical logging.
        ctx (Context | None): Optional FastMCP context for logging messages to the MCP client.
    Returns:
        AgentRunResult | None: The result of the agent run, or None if an exception occurred and was caught.
    """
    # Results
    request_usage = RequestUsage()
    nodes, result = [], None
    try:
        async with agent.iter(prompt, usage_limits=usage_limits, message_history=message_history) as agent_run:
            # Run the agent
            async for node in agent_run:
                if ctx:
                    # If we are executing in an MCP server, send info messages to the client for better debugging
                    server_name = ctx.fastmcp.name
                    await ctx.info(f"MCP server {server_name}: {node}")
                nodes.append(node)
                if show_usage:
                    usage = get_usage(node)
                    if usage:
                        request_usage.incr(usage)
                        logger.info("Usage: %s, Total: %s", usage, request_usage)
            result = agent_run.result
    except Exception as e:  # pylint: disable=broad-exception-caught
        if verbose:
            rich.print(f"[red]Error running agent:[/red] {e}")
        if not catch_exceptions:
            raise e
    return result


def has_tool_calls(msg: ModelMessage) -> bool:
    """Check if the message is a ToolCallPart."""
    return any(isinstance(part, ToolCallPart) for part in msg.parts)


def nodes_to_message_history(nodes: list, remove_last_call_tool: bool = True) -> Sequence[ModelMessage]:
    """Convert a list of nodes to a History object with a single Conversation."""
    messages = []
    for n in nodes:
        if hasattr(n, "request"):
            messages.append(n.request)
        elif hasattr(n, "response"):
            messages.append(n.response)
        elif hasattr(n, "model_response"):
            messages.append(n.model_response)
    # Optionally remove the last CallToolsNode
    if remove_last_call_tool and len(messages) >= 2 and has_tool_calls(messages[-1]):  # noqa: PLR2004
        # Remove the last CallToolsNode if present
        messages = messages[:-1]
    return messages


def get_usage(node):
    """Convert a list of nodes to a History object with a single Conversation."""
    if node and hasattr(node, "usage"):
        return node.usage
    response = None
    if hasattr(node, "response"):
        response = node.response
    elif hasattr(node, "model_response"):
        response = node.model_response
    if response and hasattr(response, "usage"):
        return response.usage
    return None

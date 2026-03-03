"""
Model creation and configuration for AI agents.
"""

import logging
import os
from pathlib import Path

import boto3
from botocore.config import Config
from openai import AsyncAzureOpenAI, AsyncOpenAI
from pydantic_ai.models.bedrock import BedrockConverseModel, BedrockModelSettings
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.bedrock import BedrockProvider
from pydantic_ai.providers.openai import OpenAIProvider

from agentic_patterns.core.agents.config import (
    AgentConfig,
    AIGatewayConfig,
    AzureConfig,
    BedrockConfig,
    GatewayProvider,
    Models,
    OllamaConfig,
    OpenAIConfig,
    OpenRouterConfig,
    load_models,
)
from agentic_patterns.core.config.config import MAIN_PROJECT_DIR

logger = logging.getLogger(__name__)


def _load_models(config_path: Path | str | None = None) -> Models:
    """Load model configurations from YAML file."""
    if config_path is None:
        config_path = MAIN_PROJECT_DIR / "config.yaml"

    return load_models(config_path)


def _get_config(
    config_name: str = "default", config_path: Path | str | None = None
) -> AgentConfig:
    """Get model configuration by name."""
    models = _load_models(config_path)
    return models.get(config_name)


def _get_model_bedrock(config: BedrockConfig):
    bedrock_additional_model_requests_fields = {}
    if config.claude_sonnet_1m_tokens:
        assert "anthropic.claude-sonnet-4" in config.model_name, (
            "1M tokens context window is only supported for Claude Sonnet 4 and 4.5 models"
        )
        bedrock_additional_model_requests_fields["anthropic_beta"] = [
            "context-1m-2025-08-07"
        ]

    model_settings = (
        BedrockModelSettings(
            bedrock_additional_model_requests_fields=bedrock_additional_model_requests_fields
        )
        if bedrock_additional_model_requests_fields
        else None
    )

    if config.aws_profile is not None:
        return BedrockConverseModel(
            model_name=config.model_name, settings=model_settings
        )

    provider = BedrockProvider(region_name=config.aws_region)
    return BedrockConverseModel(
        model_name=config.model_name, provider=provider, settings=model_settings
    )


def _get_model_ollama(config: OllamaConfig, http_client=None):
    provider = OpenAIProvider(base_url=config.url, http_client=http_client)
    return OpenAIChatModel(model_name=config.model_name, provider=provider)


def _get_model_openai(config: OpenAIConfig, http_client=None):
    provider = OpenAIProvider(api_key=config.api_key, http_client=http_client)
    return OpenAIChatModel(model_name=config.model_name, provider=provider)


def _get_model_openai_azure(config: AzureConfig, http_client=None):
    client = AsyncAzureOpenAI(
        azure_endpoint=config.endpoint,
        api_version=config.api_version,
        api_key=config.api_key,
        http_client=http_client,
    )
    return OpenAIChatModel(
        model_name=config.model_name, provider=OpenAIProvider(openai_client=client)
    )


def _get_model_open_router(config: OpenRouterConfig, http_client=None):
    provider = OpenAIProvider(
        base_url=config.api_url, api_key=config.api_key, http_client=http_client
    )
    return OpenAIChatModel(config.model_name, provider=provider)


def _infer_gateway_provider(model_name: str) -> GatewayProvider:
    """Infer the gateway backend provider from model name patterns.

    - Bedrock: anthropic.*, amazon.*, meta.*, cohere.*, us.*, google.gemma-* prefixes
    - Azure: gpt-*, o1/o3/o4-*, deepseek-*, grok-*, text-embedding-* models
    - Vertex AI: gemini-*, google/* models
    """
    model_lower = model_name.lower()

    bedrock_prefixes = (
        "anthropic.",
        "amazon.",
        "meta.",
        "cohere.",
        "us.",
        "google.gemma",
    )
    if model_lower.startswith(bedrock_prefixes):
        return GatewayProvider.BEDROCK

    azure_prefixes = ("gpt-", "o1", "o3", "o4-", "deepseek", "grok-", "text-embedding-")
    if model_lower.startswith(azure_prefixes):
        return GatewayProvider.AZURE

    if model_lower.startswith(("gemini-", "google/")):
        return GatewayProvider.VERTEX_OPENAI

    raise ValueError(
        f"Cannot infer gateway_provider from model '{model_name}'. "
        f"Set gateway_provider explicitly ({' | '.join(p.value for p in GatewayProvider)})"
    )


def _get_model_gateway_azure(config: AIGatewayConfig):
    client = AsyncAzureOpenAI(
        azure_endpoint=f"{config.gateway_url}/azure-openai",
        api_version="2025-01-01-preview",
        api_key=config.gateway_key,
    )
    return OpenAIChatModel(
        config.model_name, provider=OpenAIProvider(openai_client=client)
    )


def _get_model_gateway_bedrock(config: AIGatewayConfig):
    """Note: Sets AWS_BEARER_TOKEN_BEDROCK env var which is process-global."""
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = config.gateway_key
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name="us-east-1",
        endpoint_url=f"{config.gateway_url}/bedrock",
        aws_access_key_id="",
        aws_secret_access_key="",
        config=Config(retries={"max_attempts": 0}),
    )
    return BedrockConverseModel(
        model_name=config.model_name,
        provider=BedrockProvider(bedrock_client=bedrock_client),
    )


def _get_model_gateway_vertex_openai(config: AIGatewayConfig):
    model_name = config.model_name
    if model_name.lower().startswith("gemini-"):
        model_name = f"google/{model_name}"
        logger.debug(
            "Auto-prefixed model name to '%s' for OpenAI-compatible endpoint",
            model_name,
        )
    client = AsyncOpenAI(
        base_url=f"{config.gateway_url}/vertex-ai-openai/v1",
        api_key=config.gateway_key,
    )
    return OpenAIChatModel(model_name, provider=OpenAIProvider(openai_client=client))


def _get_model_ai_gateway(config: AIGatewayConfig):
    provider = config.gateway_provider or _infer_gateway_provider(config.model_name)
    logger.info(
        "AI Gateway: model='%s', provider='%s'", config.model_name, provider.value
    )

    match provider:
        case GatewayProvider.AZURE:
            return _get_model_gateway_azure(config)
        case GatewayProvider.BEDROCK:
            return _get_model_gateway_bedrock(config)
        case GatewayProvider.VERTEX_OPENAI:
            return _get_model_gateway_vertex_openai(config)


def _get_model_from_config(config: AgentConfig, http_client=None):
    """Create model from configuration object."""
    match config:
        case AIGatewayConfig():
            return _get_model_ai_gateway(config)
        case AzureConfig():
            return _get_model_openai_azure(config, http_client=http_client)
        case BedrockConfig():
            return _get_model_bedrock(config)
        case OllamaConfig():
            return _get_model_ollama(config, http_client=http_client)
        case OpenAIConfig():
            return _get_model_openai(config, http_client=http_client)
        case OpenRouterConfig():
            return _get_model_open_router(config, http_client=http_client)
        case _:
            raise ValueError(f"Unsupported config type: {type(config)}")


def get_model(
    config_name: str = "default",
    config_path: Path | str | None = None,
    http_client=None,
):
    """
    Create and return appropriate model instance from config.yaml.

    Args:
        config_name: Name of configuration from config.yaml (default: "default").
        config_path: Path to config.yaml file. If None, uses MAIN_PROJECT_DIR/config.yaml.
        http_client: HTTP client for API calls.

    Returns:
        Model instance.
    """
    config = _get_config(config_name, config_path)
    return _get_model_from_config(config, http_client=http_client)

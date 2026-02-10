"""
Model creation and configuration for AI agents.
"""

from pathlib import Path

from openai import AsyncAzureOpenAI
from pydantic_ai.models.bedrock import BedrockConverseModel, BedrockModelSettings
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.bedrock import BedrockProvider
from pydantic_ai.providers.openai import OpenAIProvider

from agentic_patterns.core.agents.config import (
    AgentConfig,
    Models,
    AzureConfig,
    BedrockConfig,
    OllamaConfig,
    OpenAIConfig,
    OpenRouterConfig,
    load_models,
)
from agentic_patterns.core.config.config import MAIN_PROJECT_DIR


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


def _get_model_from_config(config: AgentConfig, http_client=None):
    """Create model from configuration object."""
    match config:
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

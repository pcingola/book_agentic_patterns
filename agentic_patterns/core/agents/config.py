"""
Pydantic models for agent configurations.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class AzureConfig(BaseModel):
    """Configuration for Azure OpenAI models."""
    model_family: str = Field(default="azure")
    model_name: str
    api_key: str
    endpoint: str
    api_version: str
    timeout: int = Field(default=120)


class BedrockConfig(BaseModel):
    """Configuration for AWS Bedrock models."""
    model_family: str = Field(default="bedrock")
    model_name: str
    aws_region: str = Field(default="us-east-1")
    aws_profile: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None
    claude_sonnet_1m_tokens: bool = Field(default=False)
    timeout: int = Field(default=120)


class OllamaConfig(BaseModel):
    """Configuration for Ollama models."""
    model_family: str = Field(default="ollama")
    model_name: str
    url: str
    timeout: int = Field(default=120)


class OpenAIConfig(BaseModel):
    """Configuration for OpenAI models."""
    model_family: str = Field(default="openai")
    model_name: str
    api_key: str
    timeout: int = Field(default=120)


class OpenRouterConfig(BaseModel):
    """Configuration for OpenRouter models."""
    model_family: str = Field(default="openrouter")
    model_name: str
    api_key: str
    api_url: str = Field(default="https://openrouter.ai/api/v1")
    timeout: int = Field(default=120)


AgentConfig = AzureConfig | BedrockConfig | OllamaConfig | OpenAIConfig | OpenRouterConfig


class Models(BaseModel):
    """Container for multiple model configurations."""
    models: dict[str, AgentConfig]

    def get(self, name: str = "default") -> AgentConfig:
        """Get configuration by name."""
        if name not in self.models:
            raise ValueError(f"Model configuration '{name}' not found. Available: {list(self.models.keys())}")
        return self.models[name]


def load_models(config_path: Path | str) -> Models:
    """Load model configurations from YAML file."""
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if not data or "models" not in data:
        raise ValueError("Configuration file must contain 'models' key")

    configs: dict[str, AgentConfig] = {}
    for name, config_data in data["models"].items():
        model_family = config_data.get("model_family")

        match model_family:
            case "azure":
                configs[name] = AzureConfig(**config_data)
            case "bedrock":
                configs[name] = BedrockConfig(**config_data)
            case "ollama":
                configs[name] = OllamaConfig(**config_data)
            case "openai":
                configs[name] = OpenAIConfig(**config_data)
            case "openrouter":
                configs[name] = OpenRouterConfig(**config_data)
            case _:
                raise ValueError(f"Unsupported model_family: {model_family}")

    return Models(models=configs)

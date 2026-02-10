"""Pydantic models for embedding and vector database configurations."""

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class OpenAIEmbeddingConfig(BaseModel):
    """Configuration for OpenAI embeddings."""

    provider: str = Field(default="openai")
    model_name: str
    api_key: str | None = None
    dimensions: int | None = None


class OllamaEmbeddingConfig(BaseModel):
    """Configuration for Ollama embeddings."""

    provider: str = Field(default="ollama")
    model_name: str
    url: str = Field(default="http://localhost:11434")


class SentenceTransformersEmbeddingConfig(BaseModel):
    """Configuration for Sentence Transformers embeddings."""

    provider: str = Field(default="sentence_transformers")
    model_name: str
    device: str = Field(default="cpu")


class OpenRouterEmbeddingConfig(BaseModel):
    """Configuration for OpenRouter embeddings (OpenAI-compatible API)."""

    provider: str = Field(default="openrouter")
    model_name: str
    api_key: str | None = None
    api_url: str = Field(default="https://openrouter.ai/api/v1")
    dimensions: int | None = None


EmbeddingConfig = (
    OpenAIEmbeddingConfig
    | OllamaEmbeddingConfig
    | SentenceTransformersEmbeddingConfig
    | OpenRouterEmbeddingConfig
)


class ChromaVectorDBConfig(BaseModel):
    """Configuration for Chroma vector database."""

    backend: str = Field(default="chroma")
    persist_directory: str


class PgVectorDBConfig(BaseModel):
    """Configuration for PostgreSQL + pgvector."""

    backend: str = Field(default="pgvector")
    connection_string: str


VectorDBConfig = ChromaVectorDBConfig | PgVectorDBConfig


class VectorDBSettings(BaseModel):
    """Container for embedding and vector database configurations."""

    embeddings: dict[str, EmbeddingConfig]
    vectordb: dict[str, VectorDBConfig]

    def get_embedding(self, name: str = "default") -> EmbeddingConfig:
        if name not in self.embeddings:
            raise ValueError(
                f"Embedding config '{name}' not found. Available: {list(self.embeddings.keys())}"
            )
        return self.embeddings[name]

    def get_vectordb(self, name: str = "default") -> VectorDBConfig:
        if name not in self.vectordb:
            raise ValueError(
                f"VectorDB config '{name}' not found. Available: {list(self.vectordb.keys())}"
            )
        return self.vectordb[name]


def _expand_env_vars(value: str) -> str:
    """Expand ${VAR} patterns in string values."""
    pattern = r"\$\{(\w+)\}"

    def replace(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return re.sub(pattern, replace, value)


def _expand_config_vars(config: dict) -> dict:
    """Recursively expand environment variables in config dict."""
    result = {}
    for key, value in config.items():
        if isinstance(value, str):
            result[key] = _expand_env_vars(value)
        elif isinstance(value, dict):
            result[key] = _expand_config_vars(value)
        else:
            result[key] = value
    return result


def load_vectordb_settings(config_path: Path | str) -> VectorDBSettings:
    """Load embedding and vector database configurations from YAML file."""
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    embeddings: dict[str, EmbeddingConfig] = {}
    vectordb: dict[str, VectorDBConfig] = {}

    if "embeddings" in data:
        for name, config_data in data["embeddings"].items():
            config_data = _expand_config_vars(config_data)
            provider = config_data.get("provider")
            match provider:
                case "openai":
                    embeddings[name] = OpenAIEmbeddingConfig(**config_data)
                case "ollama":
                    embeddings[name] = OllamaEmbeddingConfig(**config_data)
                case "sentence_transformers":
                    embeddings[name] = SentenceTransformersEmbeddingConfig(
                        **config_data
                    )
                case "openrouter":
                    embeddings[name] = OpenRouterEmbeddingConfig(**config_data)
                case _:
                    raise ValueError(f"Unsupported embedding provider: {provider}")

    if "vectordb" in data:
        for name, config_data in data["vectordb"].items():
            config_data = _expand_config_vars(config_data)
            backend = config_data.get("backend")
            match backend:
                case "chroma":
                    vectordb[name] = ChromaVectorDBConfig(**config_data)
                case "pgvector":
                    vectordb[name] = PgVectorDBConfig(**config_data)
                case _:
                    raise ValueError(f"Unsupported vectordb backend: {backend}")

    return VectorDBSettings(embeddings=embeddings, vectordb=vectordb)

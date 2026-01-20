"""Embeddings wrapper using pydantic-ai."""

from pathlib import Path

from pydantic_ai import Embedder
from pydantic_ai.embeddings import EmbeddingSettings

from agentic_patterns.core.vectordb.config import (
    EmbeddingConfig,
    OllamaEmbeddingConfig,
    OpenAIEmbeddingConfig,
    OpenRouterEmbeddingConfig,
    SentenceTransformersEmbeddingConfig,
    load_vectordb_settings,
)

_embedders: dict[str, Embedder] = {}


def get_embedder(config: EmbeddingConfig | str | None = None, config_path: Path | str | None = None) -> Embedder:
    """Get an embedder instance from config. Uses singleton pattern."""
    if isinstance(config, str):
        if config_path is None:
            from agentic_patterns.core.config.config import MAIN_PROJECT_DIR
            config_path = MAIN_PROJECT_DIR / "config.yaml"
        settings = load_vectordb_settings(config_path)
        config = settings.get_embedding(config)

    if config is None:
        if config_path is None:
            from agentic_patterns.core.config.config import MAIN_PROJECT_DIR
            config_path = MAIN_PROJECT_DIR / "config.yaml"
        settings = load_vectordb_settings(config_path)
        config = settings.get_embedding("default")

    cache_key = f"{config.provider}:{config.model_name}"
    if cache_key in _embedders:
        return _embedders[cache_key]

    embedder = _create_embedder(config)
    _embedders[cache_key] = embedder
    return embedder


def _create_embedder(config: EmbeddingConfig) -> Embedder:
    """Create an embedder instance from config."""
    match config:
        case OpenAIEmbeddingConfig():
            model_str = f"openai:{config.model_name}"
            settings = EmbeddingSettings(dimensions=config.dimensions) if config.dimensions else None
            return Embedder(model_str, settings=settings)
        case OllamaEmbeddingConfig():
            model_str = f"ollama:{config.model_name}"
            return Embedder(model_str)
        case SentenceTransformersEmbeddingConfig():
            from pydantic_ai.embeddings.sentence_transformers import SentenceTransformersEmbeddingSettings
            model_str = f"sentence-transformers:{config.model_name}"
            settings = SentenceTransformersEmbeddingSettings(sentence_transformers_device=config.device)
            return Embedder(model_str, settings=settings)
        case OpenRouterEmbeddingConfig():
            from openai import AsyncOpenAI
            from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
            from pydantic_ai.providers.openai import OpenAIProvider
            client = AsyncOpenAI(base_url=config.api_url, api_key=config.api_key)
            model = OpenAIEmbeddingModel(config.model_name, provider=OpenAIProvider(openai_client=client))
            settings = EmbeddingSettings(dimensions=config.dimensions) if config.dimensions else None
            return Embedder(model, settings=settings)
        case _:
            raise ValueError(f"Unsupported embedding config type: {type(config)}")


async def embed_text(text: str, embedder: Embedder | None = None) -> list[float]:
    """Embed a single text string."""
    if embedder is None:
        embedder = get_embedder()
    result = await embedder.embed_query(text)
    return list(result.embeddings[0])


async def embed_texts(texts: list[str], embedder: Embedder | None = None) -> list[list[float]]:
    """Embed multiple text strings."""
    if embedder is None:
        embedder = get_embedder()
    result = await embedder.embed_documents(texts)
    return [list(emb) for emb in result.embeddings]

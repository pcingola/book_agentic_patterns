"""Vocabulary registry: loads config and routes to the appropriate strategy backend."""

import logging
from pathlib import Path

import yaml

from agentic_patterns.core.connectors.vocabulary.config import VOCABULARIES_YAML_PATH, VOCABULARY_CACHE_DIR
from agentic_patterns.core.connectors.vocabulary.models import VocabularyConfig, VocabularyInfo
from agentic_patterns.core.connectors.vocabulary.strategy_enum import StrategyEnum
from agentic_patterns.core.connectors.vocabulary.strategy_rag import StrategyRag
from agentic_patterns.core.connectors.vocabulary.strategy_tree import StrategyTree

logger = logging.getLogger(__name__)

Strategy = StrategyEnum | StrategyTree | StrategyRag

_registry: dict[str, Strategy] = {}
_configs: dict[str, VocabularyConfig] = {}


def get_configs() -> dict[str, VocabularyConfig]:
    """Return loaded configs (load from YAML if not yet loaded)."""
    if not _configs:
        _load_configs()
    return _configs


def get_vocabulary(name: str) -> Strategy:
    """Get a loaded vocabulary backend by name. Lazy-loads from config if not yet registered."""
    if name not in _registry:
        configs = get_configs()
        if name in configs:
            from agentic_patterns.core.connectors.vocabulary.loader import load_vocabulary
            load_vocabulary(configs[name], base_dir=VOCABULARY_CACHE_DIR)
        else:
            raise KeyError(f"Vocabulary '{name}' not registered. Available: {list(_registry.keys()) + list(configs.keys())}")
    return _registry[name]


def list_vocabularies() -> list[VocabularyInfo]:
    """Return info for all registered vocabularies."""
    return [backend.info() for backend in _registry.values()]


def load_all(config_path: Path | None = None, base_dir: Path | None = None) -> None:
    """Load all vocabularies defined in the YAML config."""
    from agentic_patterns.core.connectors.vocabulary.loader import load_vocabulary
    _load_configs(config_path)
    for config in _configs.values():
        if config.name not in _registry:
            try:
                load_vocabulary(config, base_dir or VOCABULARY_CACHE_DIR)
            except Exception:
                logger.exception("Failed to load vocabulary: %s", config.name)


def register_vocabulary(name: str, backend: Strategy) -> None:
    """Register a vocabulary backend directly (useful for programmatic/toy setup)."""
    _registry[name] = backend


def reset() -> None:
    """Clear all registered vocabularies and configs."""
    _registry.clear()
    _configs.clear()


def _load_configs(config_path: Path | None = None) -> None:
    """Load vocabulary configurations from YAML."""
    path = config_path or VOCABULARIES_YAML_PATH
    if not path.exists():
        return
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    vocabs = data.get("vocabularies", {})
    for name, entry in vocabs.items():
        _configs[name] = VocabularyConfig(name=name, **entry)

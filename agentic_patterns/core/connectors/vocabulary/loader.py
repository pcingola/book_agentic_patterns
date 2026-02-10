"""VocabularyLoader: dispatches to format-specific parsers and populates strategy backends."""

import json
import logging
from pathlib import Path

from agentic_patterns.core.connectors.vocabulary.config import VOCABULARY_CACHE_DIR
from agentic_patterns.core.connectors.vocabulary.models import (
    SourceFormat,
    VocabularyConfig,
    VocabularyStrategy,
    VocabularyTerm,
)
from agentic_patterns.core.connectors.vocabulary.parser_obo import parse_obo
from agentic_patterns.core.connectors.vocabulary.parser_owl import parse_owl
from agentic_patterns.core.connectors.vocabulary.parser_rf2 import parse_rf2
from agentic_patterns.core.connectors.vocabulary.parser_tabular import (
    parse_csv,
    parse_gmt,
    parse_json_flat,
    parse_json_hierarchical,
    parse_mesh_xml,
)
from agentic_patterns.core.connectors.vocabulary.registry import (
    Strategy,
    register_vocabulary,
)
from agentic_patterns.core.connectors.vocabulary.strategy_enum import StrategyEnum
from agentic_patterns.core.connectors.vocabulary.strategy_rag import StrategyRag
from agentic_patterns.core.connectors.vocabulary.strategy_tree import StrategyTree

logger = logging.getLogger(__name__)


def load_vocabulary(config: VocabularyConfig, base_dir: Path | None = None) -> Strategy:
    """Load a vocabulary from its source file and register it.

    For enum/tree strategies, writes a processed JSON cache for fast reload.
    For RAG strategy, indexes terms into the vector DB.
    """
    source_path = _resolve_source(config, base_dir)
    cache_path = VOCABULARY_CACHE_DIR / f"{config.name}.json"

    # Try cache first for enum/tree
    if (
        config.strategy in (VocabularyStrategy.ENUM, VocabularyStrategy.TREE)
        and cache_path.exists()
        and cache_path.stat().st_mtime > source_path.stat().st_mtime
    ):
        logger.info("Loading %s from cache", config.name)
        terms = _load_cache(cache_path)
    else:
        logger.info("Parsing %s from %s", config.name, source_path)
        terms = _parse(config, source_path)
        if config.strategy in (VocabularyStrategy.ENUM, VocabularyStrategy.TREE):
            _save_cache(terms, cache_path)

    backend = _create_backend(config, terms)
    register_vocabulary(config.name, backend)
    return backend


def _create_backend(config: VocabularyConfig, terms: list[VocabularyTerm]) -> Strategy:
    """Instantiate the appropriate strategy backend and populate it."""
    match config.strategy:
        case VocabularyStrategy.ENUM:
            return StrategyEnum(config.name, terms)
        case VocabularyStrategy.TREE:
            return StrategyTree(config.name, terms)
        case VocabularyStrategy.RAG:
            backend = StrategyRag(
                config.name,
                collection=config.collection,
                embedding_config=config.embedding_config,
            )
            for term in terms:
                backend.add_term(term)
            return backend


def _guess_format(path: Path) -> SourceFormat:
    """Guess source format from file extension."""
    suffix = path.suffix.lower()
    match suffix:
        case ".obo":
            return SourceFormat.OBO
        case ".owl":
            return SourceFormat.OWL
        case ".json":
            return SourceFormat.JSON_FLAT
        case ".csv":
            return SourceFormat.CSV
        case ".tsv" | ".tab":
            return SourceFormat.TSV
        case ".xml":
            return SourceFormat.MESH_XML
        case ".gmt":
            return SourceFormat.GMT
        case _:
            raise ValueError(f"Cannot guess format for {path}")


def _load_cache(cache_path: Path) -> list[VocabularyTerm]:
    """Load terms from JSON cache."""
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    return [VocabularyTerm(**item) for item in data]


def _parse(config: VocabularyConfig, source_path: Path) -> list[VocabularyTerm]:
    """Parse source file using the appropriate parser."""
    fmt = config.source_format or _guess_format(source_path)
    opts = config.parser_options

    match fmt:
        case SourceFormat.OBO:
            return parse_obo(source_path)
        case SourceFormat.OWL:
            return parse_owl(source_path)
        case SourceFormat.JSON_FLAT:
            return parse_json_flat(
                source_path,
                id_field=opts.get("id_field", "id"),
                label_field=opts.get("label_field", "label"),
                definition_field=opts.get("definition_field") or "definition",
            )
        case SourceFormat.JSON_HIERARCHICAL:
            return parse_json_hierarchical(
                source_path,
                id_field=opts.get("id_field", "id"),
                label_field=opts.get("label_field", "label"),
            )
        case SourceFormat.CSV:
            return parse_csv(
                source_path,
                id_field=opts.get("id_field", "id"),
                label_field=opts.get("label_field", "label"),
                definition_field=opts.get("definition_field", "definition"),
                delimiter=",",
            )
        case SourceFormat.TSV:
            return parse_csv(
                source_path,
                id_field=opts.get("id_field", "id"),
                label_field=opts.get("label_field", "label"),
                definition_field=opts.get("definition_field", "definition"),
                delimiter="\t",
            )
        case SourceFormat.MESH_XML:
            return parse_mesh_xml(source_path)
        case SourceFormat.GMT:
            return parse_gmt(source_path)
        case SourceFormat.RF2:
            return parse_rf2(source_path)
        case _:
            raise ValueError(f"Unsupported format: {fmt}")


def _resolve_source(config: VocabularyConfig, base_dir: Path | None) -> Path:
    """Resolve the source path relative to base_dir."""
    if not config.source:
        raise ValueError(f"No source specified for vocabulary '{config.name}'")
    path = Path(config.source)
    if path.is_absolute():
        return path
    if base_dir:
        return base_dir / path
    return path


def _save_cache(terms: list[VocabularyTerm], cache_path: Path) -> None:
    """Save terms to JSON cache."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    data = [t.model_dump() for t in terms]
    cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

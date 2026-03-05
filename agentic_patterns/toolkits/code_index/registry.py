"""Registry of code indexes -- YAML file as source of truth, vector DB for semantic search."""

import logging
from pathlib import Path

import yaml

from agentic_patterns.core.config.config import DATA_DIR
from agentic_patterns.core.vectordb.vectordb import get_vector_db

logger = logging.getLogger(__name__)

REGISTRY_COLLECTION = "_code_index_registry"
REGISTRY_FILE = DATA_DIR / "code_indexes.yaml"


def get(collection_name: str) -> dict | None:
    """Get a single index entry from the YAML registry."""
    entries = get_all()
    return entries.get(collection_name)


def get_all() -> dict[str, dict]:
    """Return all entries from the YAML registry."""
    if not REGISTRY_FILE.exists():
        return {}
    data = yaml.safe_load(REGISTRY_FILE.read_text()) or {}
    return data.get("indexes", {})


def register(collection_name: str, repo_path: Path, description: str) -> None:
    """Add or update an index in both the YAML file and the registry vector DB."""
    entries = get_all()
    entries[collection_name] = {
        "repo_path": str(repo_path),
        "description": description,
    }
    _write_yaml(entries)

    vdb = get_vector_db(REGISTRY_COLLECTION)
    vdb.add(
        text=description,
        doc_id=collection_name,
        meta={"collection_name": collection_name, "repo_path": str(repo_path)},
        force=True,
    )


def search(query: str, top_k: int = 5) -> list[dict]:
    """Semantic search over index descriptions. Returns list of {collection_name, repo_path, description, score}."""
    vdb = get_vector_db(REGISTRY_COLLECTION)
    results = vdb.retrieve(query, max_results=top_k)
    return [
        {
            "collection_name": r.metadata.get("collection_name", ""),
            "repo_path": r.metadata.get("repo_path", ""),
            "description": r.text,
            "score": r.score,
        }
        for r in results
    ]


def unregister(collection_name: str) -> None:
    """Remove an index from the YAML file and registry vector DB."""
    entries = get_all()
    entries.pop(collection_name, None)
    _write_yaml(entries)

    vdb = get_vector_db(REGISTRY_COLLECTION)
    try:
        vdb.delete(collection_name)
    except Exception:
        logger.debug("Registry entry '%s' not found in vector DB", collection_name)


def _write_yaml(entries: dict[str, dict]) -> None:
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(yaml.dump({"indexes": entries}, default_flow_style=False, sort_keys=True))

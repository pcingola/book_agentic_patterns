"""Code search operations -- vector similarity and cross-reference expansion."""

from pathlib import Path

from agentic_patterns.core.connectors.code_repo.connector import CodeRepoConnector
from agentic_patterns.core.vectordb.models import RetrievedDocument
from agentic_patterns.core.vectordb.vectordb import get_vector_db


def expand_context(hit: RetrievedDocument, repo_path: Path) -> str:
    """Expand a search hit with surrounding context and cross-references."""
    connector = CodeRepoConnector()
    parts: list[str] = []

    # Original hit
    source = hit.metadata.get("source", "")
    symbol = hit.metadata.get("symbol_name", "")
    symbol_type = hit.metadata.get("symbol_type", "")
    start_line = hit.metadata.get("start_line", 0)

    parts.append(f"## {symbol_type} `{symbol}` in {source}")
    parts.append(f"```\n{hit.text}\n```")

    # Context window around the symbol
    if source and start_line:
        file_path = repo_path / source
        if file_path.is_file():
            window = connector.fetch_window(file_path, int(start_line), radius=5)
            parts.append(f"\n### Surrounding context\n{window}")

    # Cross-references: find call sites / usages
    if symbol and symbol not in (
        "<preamble>",
        "<anonymous>",
        "<export>",
        "<decorated>",
    ):
        refs = connector.lexical_search(repo_path, symbol, max_results=10)
        if refs and refs != "No matches found.":
            parts.append(f"\n### References to `{symbol}`\n{refs}")

    return "\n".join(parts)


def search_and_expand(
    collection_name: str,
    query: str,
    repo_path: Path,
    top_k: int = 5,
    expand_top: int = 3,
) -> str:
    """Search indexed code and expand top results with cross-references."""
    hits = search_code(collection_name, query, top_k)
    if not hits:
        return "No results found."

    parts: list[str] = []
    for i, hit in enumerate(hits):
        if i < expand_top:
            parts.append(expand_context(hit, repo_path))
        else:
            source = hit.metadata.get("source", "")
            symbol = hit.metadata.get("symbol_name", "")
            parts.append(f"- `{symbol}` in {source} (score: {hit.score:.3f})")

    return "\n\n---\n\n".join(parts)


def search_code(
    collection_name: str, query: str, top_k: int = 5
) -> list[RetrievedDocument]:
    """Vector similarity search over indexed code."""
    vdb = get_vector_db(collection_name)
    return vdb.retrieve(query, max_results=top_k)

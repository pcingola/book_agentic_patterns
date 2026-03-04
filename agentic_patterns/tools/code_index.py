"""PydanticAI agent tools for code indexing and search -- wraps toolkits/code_index/."""

from pathlib import Path

from pydantic_ai import ModelRetry

from agentic_patterns.core.connectors.code_repo.connector import CodeRepoConnector
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.toolkits.code_index import indexing, search


def get_all_tools() -> list:
    """Get all code index tools for use with PydanticAI agents."""
    connector = CodeRepoConnector()

    @tool_permission(ToolPermission.READ)
    async def code_index_repo(
        repo_path: str,
        collection_name: str,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> str:
        """Index a code repository for semantic search. Scans files, parses syntax trees, and stores embeddings."""
        try:
            stats = indexing.index_repo(
                Path(repo_path), collection_name, include_patterns, exclude_patterns
            )
            return str(stats)
        except (ValueError, OSError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    async def code_search(collection_name: str, query: str, top_k: int = 5) -> str:
        """Search indexed code by semantic similarity. Returns matching code symbols with file locations."""
        try:
            hits = search.search_code(collection_name, query, top_k)
            if not hits:
                return "No results found."
            parts = []
            for hit in hits:
                source = hit.metadata.get("source", "")
                symbol = hit.metadata.get("symbol_name", "")
                symbol_type = hit.metadata.get("symbol_type", "")
                start_line = hit.metadata.get("start_line", "")
                parts.append(
                    f"[{hit.score:.3f}] {symbol_type} `{symbol}` in {source}:{start_line}\n```\n{hit.text}\n```"
                )
            return "\n\n".join(parts)
        except (ValueError, KeyError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    async def code_search_expanded(
        collection_name: str, query: str, repo_path: str, top_k: int = 5
    ) -> str:
        """Search indexed code with cross-reference expansion on top results."""
        try:
            return search.search_and_expand(
                collection_name, query, Path(repo_path), top_k
            )
        except (ValueError, KeyError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    async def code_lexical_search(
        repo_path: str, pattern: str, max_results: int = 20
    ) -> str:
        """Exact/regex search across source files in a repository."""
        try:
            return connector.lexical_search(Path(repo_path), pattern, max_results)
        except (ValueError, OSError) as e:
            raise ModelRetry(str(e)) from e

    return [code_index_repo, code_lexical_search, code_search, code_search_expanded]

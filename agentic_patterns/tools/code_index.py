"""PydanticAI agent tools for code indexing and search -- wraps toolkits/code_index/."""

from pathlib import Path

from pydantic_ai import ModelRetry

from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.toolkits.code_index.code_index import CodeIndex
from agentic_patterns.toolkits.code_index.registry import get as registry_get
from agentic_patterns.toolkits.code_index.registry import search as registry_search

_indexes: dict[str, CodeIndex] = {}


def get_all_tools() -> list:
    """Get all code index tools for use with PydanticAI agents.

    The agent gets search/navigate/lexical/discovery tools. Indexing is done
    externally via CodeIndex.index(), which auto-registers in the registry.
    """

    @tool_permission(ToolPermission.READ)
    async def code_expand(collection_name: str, doc_id: str) -> str:
        """Expand a search result by doc_id to see full context: code, description, breadcrumbs, parent class, and sibling symbols."""
        try:
            ci = _get_index(collection_name)
            return ci.expand(doc_id)
        except (ValueError, KeyError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    async def code_lexical_search(
        collection_name: str, pattern: str, max_results: int = 20
    ) -> str:
        """Exact/regex search across source files in the indexed repository."""
        try:
            ci = _get_index(collection_name)
            return ci.lexical_search(pattern, max_results)
        except (ValueError, OSError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    async def code_list_indexes(query: str, top_k: int = 5) -> str:
        """Discover which code indexes are relevant to a query. Returns matching collections with name, repo path, and description. Call this when the user does not specify a collection name."""
        results = registry_search(query, top_k)
        if not results:
            return "No indexed repositories found."
        lines = []
        for r in results:
            lines.append(
                f"- collection: {r['collection_name']}, "
                f"repo: {r['repo_path']}, description: {r['description']}"
            )
        return "\n".join(lines)

    @tool_permission(ToolPermission.READ)
    async def code_search(collection_name: str, query: str, top_k: int = 10) -> str:
        """Search indexed code by semantic similarity across code, descriptions, and structural context. Returns matching symbols with descriptions and breadcrumbs."""
        try:
            ci = _get_index(collection_name)
            results = await ci.search(query, top_k)
            if not results:
                return "No results found."
            return "\n\n".join(str(r) for r in results)
        except (ValueError, KeyError) as e:
            raise ModelRetry(str(e)) from e

    return [code_expand, code_lexical_search, code_list_indexes, code_search]


def _get_index(collection_name: str) -> CodeIndex:
    """Get a CodeIndex by name. Reconstructs from the registry if not already in memory."""
    if collection_name not in _indexes:
        entry = registry_get(collection_name)
        if entry is None:
            raise ValueError(
                f"Collection '{collection_name}' not found. "
                f"Index a repository with CodeIndex.index() first."
            )
        _indexes[collection_name] = CodeIndex(Path(entry["repo_path"]), collection_name)
    return _indexes[collection_name]

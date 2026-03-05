"""PydanticAI agent tools for code indexing and search -- wraps toolkits/code_index/."""

from pydantic_ai import ModelRetry

from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.core.vectordb import get_vector_db
from agentic_patterns.toolkits.code_index.code_index import CodeIndex

_indexes: dict[str, CodeIndex] = {}

_REGISTRY_COLLECTION = "_code_index_registry"


def get_all_tools() -> list:
    """Get all code index tools for use with PydanticAI agents.

    The agent gets search/navigate/lexical tools. Indexing is done externally
    via CodeIndex.index() and registered with register_index().
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

    @tool_permission(ToolPermission.READ)
    async def code_list_indexes(query: str, top_k: int = 5) -> str:
        """Discover which code indexes are relevant to a query. Returns matching collections with name, repo path, and description. Call this when the user does not specify a collection name."""
        vdb = get_vector_db(_REGISTRY_COLLECTION)
        results = vdb.retrieve(query, max_results=top_k)
        if not results:
            return "No indexed repositories found."
        lines = []
        for r in results:
            meta = r.metadata
            lines.append(
                f"- collection: {meta.get('collection_name', '?')}, "
                f"repo: {meta.get('repo_path', '?')}, description: {r.text}"
            )
        return "\n".join(lines)

    return [code_expand, code_lexical_search, code_list_indexes, code_search]


def register_index(code_index: CodeIndex, description: str = "") -> None:
    """Register a CodeIndex so the agent tools can use it by collection name.

    When description is provided, it is also stored in a registry vector DB
    so the agent can discover relevant indexes via semantic search.
    """
    _indexes[code_index.collection_name] = code_index
    if description:
        vdb = get_vector_db(_REGISTRY_COLLECTION)
        vdb.add(
            text=description,
            doc_id=code_index.collection_name,
            meta={
                "collection_name": code_index.collection_name,
                "repo_path": str(code_index.repo_path),
            },
            force=True,
        )


def _get_index(collection_name: str) -> CodeIndex:
    """Get a cached CodeIndex or raise if not registered."""
    if collection_name not in _indexes:
        raise ValueError(
            f"Collection '{collection_name}' not found. "
            f"Index a repository with CodeIndex.index() and register it first."
        )
    return _indexes[collection_name]

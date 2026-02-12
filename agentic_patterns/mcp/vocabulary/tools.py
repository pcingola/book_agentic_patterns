"""MCP Vocabulary server tools -- thin wrapper delegating to core/connectors/vocabulary/."""

from fastmcp import Context, FastMCP

from agentic_patterns.core.mcp import ToolRetryError
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.core.connectors.vocabulary.connector import VocabularyConnector

_connector = VocabularyConnector()


def register_tools(mcp: FastMCP) -> None:
    """Register all vocabulary tools on the given MCP server instance."""

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def vocab_list(ctx: Context = None) -> str:
        """List all available vocabularies."""
        result = _connector.list_vocabularies()
        if ctx:
            await ctx.info("vocab_list")
        return result

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def vocab_info(vocab_name: str, ctx: Context = None) -> str:
        """Get metadata about a vocabulary."""
        result = _connector.info(vocab_name)
        if ctx:
            await ctx.info(f"vocab_info: {vocab_name}")
        if result.startswith("[Error]"):
            raise ToolRetryError(result)
        return result

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def vocab_lookup(vocab_name: str, term_code: str, ctx: Context = None) -> str:
        """Look up a term by its code/ID in a vocabulary."""
        result = _connector.lookup(vocab_name, term_code)
        if ctx:
            await ctx.info(f"vocab_lookup: {vocab_name} {term_code}")
        if result.startswith("[Error]"):
            raise ToolRetryError(result)
        return result

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def vocab_search(vocab_name: str, query: str, max_results: int = 10, ctx: Context = None) -> str:
        """Search for terms matching a text query."""
        result = _connector.search(vocab_name, query, max_results)
        if ctx:
            await ctx.info(f"vocab_search: {vocab_name} query='{query}'")
        if result.startswith("[Error]"):
            raise ToolRetryError(result)
        return result

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def vocab_validate(vocab_name: str, term_code: str, ctx: Context = None) -> str:
        """Validate whether a term code exists. Suggests corrections if invalid."""
        result = _connector.validate(vocab_name, term_code)
        if ctx:
            await ctx.info(f"vocab_validate: {vocab_name} {term_code}")
        if result.startswith("[Error]"):
            raise ToolRetryError(result)
        return result

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def vocab_suggest(vocab_name: str, text: str, max_results: int = 10, ctx: Context = None) -> str:
        """Get semantic suggestions for free text (RAG vocabularies only)."""
        result = _connector.suggest(vocab_name, text, max_results)
        if ctx:
            await ctx.info(f"vocab_suggest: {vocab_name} text='{text}'")
        if result.startswith("[Error]"):
            raise ToolRetryError(result)
        return result

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def vocab_parent(vocab_name: str, term_code: str, ctx: Context = None) -> str:
        """Get direct parent(s) of a term."""
        result = _connector.parent(vocab_name, term_code)
        if ctx:
            await ctx.info(f"vocab_parent: {vocab_name} {term_code}")
        if result.startswith("[Error]"):
            raise ToolRetryError(result)
        return result

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def vocab_children(vocab_name: str, term_code: str, ctx: Context = None) -> str:
        """Get direct children of a term."""
        result = _connector.children(vocab_name, term_code)
        if ctx:
            await ctx.info(f"vocab_children: {vocab_name} {term_code}")
        if result.startswith("[Error]"):
            raise ToolRetryError(result)
        return result

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def vocab_ancestors(vocab_name: str, term_code: str, max_depth: int = 10, ctx: Context = None) -> str:
        """Get ancestor chain to root."""
        result = _connector.ancestors(vocab_name, term_code, max_depth)
        if ctx:
            await ctx.info(f"vocab_ancestors: {vocab_name} {term_code}")
        if result.startswith("[Error]"):
            raise ToolRetryError(result)
        return result

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def vocab_descendants(vocab_name: str, term_code: str, max_depth: int = 10, ctx: Context = None) -> str:
        """Get all descendants up to max_depth."""
        result = _connector.descendants(vocab_name, term_code, max_depth)
        if ctx:
            await ctx.info(f"vocab_descendants: {vocab_name} {term_code}")
        if result.startswith("[Error]"):
            raise ToolRetryError(result)
        return result

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def vocab_relationships(vocab_name: str, term_code: str, ctx: Context = None) -> str:
        """Get all typed relationships for a term."""
        result = _connector.relationships(vocab_name, term_code)
        if ctx:
            await ctx.info(f"vocab_relationships: {vocab_name} {term_code}")
        if result.startswith("[Error]"):
            raise ToolRetryError(result)
        return result

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def vocab_related(vocab_name: str, term_code: str, relation_type: str, ctx: Context = None) -> str:
        """Get terms connected by a specific relation type."""
        result = _connector.related(vocab_name, term_code, relation_type)
        if ctx:
            await ctx.info(f"vocab_related: {vocab_name} {term_code} {relation_type}")
        if result.startswith("[Error]"):
            raise ToolRetryError(result)
        return result

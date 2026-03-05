"""Structural context (breadcrumbs) for code symbols -- deterministic, no LLM."""

from pathlib import Path

from agentic_patterns.core.vectordb.models import Chunk, ChunkLevel


def build_breadcrumb(chunk: Chunk, all_chunks: list[Chunk], file_path: Path) -> str:
    """Build a structural breadcrumb string from chunk metadata.

    Includes module path, parent class, signature, imports, and sibling symbols.
    """
    parts: list[str] = []
    source = chunk.metadata.get("source", str(file_path))
    symbol_type = chunk.metadata.get("symbol_type", "")

    # Module path
    parts.append(f"module: {source}")

    # Parent class (for methods)
    if chunk.parent_id:
        parent = _find_chunk(chunk.parent_id, all_chunks)
        if parent:
            parent_name = parent.metadata.get("symbol_name", "")
            parts.append(f"parent: class {parent_name}")

    # Signature (first line of code for functions/methods/classes)
    sig = _extract_signature(chunk.text, symbol_type)
    if sig:
        parts.append(f"signature: {sig}")

    # Imports from preamble
    preamble = _find_preamble(all_chunks)
    if preamble:
        imports = _extract_imports(preamble.text)
        if imports:
            parts.append(f"imports: {', '.join(imports)}")

    # Sibling symbols in the same file/class
    siblings = _find_siblings(chunk, all_chunks)
    if siblings:
        parts.append(f"siblings: {', '.join(siblings)}")

    return " | ".join(parts)


def build_breadcrumbs(chunks: list[Chunk], file_path: Path) -> dict[str, str]:
    """Build breadcrumbs for all chunks in a file. Returns doc_id -> breadcrumb."""
    result: dict[str, str] = {}
    for chunk in chunks:
        if chunk.level == ChunkLevel.DOCUMENT:
            continue
        name = chunk.metadata.get("symbol_name", "")
        if name in ("<preamble>", "<anonymous>", "<export>", "<decorated>"):
            continue
        result[chunk.doc_id] = build_breadcrumb(chunk, chunks, file_path)
    return result


def _extract_imports(preamble_text: str) -> list[str]:
    """Extract import module names from preamble text."""
    imports: list[str] = []
    for line in preamble_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("from "):
            # "from foo.bar import baz" -> "foo.bar"
            parts = stripped.split()
            if len(parts) >= 2:
                imports.append(parts[1])
        elif stripped.startswith("import "):
            # "import foo, bar" or "import foo.bar"
            rest = stripped[7:].split(",")
            for mod in rest:
                mod = mod.strip().split(" as ")[0].strip()
                if mod:
                    imports.append(mod)
    return imports


def _extract_signature(code: str, symbol_type: str) -> str:
    """Extract the signature line from a code block."""
    if symbol_type not in ("function", "method", "class"):
        return ""
    for line in code.splitlines():
        stripped = line.strip()
        # Python
        if stripped.startswith(("def ", "class ", "async def ")):
            return stripped.rstrip(":")
        # JavaScript/TypeScript
        if stripped.startswith(
            (
                "function ",
                "async function ",
                "export function ",
                "export async function ",
                "export class ",
                "export default class ",
            )
        ):
            sig = stripped.rstrip("{").strip()
            return sig
    return ""


def _find_chunk(doc_id: str, chunks: list[Chunk]) -> Chunk | None:
    for c in chunks:
        if c.doc_id == doc_id:
            return c
    return None


def _find_preamble(chunks: list[Chunk]) -> Chunk | None:
    for c in chunks:
        if c.metadata.get("symbol_type") == "preamble":
            return c
    return None


def _find_siblings(chunk: Chunk, all_chunks: list[Chunk]) -> list[str]:
    """Find other symbols at the same level (same parent) excluding the chunk itself."""
    siblings: list[str] = []
    for c in all_chunks:
        if c.doc_id == chunk.doc_id:
            continue
        name = c.metadata.get("symbol_name", "")
        if not name or name in ("<preamble>", "<anonymous>", "<export>", "<decorated>"):
            continue
        # Same parent means same scope
        if c.parent_id == chunk.parent_id:
            siblings.append(name)
    return siblings

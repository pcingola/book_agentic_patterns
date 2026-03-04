"""Syntax-aware code chunker using tree-sitter."""

from enum import Enum
from pathlib import Path

from agentic_patterns.core.doc_ingestion.models import DocumentProvenance
from agentic_patterns.core.rag.chunker import Chunker
from agentic_patterns.core.rag.chunking import get_stem, provenance_to_meta
from agentic_patterns.core.vectordb.models import Chunk, ChunkLevel


class SymbolType(str, Enum):
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    PREAMBLE = "preamble"


# Maps file extensions to tree-sitter language names and grammar modules
_LANGUAGE_MAP: dict[str, tuple[str, str]] = {
    ".py": ("python", "tree_sitter_python"),
    ".js": ("javascript", "tree_sitter_javascript"),
    ".jsx": ("javascript", "tree_sitter_javascript"),
    ".ts": ("typescript", "tree_sitter_typescript"),
    ".tsx": ("tsx", "tree_sitter_typescript"),
}

# AST node types that represent top-level code symbols per language
_SYMBOL_NODES: dict[str, dict[str, SymbolType]] = {
    "python": {
        "function_definition": SymbolType.FUNCTION,
        "class_definition": SymbolType.CLASS,
        "decorated_definition": SymbolType.FUNCTION,
    },
    "javascript": {
        "function_declaration": SymbolType.FUNCTION,
        "class_declaration": SymbolType.CLASS,
        "export_statement": SymbolType.FUNCTION,
    },
    "typescript": {
        "function_declaration": SymbolType.FUNCTION,
        "class_declaration": SymbolType.CLASS,
        "export_statement": SymbolType.FUNCTION,
    },
    "tsx": {
        "function_declaration": SymbolType.FUNCTION,
        "class_declaration": SymbolType.CLASS,
        "export_statement": SymbolType.FUNCTION,
    },
}


def _detect_language(provenance: DocumentProvenance) -> str | None:
    """Detect language from file extension."""
    path = provenance.original_file or provenance.markdown_file
    if not path:
        return None
    suffix = Path(path).suffix.lower()
    entry = _LANGUAGE_MAP.get(suffix)
    return entry[0] if entry else None


def _get_grammar_module(provenance: DocumentProvenance) -> str | None:
    path = provenance.original_file or provenance.markdown_file
    if not path:
        return None
    suffix = Path(path).suffix.lower()
    entry = _LANGUAGE_MAP.get(suffix)
    return entry[1] if entry else None


def _extract_symbol_name(node, language: str) -> str:
    """Extract the symbol name from an AST node."""
    # For decorated definitions, dig into the inner definition
    if node.type == "decorated_definition":
        for child in node.children:
            if child.type in ("function_definition", "class_definition"):
                return _extract_symbol_name(child, language)
        return "<decorated>"

    # For export statements, dig into the declaration
    if node.type == "export_statement":
        for child in node.children:
            name = _extract_symbol_name(child, language)
            if name != "<anonymous>":
                return name
        return "<export>"

    # Look for the name/identifier child node
    for child in node.children:
        if child.type in ("identifier", "property_identifier"):
            return child.text.decode("utf-8")
    return "<anonymous>"


def _resolve_symbol_type(node, language: str) -> SymbolType:
    """Resolve the actual symbol type, looking through wrappers."""
    if node.type == "decorated_definition":
        for child in node.children:
            if child.type == "class_definition":
                return SymbolType.CLASS
            if child.type == "function_definition":
                return SymbolType.FUNCTION
        return SymbolType.FUNCTION

    if node.type == "export_statement":
        for child in node.children:
            result = _SYMBOL_NODES.get(language, {}).get(child.type)
            if result:
                return result
        return SymbolType.FUNCTION

    return _SYMBOL_NODES.get(language, {}).get(node.type, SymbolType.FUNCTION)


class ChunkerCode(Chunker):
    """Splits source code at natural syntax boundaries using tree-sitter."""

    def __init__(self, min_preamble_lines: int = 2) -> None:
        self._min_preamble_lines = min_preamble_lines

    def chunk(self, text: str, provenance: DocumentProvenance) -> list[Chunk]:
        language = _detect_language(provenance)
        if not language:
            return self._fallback_chunk(text, provenance)

        grammar_module = _get_grammar_module(provenance)
        if not grammar_module:
            return self._fallback_chunk(text, provenance)

        try:
            return self._chunk_with_treesitter(
                text, provenance, language, grammar_module
            )
        except Exception:
            return self._fallback_chunk(text, provenance)

    def _chunk_with_treesitter(
        self,
        text: str,
        provenance: DocumentProvenance,
        language: str,
        grammar_module: str,
    ) -> list[Chunk]:
        import importlib

        import tree_sitter as ts

        mod = importlib.import_module(grammar_module)
        # tree-sitter-python etc. expose a language() function
        lang = ts.Language(mod.language())
        parser = ts.Parser(lang)

        source_bytes = text.encode("utf-8")
        tree = parser.parse(source_bytes)
        root = tree.root_node

        stem = get_stem(provenance)
        meta = provenance_to_meta(provenance)
        file_doc_id = f"{stem}-file"
        symbol_nodes = _SYMBOL_NODES.get(language, {})

        chunks: list[Chunk] = []
        preamble_lines: list[str] = []
        lines = text.split("\n")
        symbol_idx = 0
        covered_ranges: list[tuple[int, int]] = []

        # Collect top-level symbol nodes
        for child in root.children:
            if child.type in symbol_nodes:
                covered_ranges.append((child.start_point.row, child.end_point.row))
                symbol_idx += 1
                symbol_name = _extract_symbol_name(child, language)
                symbol_type = _resolve_symbol_type(child, language)
                start_line = child.start_point.row
                end_line = child.end_point.row
                chunk_text = "\n".join(lines[start_line : end_line + 1])
                doc_id = f"{stem}-{symbol_type.value}-{symbol_idx}-{symbol_name}"

                chunk_meta = dict(meta)
                chunk_meta["symbol_name"] = symbol_name
                chunk_meta["symbol_type"] = symbol_type.value
                chunk_meta["start_line"] = start_line + 1
                chunk_meta["end_line"] = end_line + 1

                chunks.append(
                    Chunk(
                        doc_id=doc_id,
                        text=chunk_text,
                        level=ChunkLevel.SECTION,
                        parent_id=file_doc_id,
                        metadata=chunk_meta,
                    )
                )

                # For classes, also extract methods as sub-chunks
                if symbol_type == SymbolType.CLASS:
                    self._extract_methods(
                        child, lines, stem, symbol_idx, meta, doc_id, language, chunks
                    )

        # Build preamble from lines not covered by any symbol
        for i, line in enumerate(lines):
            if not any(start <= i <= end for start, end in covered_ranges):
                preamble_lines.append(line)

        preamble_text = "\n".join(preamble_lines).strip()
        if (
            preamble_text
            and len(preamble_text.splitlines()) >= self._min_preamble_lines
        ):
            preamble_meta = dict(meta)
            preamble_meta["symbol_name"] = "<preamble>"
            preamble_meta["symbol_type"] = SymbolType.PREAMBLE.value
            chunks.insert(
                0,
                Chunk(
                    doc_id=f"{stem}-preamble",
                    text=preamble_text,
                    level=ChunkLevel.SECTION,
                    parent_id=file_doc_id,
                    metadata=preamble_meta,
                ),
            )

        # Add file-level parent chunk
        file_meta = dict(meta)
        file_meta["symbol_type"] = "file"
        chunks.insert(
            0,
            Chunk(
                doc_id=file_doc_id,
                text=text,
                level=ChunkLevel.DOCUMENT,
                parent_id=None,
                metadata=file_meta,
            ),
        )

        return chunks

    def _extract_methods(
        self,
        class_node,
        lines: list[str],
        stem: str,
        class_idx: int,
        meta: dict,
        class_doc_id: str,
        language: str,
        chunks: list[Chunk],
    ) -> None:
        """Extract method-level chunks from a class node."""
        method_types = {"function_definition", "method_definition"}
        method_idx = 0
        for child in class_node.children:
            # Handle decorated methods
            node = child
            if child.type == "decorated_definition":
                for sub in child.children:
                    if sub.type in method_types:
                        node = sub
                        break
                else:
                    continue
            elif child.type == "block":
                # Python class body is inside a block node
                for block_child in child.children:
                    inner = block_child
                    if block_child.type == "decorated_definition":
                        for sub in block_child.children:
                            if sub.type in method_types:
                                inner = sub
                                break
                        else:
                            continue
                    if inner.type in method_types:
                        method_idx += 1
                        method_name = _extract_symbol_name(block_child, language)
                        start_line = block_child.start_point.row
                        end_line = block_child.end_point.row
                        chunk_text = "\n".join(lines[start_line : end_line + 1])
                        doc_id = (
                            f"{stem}-class{class_idx}-method-{method_idx}-{method_name}"
                        )
                        method_meta = dict(meta)
                        method_meta["symbol_name"] = method_name
                        method_meta["symbol_type"] = SymbolType.METHOD.value
                        method_meta["start_line"] = start_line + 1
                        method_meta["end_line"] = end_line + 1
                        chunks.append(
                            Chunk(
                                doc_id=doc_id,
                                text=chunk_text,
                                level=ChunkLevel.PARAGRAPH,
                                parent_id=class_doc_id,
                                metadata=method_meta,
                            )
                        )
                continue

            if node.type not in method_types:
                continue
            method_idx += 1
            method_name = _extract_symbol_name(child, language)
            start_line = child.start_point.row
            end_line = child.end_point.row
            chunk_text = "\n".join(lines[start_line : end_line + 1])
            doc_id = f"{stem}-class{class_idx}-method-{method_idx}-{method_name}"
            method_meta = dict(meta)
            method_meta["symbol_name"] = method_name
            method_meta["symbol_type"] = SymbolType.METHOD.value
            method_meta["start_line"] = start_line + 1
            method_meta["end_line"] = end_line + 1
            chunks.append(
                Chunk(
                    doc_id=doc_id,
                    text=chunk_text,
                    level=ChunkLevel.PARAGRAPH,
                    parent_id=class_doc_id,
                    metadata=method_meta,
                )
            )

    def _fallback_chunk(self, text: str, provenance: DocumentProvenance) -> list[Chunk]:
        from agentic_patterns.core.rag.chunker_smart import ChunkerSmart

        return ChunkerSmart().chunk(text, provenance)

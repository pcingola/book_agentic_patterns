"""Unit tests for code index breadcrumbs."""

import unittest
from pathlib import Path

from agentic_patterns.core.vectordb.models import Chunk, ChunkLevel
from agentic_patterns.toolkits.code_index.breadcrumbs import (
    build_breadcrumb,
    build_breadcrumbs,
)


def _make_chunk(
    doc_id: str,
    text: str,
    symbol_name: str,
    symbol_type: str,
    source: str = "example.py",
    level: ChunkLevel = ChunkLevel.SECTION,
    parent_id: str | None = None,
) -> Chunk:
    return Chunk(
        doc_id=doc_id,
        text=text,
        level=level,
        parent_id=parent_id,
        metadata={
            "symbol_name": symbol_name,
            "symbol_type": symbol_type,
            "source": source,
        },
    )


class TestBuildBreadcrumbs(unittest.TestCase):
    def setUp(self) -> None:
        self.preamble = _make_chunk(
            "f-preamble",
            "import os\nfrom pathlib import Path",
            "<preamble>",
            "preamble",
            level=ChunkLevel.PARAGRAPH,
        )
        self.func = _make_chunk(
            "f-connect",
            "def connect(host: str) -> bool:\n    pass",
            "connect",
            "function",
        )
        self.cls = _make_chunk(
            "f-pool",
            "class ConnectionPool:\n    pass",
            "ConnectionPool",
            "class",
        )
        self.method = _make_chunk(
            "f-acquire",
            "def acquire(self) -> object:\n    pass",
            "acquire",
            "method",
            parent_id="f-pool",
        )
        self.all_chunks = [self.preamble, self.func, self.cls, self.method]

    def test_breadcrumbs_skip_preamble_and_document(self) -> None:
        doc_chunk = _make_chunk("f-doc", "", "", "", level=ChunkLevel.DOCUMENT)
        chunks = [self.preamble, doc_chunk, self.func]
        result = build_breadcrumbs(chunks, Path("example.py"))
        self.assertNotIn("f-preamble", result)
        self.assertNotIn("f-doc", result)
        self.assertIn("f-connect", result)

    def test_breadcrumb_contains_module(self) -> None:
        bc = build_breadcrumb(self.func, self.all_chunks, Path("example.py"))
        self.assertIn("module: example.py", bc)

    def test_breadcrumb_contains_signature(self) -> None:
        bc = build_breadcrumb(self.func, self.all_chunks, Path("example.py"))
        self.assertIn("signature: def connect(host: str) -> bool", bc)

    def test_breadcrumb_method_has_parent(self) -> None:
        bc = build_breadcrumb(self.method, self.all_chunks, Path("example.py"))
        self.assertIn("parent: class ConnectionPool", bc)

    def test_breadcrumb_contains_imports(self) -> None:
        bc = build_breadcrumb(self.func, self.all_chunks, Path("example.py"))
        self.assertIn("imports:", bc)
        self.assertIn("os", bc)
        self.assertIn("pathlib", bc)

    def test_breadcrumb_contains_siblings(self) -> None:
        bc = build_breadcrumb(self.func, self.all_chunks, Path("example.py"))
        self.assertIn("siblings:", bc)
        self.assertIn("ConnectionPool", bc)

    def test_build_breadcrumbs_returns_all_symbols(self) -> None:
        result = build_breadcrumbs(self.all_chunks, Path("example.py"))
        self.assertEqual(set(result.keys()), {"f-connect", "f-pool", "f-acquire"})


if __name__ == "__main__":
    unittest.main()

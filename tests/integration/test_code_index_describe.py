"""Integration tests for code index describe_symbols (LLM mocked)."""

import unittest
from unittest.mock import patch

from agentic_patterns.core.rag.chunker_code import SymbolType
from agentic_patterns.core.vectordb.models import Chunk, ChunkLevel
from agentic_patterns.testing.model_mock import ModelMock, final_result_tool
from agentic_patterns.toolkits.code_index.describe import (
    SymbolDescriptions,
    SymbolDescription,
    describe_symbols,
)


def _make_chunk(
    doc_id: str,
    text: str,
    symbol_name: str,
    symbol_type: str,
    source: str = "example.py",
) -> Chunk:
    return Chunk(
        doc_id=doc_id,
        text=text,
        level=ChunkLevel.SECTION,
        parent_id=None,
        metadata={
            "symbol_name": symbol_name,
            "symbol_type": symbol_type,
            "source": source,
        },
    )


class TestDescribeSymbols(unittest.IsolatedAsyncioTestCase):

    async def test_descriptions_matched_to_doc_ids(self) -> None:
        """The LLM returns SymbolType enum values; they must match the string keys from metadata."""
        chunks = [
            _make_chunk("id-connect", "def connect(): pass", "connect", "function"),
            _make_chunk("id-pool", "class Pool: pass", "Pool", "class"),
        ]
        mock_response = final_result_tool(SymbolDescriptions(symbols=[
            SymbolDescription(symbol_name="connect", symbol_type=SymbolType.FUNCTION, description="Establishes a connection."),
            SymbolDescription(symbol_name="Pool", symbol_type=SymbolType.CLASS, description="Manages pooled connections."),
        ]))
        model = ModelMock(responses=[mock_response])

        with patch("agentic_patterns.toolkits.code_index.describe.get_agent") as mock_get_agent:
            from pydantic_ai import Agent
            agent = Agent(model=model, output_type=SymbolDescriptions)
            mock_get_agent.return_value = agent
            result = await describe_symbols(chunks)

        self.assertEqual(len(result), 2)
        self.assertEqual(result["id-connect"], "Establishes a connection.")
        self.assertEqual(result["id-pool"], "Manages pooled connections.")

    async def test_empty_chunks_returns_empty(self) -> None:
        result = await describe_symbols([])
        self.assertEqual(result, {})

    async def test_preamble_chunks_are_filtered(self) -> None:
        chunks = [
            _make_chunk("id-preamble", "import os", "<preamble>", "preamble"),
        ]
        result = await describe_symbols(chunks)
        self.assertEqual(result, {})

    async def test_unmatched_symbols_are_skipped(self) -> None:
        """If the LLM returns a symbol name that doesn't match any chunk, it is ignored."""
        chunks = [
            _make_chunk("id-foo", "def foo(): pass", "foo", "function"),
        ]
        mock_response = final_result_tool(SymbolDescriptions(symbols=[
            SymbolDescription(symbol_name="foo", symbol_type=SymbolType.FUNCTION, description="Does foo."),
            SymbolDescription(symbol_name="bar", symbol_type=SymbolType.FUNCTION, description="Does bar."),
        ]))
        model = ModelMock(responses=[mock_response])

        with patch("agentic_patterns.toolkits.code_index.describe.get_agent") as mock_get_agent:
            from pydantic_ai import Agent
            agent = Agent(model=model, output_type=SymbolDescriptions)
            mock_get_agent.return_value = agent
            result = await describe_symbols(chunks)

        self.assertEqual(len(result), 1)
        self.assertEqual(result["id-foo"], "Does foo.")


if __name__ == "__main__":
    unittest.main()

"""Chunker ABC -- base class for all chunking strategies."""

from abc import ABC, abstractmethod

from agentic_patterns.core.doc_ingestion.models import DocumentProvenance
from agentic_patterns.core.vectordb.models import Chunk


class Chunker(ABC):
    @abstractmethod
    def chunk(self, text: str, provenance: DocumentProvenance) -> list[Chunk]: ...

    async def achunk(self, text: str, provenance: DocumentProvenance) -> list[Chunk]:
        """Async variant. Default calls sync chunk()."""
        return self.chunk(text, provenance)

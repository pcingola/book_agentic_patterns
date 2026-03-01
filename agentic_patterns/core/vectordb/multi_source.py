"""Multi-source retrieval across named VectorDB collections."""

import asyncio

from agentic_patterns.core.vectordb.models import ChunkLevel, RetrievedDocument
from agentic_patterns.core.vectordb.vectordb import VectorDB


class MultiSourceRetriever:
    """Retrieves from multiple named VectorDB collections in parallel."""

    def __init__(self, **sources: VectorDB) -> None:
        self.sources = sources

    async def retrieve_all(
        self,
        query: str,
        max_results: int = 10,
        level: ChunkLevel | None = None,
    ) -> list[RetrievedDocument]:
        """Query all sources concurrently, merge, deduplicate, and sort by score.

        Source name is stored in each document's metadata under 'source_collection'.
        """
        async def _query(name: str, vdb: VectorDB) -> list[RetrievedDocument]:
            docs = await vdb.aretrieve(query, max_results=max_results, level=level)
            for doc in docs:
                doc.metadata["source_collection"] = name
            return docs

        results = await asyncio.gather(*[_query(name, vdb) for name, vdb in self.sources.items()])
        all_docs = [doc for docs in results for doc in docs]

        seen: dict[str, RetrievedDocument] = {}
        for doc in all_docs:
            if doc.doc_id not in seen or doc.score > seen[doc.doc_id].score:
                seen[doc.doc_id] = doc
        return sorted(seen.values(), key=lambda d: d.score, reverse=True)

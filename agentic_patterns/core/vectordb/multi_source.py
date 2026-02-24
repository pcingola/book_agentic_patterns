"""Multi-source retrieval across named VectorDB collections."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from agentic_patterns.core.vectordb.models import ChunkLevel, RetrievedDocument
from agentic_patterns.core.vectordb.vectordb import VectorDB


class MultiSourceRetriever:
    """Retrieves from multiple named VectorDB collections in parallel."""

    def __init__(self, sources: dict[str, VectorDB]) -> None:
        self.sources = sources

    def retrieve_all(
        self,
        query: str,
        max_results: int = 10,
        level: ChunkLevel | None = None,
    ) -> list[RetrievedDocument]:
        """Query all sources in parallel, merge, deduplicate, and sort by score.

        Source name is stored in each document's metadata under 'source_collection'.
        """
        all_docs: list[RetrievedDocument] = []

        def _query(name: str, vdb: VectorDB) -> list[RetrievedDocument]:
            docs = vdb.retrieve(query, max_results=max_results, level=level)
            for doc in docs:
                doc.metadata["source_collection"] = name
            return docs

        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(_query, name, vdb): name
                for name, vdb in self.sources.items()
            }
            for future in as_completed(futures):
                all_docs.extend(future.result())

        seen: dict[str, RetrievedDocument] = {}
        for doc in all_docs:
            if doc.doc_id not in seen or doc.score > seen[doc.doc_id].score:
                seen[doc.doc_id] = doc
        return sorted(seen.values(), key=lambda d: d.score, reverse=True)

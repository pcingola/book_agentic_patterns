"""Multi-source retrieval across named Chroma collections."""

from concurrent.futures import ThreadPoolExecutor, as_completed

import chromadb

from agentic_patterns.core.vectordb.models import ChunkLevel, RetrievedDocument
from agentic_patterns.core.vectordb.retrieval import retrieve


class MultiSourceRetriever:
    """Retrieves from multiple named vector database collections in parallel."""

    def __init__(self, sources: dict[str, chromadb.Collection]) -> None:
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

        def _query_source(name: str, collection: chromadb.Collection) -> list[RetrievedDocument]:
            docs = retrieve(collection, query, max_results=max_results, level=level)
            for doc in docs:
                doc.metadata["source_collection"] = name
            return docs

        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(_query_source, name, col): name for name, col in self.sources.items()}
            for future in as_completed(futures):
                all_docs.extend(future.result())

        # Deduplicate by doc_id, keeping highest score
        seen: dict[str, RetrievedDocument] = {}
        for doc in all_docs:
            if doc.doc_id not in seen or doc.score > seen[doc.doc_id].score:
                seen[doc.doc_id] = doc

        return sorted(seen.values(), key=lambda d: d.score, reverse=True)

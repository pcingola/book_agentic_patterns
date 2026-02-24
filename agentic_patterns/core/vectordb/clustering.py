"""Embedding-based clustering for chunks and Chroma collections."""

import asyncio

import chromadb
import numpy as np

from agentic_patterns.core.vectordb.models import Chunk, Cluster, ClusterItem, ClusterResult


def cluster(
    input: list[Chunk] | chromadb.Collection,
    n_clusters: int | None = None,
    algorithm: str = "hdbscan",
    embedder=None,
) -> ClusterResult:
    """Cluster chunks or a Chroma collection by embedding similarity.

    When input is a chromadb.Collection, stored embeddings are fetched directly.
    algorithm="kmeans" requires n_clusters; algorithm="hdbscan" auto-discovers k.
    Returns ClusterResult with label=None and summary=None on each cluster.
    """
    if isinstance(input, list):
        ids, texts, metadatas, embeddings = _embed_chunks(input, embedder)
    else:
        ids, texts, metadatas, embeddings = _fetch_collection(input)

    if not ids:
        return ClusterResult(clusters=[])

    labels = _run_algorithm(embeddings, algorithm, n_clusters)
    return _build_result(ids, texts, metadatas, labels)


def _embed_chunks(chunks: list[Chunk], embedder) -> tuple[list, list, list, list]:
    from agentic_patterns.core.vectordb.embeddings import embed_texts, get_embedder

    if embedder is None:
        embedder = get_embedder()

    ids = [c.doc_id for c in chunks]
    texts = [c.text for c in chunks]
    metadatas = [c.metadata for c in chunks]

    loop = asyncio.get_event_loop()
    if loop.is_running():
        import nest_asyncio
        nest_asyncio.apply()
    embeddings = loop.run_until_complete(embed_texts(texts, embedder))
    return ids, texts, metadatas, embeddings


def _fetch_collection(collection: chromadb.Collection) -> tuple[list, list, list, list]:
    result = collection.get(include=["embeddings", "documents", "metadatas"])
    ids = result.get("ids", [])
    texts = result.get("documents", []) or [""] * len(ids)
    metadatas = result.get("metadatas", []) or [{}] * len(ids)
    embeddings = result.get("embeddings", [])
    return ids, texts, metadatas, embeddings


def _run_algorithm(embeddings: list, algorithm: str, n_clusters: int | None) -> list[int]:
    X = np.array(embeddings)
    match algorithm:
        case "hdbscan":
            import hdbscan
            clusterer = hdbscan.HDBSCAN(min_cluster_size=2)
            return list(clusterer.fit_predict(X))
        case "kmeans":
            if n_clusters is None:
                raise ValueError("n_clusters is required for kmeans algorithm")
            from sklearn.cluster import KMeans
            km = KMeans(n_clusters=n_clusters, n_init="auto")
            return list(km.fit_predict(X))
        case _:
            raise ValueError(f"Unsupported clustering algorithm: {algorithm!r}")


def _build_result(ids: list, texts: list, metadatas: list, labels: list[int]) -> ClusterResult:
    clusters_dict: dict[int, list[ClusterItem]] = {}
    for doc_id, text, meta, label in zip(ids, texts, metadatas, labels):
        clusters_dict.setdefault(label, []).append(ClusterItem(doc_id=doc_id, text=text, metadata=meta or {}))

    clusters = [
        Cluster(cluster_id=label, items=items)
        for label, items in sorted(clusters_dict.items())
    ]
    return ClusterResult(clusters=clusters)

"""Embedding-based clustering for chunks and VectorDB collections."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from agentic_patterns.core.vectordb.vectordb import VectorDB

from agentic_patterns.core.vectordb.models import (
    Chunk,
    Cluster,
    ClusterAlgorithm,
    ClusterItem,
    ClusterResult,
    DimReducer,
)


def cluster(
    input: "list[Chunk] | VectorDB",
    n_clusters: int | None = None,
    algorithm: ClusterAlgorithm = ClusterAlgorithm.AGGLOMERATIVE,
    reduce_dim: DimReducer | None = None,
    n_components: int = 50,
    distance_threshold: float = 0.3,
    min_cluster_size: int = 10,
    embedder=None,
) -> ClusterResult:
    """Cluster chunks or a VectorDB collection by embedding similarity.

    When input is a VectorDB, stored embeddings are fetched directly (no re-embedding).
    Use reduce_dim to apply dimensionality reduction before clustering.
    For agglomerative without n_clusters, distance_threshold controls auto-k discovery.
    """
    if isinstance(input, list):
        ids, texts, metadatas, embeddings = _embed_chunks(input, embedder)
    else:
        ids, texts, metadatas, embeddings = _fetch_collection(input)

    if not ids:
        return ClusterResult(clusters=[])

    X = np.array(embeddings)
    if reduce_dim is not None:
        X = _reduce(X, reduce_dim, n_components)

    labels = _run_algorithm(X, algorithm, n_clusters, distance_threshold)
    return _build_result(ids, texts, metadatas, labels)


def _reduce(X: np.ndarray, reducer: DimReducer, n_components: int) -> np.ndarray:
    match reducer:
        case DimReducer.UMAP:
            import umap

            return umap.UMAP(n_components=n_components).fit_transform(X)
        case DimReducer.PACMAP:
            import pacmap

            return pacmap.PaCMAP(n_components=n_components).fit_transform(X)


def _run_algorithm(
    X: np.ndarray,
    algorithm: ClusterAlgorithm,
    n_clusters: int | None,
    distance_threshold: float,
) -> list[int]:
    match algorithm:
        case ClusterAlgorithm.AGGLOMERATIVE:
            from sklearn.cluster import AgglomerativeClustering

            if n_clusters is not None:
                model = AgglomerativeClustering(
                    n_clusters=n_clusters, metric="cosine", linkage="average"
                )
            else:
                model = AgglomerativeClustering(
                    metric="cosine",
                    linkage="average",
                    distance_threshold=distance_threshold,
                    n_clusters=None,
                )
            return list(model.fit_predict(X))
        case ClusterAlgorithm.HDBSCAN:
            import hdbscan

            return list(hdbscan.HDBSCAN(min_cluster_size=2).fit_predict(X))
        case ClusterAlgorithm.KMEANS:
            from sklearn.cluster import KMeans

            if n_clusters is None:
                raise ValueError("n_clusters is required for kmeans")
            return list(KMeans(n_clusters=n_clusters, n_init="auto").fit_predict(X))
        case ClusterAlgorithm.SPHERICAL_KMEANS:
            from sklearn.cluster import KMeans

            if n_clusters is None:
                raise ValueError("n_clusters is required for spherical_kmeans")
            norms = np.linalg.norm(X, axis=1, keepdims=True)
            X_norm = X / np.where(norms == 0, 1, norms)
            return list(
                KMeans(n_clusters=n_clusters, n_init="auto").fit_predict(X_norm)
            )


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


def _fetch_collection(vdb: "VectorDB") -> tuple[list, list, list, list]:
    return vdb.get_all_with_embeddings()


def _build_result(
    ids: list, texts: list, metadatas: list, labels: list[int]
) -> ClusterResult:
    clusters_dict: dict[int, list[ClusterItem]] = {}
    for doc_id, text, meta, label in zip(ids, texts, metadatas, labels):
        clusters_dict.setdefault(label, []).append(
            ClusterItem(doc_id=doc_id, text=text, metadata=meta or {})
        )
    return ClusterResult(
        clusters=[
            Cluster(cluster_id=label, items=items)
            for label, items in sorted(clusters_dict.items())
        ]
    )

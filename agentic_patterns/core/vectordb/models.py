"""Shared data models for vector database chunking, retrieval, and clustering."""

from enum import Enum

from pydantic import BaseModel


class ClusterAlgorithm(str, Enum):
    AGGLOMERATIVE = "agglomerative"
    HDBSCAN = "hdbscan"
    KMEANS = "kmeans"
    SPHERICAL_KMEANS = "spherical_kmeans"


class DimReducer(str, Enum):
    PACMAP = "pacmap"
    UMAP = "umap"


class ChunkLevel(str, Enum):
    DOCUMENT = "DOCUMENT"
    CHAPTER = "CHAPTER"
    SECTION = "SECTION"
    PARAGRAPH = "PARAGRAPH"


class Chunk(BaseModel):
    """A text chunk with provenance and hierarchy metadata."""

    doc_id: str
    text: str
    level: ChunkLevel
    parent_id: str | None
    metadata: dict

    def __str__(self) -> str:
        return f"Chunk({self.doc_id}, level={self.level}, len={len(self.text)})"


class RetrievedDocument(BaseModel):
    """A document retrieved from the vector database with its similarity score."""

    doc_id: str
    text: str
    score: float
    level: ChunkLevel
    parent_id: str | None
    metadata: dict

    def __str__(self) -> str:
        return f"RetrievedDocument({self.doc_id}, score={self.score:.3f}, level={self.level})"


class ClusterItem(BaseModel):
    doc_id: str
    text: str
    metadata: dict


class Cluster(BaseModel):
    cluster_id: int
    label: str | None = None
    summary: str | None = None
    items: list[ClusterItem]

    def __str__(self) -> str:
        return f"Cluster({self.cluster_id}, label={self.label!r}, n={len(self.items)})"


class ClusterResult(BaseModel):
    clusters: list[Cluster]

    def __str__(self) -> str:
        return f"ClusterResult(n_clusters={len(self.clusters)})"

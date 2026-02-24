## Semantic Clustering

Retrieval-augmented systems are built on the assumption that a query can identify the relevant subset of a corpus. This assumption holds when users know what they are looking for. But many RAG applications involve tasks where the structure of the corpus itself is unknown: a new domain corpus has just been ingested, a collection of customer concerns needs to be organized into themes, or a research assistant must identify recurring patterns across hundreds of documents. Semantic clustering addresses these tasks by grouping documents by embedding similarity rather than by query relevance.

#### Clustering in embedding space

Semantic clustering treats each chunk or document as a point in a high-dimensional embedding space and applies a clustering algorithm to partition or densely group those points. The key property of clustering in embedding space is that geometric proximity reflects semantic similarity: chunks about the same topic will cluster together, even if they use different terminology.

The choice of clustering algorithm has significant implications for how results are structured. Two families dominate RAG applications.

Partitional clustering, most commonly k-means, divides the corpus into exactly *k* groups where each point belongs to exactly one cluster. The number of clusters must be specified in advance, which requires either domain knowledge or a model selection procedure. K-means is efficient and scales to millions of points, but it assumes spherical clusters and equal cluster sizes—assumptions that rarely hold in heterogeneous document corpora. It is most useful when the number of topics is approximately known and the corpus is relatively homogeneous.

```python
from sklearn.cluster import KMeans
import numpy as np

X = np.array(embeddings)
km = KMeans(n_clusters=k, n_init="auto")
labels = km.fit_predict(X)
```

Density-based clustering, most commonly HDBSCAN (Hierarchical Density-Based Spatial Clustering of Applications with Noise), automatically discovers the number of clusters by finding dense regions in embedding space. Points in sparse regions are labeled as noise (cluster label -1) rather than forced into a cluster. This is important in RAG: not every document belongs to a coherent theme, and forcing noisy or peripheral documents into clusters distorts the structure. HDBSCAN is more computationally intensive than k-means but produces more interpretable results on heterogeneous corpora.

```python
import hdbscan
import numpy as np

X = np.array(embeddings)
clusterer = hdbscan.HDBSCAN(min_cluster_size=5)
labels = clusterer.fit_predict(X)
# labels == -1 indicates noise points
```

The `min_cluster_size` parameter controls the minimum number of points required to form a cluster. Setting it too low produces many small, specific clusters; setting it too high merges distinct themes. The appropriate value depends on corpus size and the expected granularity of topics.

#### Fetching stored embeddings

A practical advantage of clustering collections that have been ingested into a vector database is that embeddings are already computed and stored. Re-embedding is expensive; fetching stored vectors is cheap. Chroma's collection API supports direct embedding retrieval:

```python
result = collection.get(include=["embeddings", "documents", "metadatas"])
embeddings = result["embeddings"]  # shape: (n_docs, embedding_dim)
documents = result["documents"]
ids = result["ids"]
```

This avoids re-running embedding inference and ensures that clustering is performed in exactly the same space as retrieval, which is important for consistency.

#### LLM-based cluster labeling

Clustering produces groups of documents, not interpretations. Each cluster is initially identified only by its constituent documents. To make clusters actionable, they must be labeled: given the items in a cluster, what topic or theme does it represent?

This is a natural task for a language model. The prompt presents a sample of documents from the cluster (or their summaries) and asks the model to produce a short label and a concise summary. Because the model has broad semantic knowledge, it can identify themes even when individual documents use varied terminology.

```python
label_prompt = """
Given these text passages from a cluster, provide:
1. A short label (2-5 words) identifying the cluster's theme
2. A one-sentence summary of what the cluster covers

Passages:
{passages}
"""
```

The returned label and summary transform the cluster from an opaque set of embeddings into a named, interpretable category. In practice, cluster labels serve as the building blocks for higher-level corpus navigation.

#### Applications in RAG systems

Semantic clustering serves several distinct roles in RAG architectures.

**Corpus exploration and quality control.** After ingesting a new document set, clustering reveals the topical distribution of the corpus. Dominant clusters indicate well-represented topics; sparse or isolated clusters may indicate outlier documents or ingestion errors. An engineer can inspect cluster labels to verify that the corpus covers the expected domains before the system goes into production.

**Query routing at topic level.** When cluster labels are computed in advance, incoming queries can be routed not just by collection but by cluster. A query about a specific theme is directed to chunks in the relevant cluster, reducing retrieval noise. This is a form of dynamic filtering that operates on semantic structure rather than explicit metadata tags.

**Rubric and criteria refinement.** In evaluation and assessment systems, clusters over historical examples reveal which themes occur frequently and which are rare. This allows rubric authors to calibrate criteria against actual evidence: criteria that no cluster matches may be obsolete, while frequently occurring clusters without a corresponding criterion indicate a gap in the rubric.

**Theme extraction from unstructured feedback.** Customer support tickets, survey responses, and meeting minutes often contain recurring concerns that are not labeled explicitly. Clustering these texts groups related concerns together, and LLM labeling names the themes. The resulting cluster structure is a lightweight taxonomy derived from actual data rather than manually designed.

#### Hierarchical and multi-level clustering

Single-level clustering treats all documents at the same granularity. For large or heterogeneous corpora, a hierarchical approach is often more useful. A coarse first pass identifies broad themes; a second pass clusters within each theme to produce subtopics. This two-level structure mirrors the hierarchical organization of knowledge in many domains: a top level of "product areas" and a second level of "feature categories" within each area.

HDBSCAN supports hierarchical clustering natively through its condensed tree representation, which can be cut at different levels to produce coarser or finer partitions. K-means can be applied hierarchically by running a second k-means pass within each first-level cluster.

The output of multi-level clustering is a cluster tree, where each node is a named topic and leaf nodes contain the individual documents. This structure can serve as a navigational index for the corpus, allowing users to drill into topics of interest rather than relying entirely on query-based retrieval.

#### Clustering as a complement to retrieval

Retrieval and clustering are complementary strategies for accessing a corpus. Retrieval is query-driven and latency-sensitive; clustering is exploratory and batch-oriented. Together they support two modes of use: a user who knows what they are looking for uses retrieval; a user who wants to understand what is in the corpus uses clustering. In advanced RAG systems, the outputs of clustering—labels, summaries, and cluster assignments—are themselves indexed and made retrievable, blurring the boundary between the two modes.

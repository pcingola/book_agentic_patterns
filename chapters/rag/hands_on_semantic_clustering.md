## Hands-On: Semantic Clustering

This hands-on demonstrates how to cluster an existing vector database collection by embedding similarity, label the resulting clusters with an LLM, and use the cluster structure to understand what a corpus contains. The example uses `example_RAG_04_clustering.ipynb`.

### What Clustering Reveals

Retrieval serves users who know what they are looking for. Clustering serves a different need: understanding what is in the corpus without a specific query. By grouping embeddings that are close in vector space, clustering reveals the dominant themes, the proportion of content each theme occupies, and the presence of peripheral or transitional material that does not fit cleanly into any theme.

This is useful before deploying a RAG system. If a corpus is supposed to cover ten topics but clustering reveals only three dense regions, the corpus is biased and retrieval will be unreliable for the underrepresented topics.

### Clustering an Existing Collection

After running the ingestion notebooks, the `books` collection already contains embeddings for all book chunks. The `cluster` function fetches those stored embeddings directly rather than re-embedding the documents:

```python
from agentic_patterns.core.vectordb import get_vector_db
from agentic_patterns.core.vectordb.clustering import cluster

vdb = get_vector_db("books")
result = cluster(vdb, algorithm="hdbscan")

print(f"Found {len(result.clusters)} clusters")
for c in result.clusters:
    print(f"  Cluster {c.cluster_id}: {len(c.items)} items")
```

When the input is a `VectorDB`, `cluster` fetches stored embeddings directly via the underlying collection and works on them without any additional embedding calls. This makes clustering an existing collection fast and free of API cost.

HDBSCAN does not require specifying the number of clusters. It finds dense regions in the embedding space and labels outlier points with cluster id `-1`. These noise points are intentional: some chunks are peripheral or transitional and should not be forced into a coherent theme. Forcing them in would dilute the coherent clusters.

### Labeling Clusters with an LLM

Raw clusters are groups of document IDs and texts with no human-readable description. `label_clusters` passes a sample of each cluster's items to a language model and asks it to assign a short label and a summary:

```python
from agentic_patterns.agents.rag.clustering import label_clusters

labeled = await label_clusters(result)

for c in labeled.clusters:
    if c.cluster_id == -1:
        continue  # Skip noise
    print(f"\nCluster {c.cluster_id}: {c.label}")
    print(f"  Summary: {c.summary}")
    print(f"  Items: {len(c.items)}")
```

The LLM receives up to 500 characters from each item's text, structured as a list, and returns a `label` like "Space travel and alien encounters" and a `summary` like "Passages describing interstellar journeys, first contact scenarios, and alien cultures." These labels make the clusters immediately interpretable without reading individual documents.

### Interpreting the Results

A typical run over the book corpus reveals clusters such as:

- Narrative scenes with specific characters and dialogue
- World-building and setting descriptions
- Technical explanations of fictional technology or science
- Philosophical reflections and inner monologue
- Transitional passages and plot exposition

This distribution reveals something about the corpus structure that a query-based approach would never show: the corpus is narrative-heavy with relatively few technical segments. A RAG system built on this corpus will be strong for character and plot queries but weak for factual lookups, because the factual content represents a small fraction of the chunks.

### Using K-Means When the Number of Clusters Is Known

For corpora where the expected number of topics is approximately known — for example, ten product categories in a support ticket corpus — k-means produces more balanced clusters:

```python
result_km = cluster(vdb, algorithm="kmeans", n_clusters=10)
labeled_km = await label_clusters(result_km)
```

K-means forces every document into a cluster, which is useful when the goal is complete coverage rather than noise rejection. The trade-off is that some clusters may be conceptually forced: groups that happen to be near each other in embedding space but do not represent a coherent theme. HDBSCAN's noise class provides an honest signal that k-means cannot.

### Mapping Clusters to Structured Items

A practical downstream use of clustering is mapping corpus themes to a predefined structure. Suppose the application has a set of evaluation criteria and wants to identify which criteria are well-represented in the corpus and which are absent. After labeling clusters, a simple comparison — either embedding-based similarity or LLM-based matching — can assign each cluster to the most relevant criterion:

```python
criteria = [
    "Ethical decision-making",
    "Resource management under constraints",
    "Communication with unknown entities",
]

for c in labeled.clusters:
    if c.cluster_id == -1:
        continue
    # Embed the cluster label and compare against criteria embeddings
    best_match = find_closest_criterion(c.label, criteria)
    print(f"{c.label} -> {best_match}")
```

This mapping reveals coverage gaps: criteria with no matching cluster are absent from the corpus, suggesting the document set is incomplete or biased. In a rubric-based evaluation system, this analysis directly informs which evidence sources need to be supplemented.

### Cluster Labels as a Navigation Layer

The final step in the notebook indexes the cluster labels themselves into a separate collection, creating a navigational layer over the corpus:

```python
from agentic_patterns.core.vectordb import get_vector_db
from agentic_patterns.core.vectordb.models import Chunk, ChunkLevel

vdb_index = get_vector_db("books_cluster_index")

index_chunks = []
for c in labeled.clusters:
    if c.cluster_id == -1:
        continue
    doc_ids = ",".join(item.doc_id for item in c.items)
    index_chunks.append(Chunk(
        doc_id=f"cluster-{c.cluster_id}",
        text=f"{c.label}: {c.summary}",
        level=ChunkLevel.DOCUMENT,
        parent_id=None,
        metadata={"cluster_id": c.cluster_id, "doc_ids": doc_ids},
    ))

vdb_index.ingest(index_chunks, force=True)
```

A user query first searches the cluster index to identify the most relevant theme, then retrieves chunks from only that cluster's documents. This two-stage retrieval reduces noise from irrelevant topics and can substantially improve precision for topically focused queries.

### Connection to the Chapter

Clustering and retrieval are complementary strategies over the same embedding space. Retrieval uses the space to answer a specific question; clustering uses the same space to map the territory. The `ClusterResult` returned by `cluster` and enriched by `label_clusters` is a reusable data structure: its labels can feed downstream filtering, its summaries can seed a navigational index, and its noise points identify documents that may need better chunking or categorization.

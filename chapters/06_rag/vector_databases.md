## Vector Databases

Vector databases are specialized data systems designed to store high-dimensional vectors and efficiently retrieve the most similar vectors to a given query.

### Historical perspective

The foundations of vector databases lie in decades of research on similarity search and nearest-neighbor problems in information retrieval and computational geometry. Early work in the 1970s and 1980s focused on exact nearest-neighbor search in low-dimensional metric spaces, but these approaches did not scale to high dimensions. As datasets grew and feature representations became more complex, research shifted toward *approximate nearest neighbor* (ANN) methods, trading exactness for dramatic gains in speed and memory efficiency.

In the late 1990s and 2000s, algorithms such as KD-trees, ball trees, and locality-sensitive hashing (LSH) emerged as practical approximations. However, the modern resurgence of vector search was driven by machine learning and deep learning, where embeddings routinely live in hundreds or thousands of dimensions. Systems like **FAISS** (2017) and later dedicated vector databases such as **Milvus** formalized these ideas into production-ready infrastructure, making vector search a core primitive for recommender systems, semantic search, and eventually Retrieval-Augmented Generation (RAG).

### How vector databases work

At a conceptual level, a vector database manages three tightly coupled concerns: storage, indexing, and similarity search. Each document, chunk, or entity is represented as a numerical vector produced by an embedding model. These vectors are stored alongside identifiers and optional metadata, but the primary operation is not key-value lookup—it is similarity search.

When a query arrives, it is first embedded into the same vector space. The database then searches for vectors that are “close” to the query vector under a chosen similarity metric. Because naïvely comparing the query to every stored vector is prohibitively expensive at scale, vector databases rely on specialized indexes that dramatically reduce the search space while preserving good recall.

In practice, a vector database behaves less like a traditional relational database and more like a search engine optimized for continuous spaces. Insertions update both raw storage and index structures; queries traverse those indexes to produce a ranked list of candidate vectors, often combined with metadata filtering before final results are returned.

### Similarity metrics

Similarity metrics define what it means for two vectors to be “close.” The choice of metric is not incidental; it encodes assumptions about how embeddings were trained and how magnitude and direction should be interpreted.

Cosine similarity measures the angle between vectors and is invariant to vector length. It is commonly used when embeddings are normalized and direction encodes semantics. Dot product is closely related and often preferred in dense retrieval models trained with inner-product objectives. Euclidean distance measures absolute geometric distance and is natural when vector magnitudes are meaningful.

Most vector databases treat the metric as a first-class configuration, because index structures and optimizations may depend on it. A mismatch between embedding model and similarity metric can significantly degrade retrieval quality, even if the infrastructure itself is functioning correctly.

### Indexing strategies

Indexing is the defining feature that distinguishes a vector database from a simple vector store. An index organizes vectors so that nearest-neighbor queries can be answered efficiently without exhaustive comparison.

Tree-based structures, such as KD-trees or ball trees, recursively partition the space and work well in low to moderate dimensions, but they degrade rapidly as dimensionality increases. Hash-based methods, particularly locality-sensitive hashing, map nearby vectors to the same buckets with high probability, enabling fast candidate generation at the cost of approximate results.

Graph-based indexes represent vectors as nodes in a graph, with edges connecting nearby neighbors. During search, the algorithm navigates the graph starting from an entry point and greedily moves toward vectors that are closer to the query. These structures scale well to high dimensions and large datasets and are widely used in modern systems.

Quantization-based approaches compress vectors into more compact representations, reducing memory footprint and improving cache efficiency. While quantization introduces approximation error, it often yields favorable trade-offs for large-scale deployments.

### Core vector database algorithms

Most production vector databases rely on a small family of ANN algorithms, often combined or layered for better performance. Hierarchical Navigable Small World (HNSW) graphs build multi-layer proximity graphs that enable logarithmic-like search behavior in practice. Inverted file (IVF) indexes first cluster vectors and then search only within the most relevant clusters. Product quantization (PQ) decomposes vectors into subspaces and encodes them compactly, enabling fast distance estimation.

These algorithms are rarely used in isolation. A common pattern is coarse partitioning (such as IVF) followed by graph-based or quantized search within partitions. The database exposes high-level configuration knobs—index type, efSearch, nprobe, recall targets—but internally orchestrates multiple algorithmic stages to balance latency, recall, and memory usage.

### Vector databases in RAG systems

In a RAG architecture, the vector database acts as the semantic memory layer. Document chunks are embedded and indexed once during ingestion, while user queries are embedded and searched at runtime. The quality of retrieval depends jointly on embedding quality, similarity metric, index choice, and search parameters. As a result, vector databases are not passive storage components but active participants in the behavior of the overall system.

Tuning a RAG system often involves iterative adjustments to vector database configuration: choosing an index that matches data scale, increasing recall at the expense of latency, or combining vector search with metadata filters to enforce structural constraints. Understanding how vector databases work internally is therefore essential for diagnosing retrieval failures and for designing robust, scalable RAG pipelines.


## Core Vector Database Algorithms

Vector databases are fundamentally concerned with solving the *nearest neighbor search* problem in high-dimensional continuous spaces. The practical design of these systems is best understood by starting from the formal problem definition and then examining how successive algorithmic relaxations make large-scale retrieval tractable.

### Formal problem definition

Let
$$
\mathcal{X} = \{x_1, x_2, \dots, x_n\}, \quad x_i \in \mathbb{R}^d
$$
be a collection of vectors embedded in a $d$-dimensional space, and let
$$
q \in \mathbb{R}^d
$$
be a query vector. Given a distance function $\delta(\cdot, \cdot)$, the *exact nearest neighbor* problem is defined as
$$
\operatorname{NN}(q) = \arg\min_{x_i \in \mathcal{X}} \delta(q, x_i)
$$

For cosine similarity, this becomes
$$
\operatorname{NN}(q) = \arg\max_{x_i \in \mathcal{X}} \frac{q \cdot x_i}{|q| |x_i|}
$$

A brute-force solution requires $O(nd)$ operations per query, which is computationally infeasible for large $n$. The central challenge addressed by vector database algorithms is to reduce this complexity while preserving ranking quality.

### High-dimensional effects and approximation

As dimensionality increases, distances between points concentrate. For many distributions, the ratio
$$
\frac{\min_i \delta(q, x_i)}{\max_i \delta(q, x_i)} \rightarrow 1 \quad \text{as } d \rightarrow \infty
$$

This phenomenon undermines exact pruning strategies and motivates *Approximate Nearest Neighbor (ANN)* search. ANN replaces the exact objective with a relaxed one:
$$
\delta(q, \hat{x}) \le (1 + \varepsilon) \cdot \delta(q, x^*)
$$
where $x^*$ is the true nearest neighbor.

All modern vector database algorithms can be understood as structured approximations to this relaxed objective.

---

## Partition-based search: Inverted File Index (IVF)

The inverted file index reduces search complexity by introducing a *coarse quantization* of the vector space. Let
$$
C = \{c_1, \dots, c_k\}
$$
be a set of centroids obtained via k-means clustering:
$$
C = \arg\min_{C} \sum_{i=1}^{n} \min_{c_j \in C} |x_i - c_j|^2
$$

Each vector is assigned to its closest centroid:
$$
\text{bucket}(x_i) = \arg\min_{c_j \in C} |x_i - c_j|
$$

At query time, the search proceeds in two stages. First, the query is compared against all centroids:
$$
d_j = |q - c_j|
$$
Then, only the vectors stored in the $n_{\text{probe}}$ closest buckets are searched exhaustively.

#### IVF query algorithm (pseudo-code)

```
function IVF_SEARCH(query q, centroids C, buckets B, n_probe):
    distances = compute_distance(q, C)
    selected = argmin_n(distances, n_probe)
    candidates = union(B[c] for c in selected)
    return top_k_by_distance(q, candidates)
```

This reduces query complexity to approximately
$$
O(kd + \frac{n}{k} \cdot n_{\text{probe}} \cdot d)
$$
which is sublinear in $n$ for reasonable values of $k$ and $n_{\text{probe}}$.

---

## Vector compression: Product Quantization (PQ)

Product Quantization further reduces computational and memory costs by compressing vectors. The original space $\mathbb{R}^d$ is decomposed into $m$ disjoint subspaces:
$$
x = (x^{(1)}, x^{(2)}, \dots, x^{(m)})
$$

Each subspace is quantized independently using a codebook:
$$
Q_j : \mathbb{R}^{d/m} \rightarrow \{1, \dots, k\}
$$

A vector is encoded as a sequence of discrete codes:
$$
\text{PQ}(x) = (Q_1(x^{(1)}), \dots, Q_m(x^{(m)}))
$$

Distance computation uses *asymmetric distance estimation*:
$$
\delta(q, x) \approx \sum_{j=1}^{m} | q^{(j)} - c_{Q_j(x)}^{(j)} |^2
$$

#### PQ distance computation (pseudo-code)

```
function PQ_DISTANCE(query q, codes c, lookup_tables T):
    dist = 0
    for j in 1..m:
        dist += T[j][c[j]]
    return dist
```

Theoretical justification comes from rate–distortion theory: PQ minimizes expected reconstruction error under constrained bit budgets. Empirically, it preserves relative ordering sufficiently well for ranking-based retrieval.

---

## Hash-based search: Locality-Sensitive Hashing (LSH)

Locality-Sensitive Hashing constructs hash functions $h \in \mathcal{H}$ such that
$$
\Pr[h(x) = h(y)] = f(\delta(x, y))
$$
where $f$ decreases monotonically with distance.

For Euclidean distance, a common family is
$$
h_{a,b}(x) = \left\lfloor \frac{a \cdot x + b}{w} \right\rfloor
$$
with random $a \sim \mathcal{N}(0, I)$ and $b \sim U(0, w)$.

By concatenating hashes and using multiple tables, LSH achieves expected query complexity
$$
O(n^\rho), \quad \rho < 1
$$

Despite strong theoretical guarantees, LSH often underperforms graph-based methods in dense embedding spaces typical of neural models.

---

## Graph-based search: Navigable small-world graphs and HNSW

Graph-based methods model the dataset as a proximity graph $G = (V, E)$, where each node corresponds to a vector. Search proceeds via greedy graph traversal:
$$
x_{t+1} = \arg\min_{y \in \mathcal{N}(x_t)} \delta(q, y)
$$

Hierarchical Navigable Small World (HNSW) graphs extend this idea by constructing multiple graph layers. Each vector is assigned a maximum level:
$$
\ell \sim \text{Geometric}(p)
$$

Upper layers are sparse and provide long-range connections, while lower layers are dense and preserve local neighborhoods.

#### HNSW search algorithm (simplified)

```
function HNSW_SEARCH(query q, entry e, graph G):
    current = e
    for level from max_level down to 1:
        current = greedy_search(q, current, G[level])
    return best_neighbors(q, current, G[0])
```

Theoretical intuition comes from small-world graph theory: the presence of long-range links reduces graph diameter, while local edges enable precise refinement. Expected search complexity is close to $O(\log n)$, with high recall even in large, high-dimensional datasets.

---

## Algorithmic composition in vector databases

In practice, vector databases compose these algorithms hierarchically. A typical pipeline applies IVF to reduce the candidate set, PQ to compress vectors and accelerate distance computation, and graph-based search to refine nearest neighbors. Each stage introduces controlled approximation while drastically reducing computational cost.

This layered structure mirrors the mathematical decomposition of the nearest neighbor problem: spatial restriction, metric approximation, and navigational optimization.

---

## Implications for RAG systems

In Retrieval-Augmented Generation, these algorithms define the semantic recall boundary of the system. Errors in retrieval are often consequences of approximation layers rather than embedding quality. Understanding the mathematical and algorithmic foundations of vector databases is therefore essential for diagnosing failure modes, tuning recall–latency trade-offs, and designing reliable RAG pipelines.

Vector databases should thus be viewed not as storage engines, but as algorithmic systems grounded in decades of research on high-dimensional geometry, probabilistic approximation, and graph navigation.

---

## References

1. Indyk, P., Motwani, R. *Approximate Nearest Neighbors: Towards Removing the Curse of Dimensionality*. STOC, 1998.
2. Jégou, H., Douze, M., Schmid, C. *Product Quantization for Nearest Neighbor Search*. IEEE TPAMI, 2011.
3. Johnson, J., Douze, M., Jégou, H. *Billion-scale similarity search with GPUs*. IEEE Transactions on Big Data, 2019.
4. Malkov, Y., Yashunin, D. *Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs*. IEEE TPAMI, 2020.
5. Andoni, A., Indyk, P. *Near-optimal hashing algorithms for approximate nearest neighbor in high dimensions*. FOCS, 2006.
6. Indyk, P., Motwani, R. *Approximate Nearest Neighbors: Towards Removing the Curse of Dimensionality*. STOC, 1998.
7. Johnson, J., Douze, M., Jégou, H. *Billion-scale similarity search with GPUs*. IEEE Transactions on Big Data, 2019.
8. Malkov, Y., Yashunin, D. *Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs*. IEEE TPAMI, 2020.
9. Jégou, H., Douze, M., Schmid, C. *Product Quantization for Nearest Neighbor Search*. IEEE TPAMI, 2011.
10. [https://ai.pydantic.dev/](https://ai.pydantic.dev/)



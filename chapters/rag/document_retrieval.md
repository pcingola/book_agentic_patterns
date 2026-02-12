## Document Retrieval

Document retrieval is the stage in a RAG system that transforms a user query into a ranked, filtered set of candidate documents or passages that are most likely to support a correct answer.

### Conceptual overview of document retrieval

In a RAG system, document retrieval is not a single operation but a pipeline. A raw user query is progressively transformed, evaluated, and constrained until a small, high-quality context set is produced. Each stage trades recall for precision, with early stages favoring breadth and later stages favoring accuracy and relevance.

At a high level, the retrieval process consists of query interpretation and rewriting, candidate generation, scoring, re-ranking, filtering, and combination with structured constraints. While these stages can be collapsed in small systems, large-scale RAG deployments almost always implement them explicitly to control cost, latency, and quality.

### Query interpretation and rewriting

User queries are often underspecified, ambiguous, or conversational. Before retrieval, the system may rewrite the query into one or more canonical forms that are better aligned with the indexed representation of documents. This includes expanding abbreviations, resolving coreferences, normalizing terminology, or decomposing a complex question into multiple sub-queries.

In neural systems, query rewriting is frequently performed by a language model that produces a more retrieval-friendly query while preserving intent. Importantly, rewriting does not aim to answer the question, but to maximize the likelihood that relevant documents are retrieved.

```python
# Pseudocode for query rewriting
rewritten_query = rewrite_model.generate(
    original_query,
    objective="maximize retrievability"
)
```

Multiple rewritten queries may be generated to increase recall, with their results merged downstream.

### Candidate generation

Candidate generation is the first retrieval pass over the corpus. Its purpose is to retrieve a relatively large set of potentially relevant documents with high recall and low computational cost. This stage commonly uses either sparse retrieval (e.g., inverted indexes with BM25), dense vector search over embeddings, or both.

Dense retrieval maps the rewritten query into the same embedding space as documents and retrieves nearest neighbors under a similarity metric. At this stage, approximate nearest neighbor algorithms are typically used to ensure scalability.

```python
# Dense candidate generation
query_vector = embed(rewritten_query)
candidates = vector_index.search(
    query_vector,
    top_k=K_large
)
```

The output of this stage is intentionally noisy. Precision is improved later.

### Scoring and initial ranking

Each candidate document is assigned a relevance score with respect to the query. In simple systems, this score may be the similarity returned by the vector database or the BM25 score. In more advanced systems, multiple signals are combined, such as dense similarity, sparse similarity, document freshness, or domain-specific heuristics.

Formally, scoring can be expressed as a function
$s(d, q) \rightarrow \mathbb{R}$,
where $d$ is a document and $q$ is the rewritten query. At this stage, the goal is to produce a reasonably ordered list, not a final ranking.

### Re-ranking with cross-encoders or task-aware models

Re-ranking refines the initial ranking using more expensive but more accurate models. Instead of independently embedding queries and documents, re-rankers jointly encode the query–document pair, allowing fine-grained interaction between their tokens. This substantially improves precision, especially at the top of the ranking.

Because re-ranking is computationally expensive, it is applied only to a small subset of top candidates from the previous stage.

```python
# Re-ranking stage
top_candidates = candidates[:K_small]
reranked = reranker.score_pairs(
    query=rewritten_query,
    documents=top_candidates
)
```

The result is a high-precision ordering optimized for downstream generation rather than generic relevance.

### Filtering and constraints

Filtering removes candidates that are irrelevant or invalid given explicit constraints. These constraints often come from metadata, such as document type, access permissions, time ranges, language, or domain tags. Filtering can be applied before retrieval to reduce the search space, after retrieval to prune results, or at both stages.

In enterprise RAG systems, filtering is critical for correctness and safety. A highly relevant document that violates a constraint is worse than a less relevant but valid one.

```python
# Metadata-based filtering
filtered = [
    d for d in reranked
    if d.metadata["access_level"] <= user_access
]
```

### Combined strategies: metadata, SQL, and embeddings

Modern retrieval pipelines frequently combine symbolic and vector-based approaches. A common pattern is to use structured queries (e.g., SQL or metadata filters) to narrow the candidate set, followed by dense similarity search within that subset. This hybrid approach exploits the strengths of both paradigms: exactness and interpretability from structured filters, and semantic generalization from embeddings.

Conceptually, this corresponds to retrieving from a conditional distribution
$p(d \mid q, m)$,
where $m$ represents structured metadata constraints.

This combination is especially powerful in domains with rich schemas, such as scientific literature, enterprise knowledge bases, or regulatory documents.

### Retrieval as a system, not a single model

A key insight in modern RAG is that retrieval quality emerges from the interaction of stages rather than from any single algorithm. Query rewriting increases recall, candidate generation ensures coverage, scoring and re-ranking enforce relevance, and filtering guarantees validity. Treating retrieval as a modular pipeline allows systematic evaluation, targeted optimization, and controlled trade-offs between cost and quality.

### Putting it together: a simple RAG pipeline

In its simplest form, a RAG system can be described as a linear pipeline: ingest documents, retrieve relevant chunks, and generate an answer conditioned on them. The following pseudocode illustrates the core idea, omitting implementation details:

```python
# Offline ingestion
chunks = chunk_documents(documents)
vectors = embed(chunks)
index.store(vectors, metadata=chunks.metadata)

# Online query
query_vector = embed(query)
retrieved_chunks = index.search(query_vector, top_k=5)

# Generation
context = "\n".join(chunk.text for chunk in retrieved_chunks)
answer = llm.generate(
    prompt=f"Use the following context to answer the question:\n{context}\n\nQuestion: {query}"
)
```

Despite its simplicity, this pattern already delivers most of the benefits associated with RAG. The model is guided by retrieved evidence, answers can be traced back to source documents, and updating knowledge only requires re-ingesting data rather than retraining the model. More advanced systems extend this basic flow with richer chunking strategies, hybrid retrieval, iterative querying, and explicit evaluation loops, but the foundational pattern remains the same: retrieval first, generation second, with a clear boundary between the two.

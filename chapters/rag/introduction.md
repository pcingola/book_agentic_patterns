
**Retrieval-Augmented Generation (RAG)** is an architectural pattern that combines information retrieval systems with generative language models so that responses are grounded in external, up-to-date, and inspectable knowledge rather than relying solely on model parameters.

### Conceptual overview of RAG

At a high level, a RAG system treats external data as a first-class component of generation. Instead of asking a model to answer a question directly, the system first retrieves relevant information from a corpus, then conditions the model on that information when generating the final answer. The language model remains a reasoning and synthesis engine, while the retriever acts as a dynamic memory.

This separation introduces a clear information workflow with two main phases: **document ingestion** and **document retrieval**, followed by **generation**.

![Image](img/rag_overview.jpg)

![Image](img/rag_workflow.png)

![Image](img/semantic_search.png)

### Information workflow in RAG systems

#### Document ingestion

Document ingestion is the offline (or semi-offline) process that prepares raw data for efficient retrieval. It typically begins with collecting documents from sources such as filesystems, databases, APIs, or web crawls. These documents are then normalized into a common textual representation, which may involve parsing PDFs, stripping markup, or extracting structured fields.

Because language models have limited context windows, documents are usually divided into smaller units called "chunks". This chunking step aims to balance semantic coherence with retrievability: chunks should be large enough to preserve meaning, but small enough to be selectively retrieved. Each chunk is then transformed into a numerical representation, typically via embeddings that capture semantic similarity. The resulting vectors, along with metadata such as source, timestamps, or access permissions, are stored in an index optimized for similarity search.

Ingested data is therefore not just stored text, but a structured memory that supports efficient and meaningful retrieval.

#### Document retrieval

Document retrieval is the online phase, executed at query time. Given a user query or task description, the system first produces a query representation, often using the same embedding space as the documents. This representation is used to search the index and retrieve the most relevant chunks according to a similarity or scoring function.

Retrieval rarely ends at a single step. Results may be filtered using metadata constraints, re-ranked using more expensive scoring models, or combined with other retrieval strategies such as keyword search or structured database queries. The outcome is a small set of contextually relevant passages that can fit within the model’s context window.

These retrieved chunks form the factual grounding for the generation step, effectively acting as an external, query-specific memory.

### How a simple RAG works

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

Despite its simplicity, this pattern already delivers most of the benefits associated with RAG. The model is guided by retrieved evidence, answers can be traced back to source documents, and updating knowledge only requires re-ingesting data rather than retraining the model.

More advanced systems extend this basic flow with richer chunking strategies, hybrid retrieval, iterative querying, and explicit evaluation loops, but the foundational pattern remains the same: retrieval first, generation second, with a clear boundary between the two.

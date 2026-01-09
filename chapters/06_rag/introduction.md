## RAG: Introduction

**Retrieval-Augmented Generation (RAG)** is an architectural pattern that combines information retrieval systems with generative language models so that responses are grounded in external, up-to-date, and inspectable knowledge rather than relying solely on model parameters.

### Historical perspective

The core idea behind RAG predates modern large language models and can be traced back to classical information retrieval and question answering systems from the 1990s and early 2000s, where a retriever selected relevant documents and a separate component synthesized an answer. Early open-domain QA systems combined search engines with symbolic or statistical answer extractors, highlighting the separation between *finding information* and *using it*.

With the rise of neural language models, research shifted toward integrating retrieval more tightly with generation. Dense retrieval methods, such as neural embeddings for semantic search, emerged in the late 2010s and enabled retrieval beyond keyword matching. This line of work culminated in explicit Retrieval-Augmented Generation formulations around 2020, where retrieved documents were injected into the model’s context to guide generation. The motivation was twofold: reduce hallucinations by grounding outputs in real documents, and decouple knowledge updates from expensive model retraining.

### Conceptual overview of RAG

At a high level, a RAG system treats external data as a first-class component of generation. Instead of asking a model to answer a question directly, the system first retrieves relevant information from a corpus, then conditions the model on that information when generating the final answer. The language model remains a reasoning and synthesis engine, while the retriever acts as a dynamic memory.

This separation introduces a clear information workflow with two main phases: **document ingestion** and **document retrieval**, followed by **generation**.

![Image](https://www.solulab.com/wp-content/uploads/2024/07/Retrieval-Augmented-Generation-2-1024x569.jpg)

![Image](https://media.licdn.com/dms/image/v2/D4D12AQGfhRsQs5s4lA/article-inline_image-shrink_1000_1488/article-inline_image-shrink_1000_1488/0/1728125633128?e=2147483647\&t=Bj2Ev3UUFRmn5Jio99rQn2L95xJCQ8n6lWoz6HeGXto\&v=beta)

![Image](https://media.geeksforgeeks.org/wp-content/uploads/20250620114121537025/Semantic-Search-using-VectorDB.webp)

### Information workflow in RAG systems

#### Document ingestion

Document ingestion is the offline (or semi-offline) process that prepares raw data for efficient retrieval. It typically begins with collecting documents from sources such as filesystems, databases, APIs, or web crawls. These documents are then normalized into a common textual representation, which may involve parsing PDFs, stripping markup, or extracting structured fields.

Because language models have limited context windows, documents are usually divided into smaller units. This chunking step aims to balance semantic coherence with retrievability: chunks should be large enough to preserve meaning, but small enough to be selectively retrieved. Each chunk is then transformed into a numerical representation, typically via embeddings that capture semantic similarity. The resulting vectors, along with metadata such as source, timestamps, or access permissions, are stored in an index optimized for similarity search.

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

### References

1. Lewis, P. et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS, 2020. [https://arxiv.org/abs/2005.11401](https://arxiv.org/abs/2005.11401)
2. Karpukhin, V. et al. *Dense Passage Retrieval for Open-Domain Question Answering*. EMNLP, 2020. [https://arxiv.org/abs/2004.04906](https://arxiv.org/abs/2004.04906)
3. Chen, D. et al. *Reading Wikipedia to Answer Open-Domain Questions*. ACL, 2017. [https://arxiv.org/abs/1704.00051](https://arxiv.org/abs/1704.00051)
4. Izacard, G., Grave, E. *Leveraging Passage Retrieval with Generative Models for Open Domain Question Answering*. EACL, 2021. [https://arxiv.org/abs/2007.01282](https://arxiv.org/abs/2007.01282)

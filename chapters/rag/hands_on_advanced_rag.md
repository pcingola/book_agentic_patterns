## Hands-On: Advanced Document Ingestion and Retrieval

This hands-on explores techniques that improve upon the basic RAG pipeline: semantic chunking during ingestion and multi-stage retrieval with query expansion, filtering, and re-ranking. The examples use `example_RAG_02_load.ipynb` for LLM-based chunking and `example_RAG_02_query.ipynb` for advanced retrieval.

### Why Go Beyond Simple RAG

The simple paragraph-based chunking from the previous example works well when document structure aligns with semantic boundaries. But real documents often violate this assumption. A conversation might span multiple paragraphs. A technical explanation might flow continuously without clear breaks. Naive chunking splits these coherent units, forcing the retriever to find multiple partial chunks that together contain the answer.

Similarly, simple retrieval assumes the user's query directly matches how information is expressed in the documents. In practice, users ask questions in many ways, and a single embedding might miss relevant passages that use different terminology. The advanced retrieval techniques address these limitations by expanding queries, filtering results, and re-ranking for precision.

### Part 1: LLM-Based Semantic Chunking

The ingestion notebook (`example_RAG_02_load.ipynb`) replaces naive paragraph splitting with an LLM that identifies semantic boundaries.

#### Chunking with chunk_with_llm

The `chunk_with_llm` function in `agents/rag/chunking.py` handles the full ingestion pipeline: batching the text, prompting the LLM to identify topic boundaries, and managing the leftover strategy across batch edges.

```python
from agentic_patterns.core.doc_ingestion.models import DocumentProvenance
from agentic_patterns.agents.rag.chunking import chunk_with_llm
from agentic_patterns.core.vectordb import get_vector_db

vdb = get_vector_db('books_semantic')

for txt_file in DOCS_DIR.glob('*.txt'):
    text = txt_file.read_text()
    provenance = DocumentProvenance(original_file=txt_file, source=txt_file.stem)
    chunks = await chunk_with_llm(text, provenance, batch_size=15000)
    added = vdb.ingest(chunks, force=False)
    print(f"{txt_file.name}: {added} semantic chunks added")
```

`chunk_with_llm` splits the text into batches at paragraph boundaries so that no single batch exceeds the LLM's practical context limit. It prompts the LLM to identify where topics or scenes change within each batch, returning a list of coherent text segments. Each chunk comes back at `ChunkLevel.SECTION` — one level coarser than the paragraph-level chunks produced by `chunk_by_paragraphs`.

#### Handling Incomplete Chunks Across Batches

The key challenge with batching is that a semantic unit might straddle a batch boundary. `chunk_with_llm` addresses this with a leftover strategy: the last chunk of each batch is treated as potentially incomplete and is prepended to the next batch. The LLM then sees that fragment with sufficient following context to determine where the topic actually ends.

This approach maintains coherence across arbitrary batch boundaries without requiring the LLM to see the entire document at once. The prompt instructs the LLM to place potentially incomplete content last, which makes the detection reliable: the final element of each batch response is always the candidate for continuation.

#### Why Semantic Chunking Matters

Unlike heuristic approaches that count characters or split on punctuation, the LLM understands when a scene changes or a new concept begins. Two ideas that happen to share a paragraph boundary will be separated; a single paragraph that covers two distinct topics will be split. The resulting chunks are more semantically self-contained, which directly improves retrieval precision because each embedding represents one coherent idea.

The trade-off is cost and latency. LLM chunking requires one or more API calls per document at ingestion time. For small corpora this is acceptable; for very large corpora, the markdown-aware `chunk_by_markdown` chunker provides a cheaper approximation that still respects heading structure.

### Part 2: Advanced Retrieval

The retrieval notebook (`example_RAG_02_query.ipynb`) demonstrates a multi-stage pipeline that improves upon direct similarity search.

#### Query Expansion

A single query embedding might miss relevant documents that express the same concept differently. `expand_query` reformulates the user's question into multiple variants:

```python
from agentic_patterns.agents.rag.retrieval import expand_query

query = "Who is a man with two heads?"
queries = await expand_query(query)
# e.g. ["character described as having two heads",
#        "dual-headed individual in the story",
#        "person with two heads description", ...]
```

For a question like "Who is a man with two heads?", the LLM might generate variations like "character with multiple heads", "dual-headed individual", and "person with two heads description". Each reformulation captures a different lexical angle on the same semantic intent. Querying with all variations increases recall because documents matching any phrasing will be retrieved.

#### Multi-Query Retrieval with Metadata Filtering

Each reformulated query runs against the vector database with an optional metadata filter applied at query time:

```python
from agentic_patterns.core.vectordb import get_vector_db

vdb = get_vector_db('books_semantic')
book_name = 'hhgttg'

all_results = []
for q in queries:
    all_results.extend(vdb.retrieve(q, filter={'source': book_name}, max_results=10))
```

The `filter` parameter restricts results at the database level, which is more efficient than filtering after retrieval. In production systems, metadata filtering handles access control (only documents the user is authorized to see), temporal constraints (only documents from a certain time period), or domain restrictions (only documents from a particular category).

The same document might appear multiple times because it matches several reformulations. This duplication is handled in the next step.

#### Deduplication and Re-ranking

`vdb.retrieve` already deduplicates within a single query. Across multiple queries, we deduplicate by `doc_id`, keeping the highest score, then sort:

```python
seen: dict[str, RetrievedDocument] = {}
for doc in all_results:
    if doc.doc_id not in seen or doc.score > seen[doc.doc_id].score:
        seen[doc.doc_id] = doc

top_results = sorted(seen.values(), key=lambda d: d.score, reverse=True)[:10]
```

This score-based sort provides a simple re-ranking baseline. Production systems often use cross-encoder models that jointly encode the query and document to produce more accurate relevance scores. Cross-encoders are too slow for an initial search over thousands of documents, but work well for re-ranking a small candidate set of ten to twenty documents.

The `max_results` limit caps how many documents enter the final prompt. More documents provide more context but increase token usage and may dilute the most relevant passages.

#### Building the Final Prompt

The filtered, deduplicated, sorted documents become context for the LLM:

```python
docs_str = ''
for doc in top_results:
    docs_str += f"Similarity Score: {doc.score:.3f}\nDocument ID: {doc.doc_id}\nDocument:\n{doc.text}\n\n"

prompt = f"""
Given the following documents, answer the user's question.
Show used references (using document ids).

## Documents

{docs_str}

## User's question

{query}
"""
```

Including document IDs enables citation. The LLM can reference specific documents in its answer, allowing users to trace claims back to sources. This transparency is valuable in applications where users need to verify the LLM's reasoning.

### The Cost-Quality Tradeoff

The advanced techniques in this hands-on improve retrieval quality but increase cost and latency. LLM-based chunking requires one or more LLM calls per document during ingestion. Query expansion adds an LLM call per query. These costs should be weighed against the improvement in retrieval quality for your specific use case.

For small corpora with well-structured documents, simple paragraph chunking and direct retrieval may suffice. For large, heterogeneous corpora where retrieval precision matters, the investment in semantic chunking and multi-stage retrieval pays off in better answers.

### Connection to the Chapter

The techniques demonstrated here correspond to concepts from the chapter sections on document ingestion and retrieval. `chunk_with_llm` implements the topic-aware segmentation described in the ingestion section. `expand_query`, metadata filtering, and score-based re-ranking implement stages of the retrieval pipeline described in the retrieval section. The code makes these abstract concepts concrete and runnable.

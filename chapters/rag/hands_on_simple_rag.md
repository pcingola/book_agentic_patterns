## Hands-On: Simple Document Ingestion and Retrieval

This hands-on walks through the fundamental RAG pipeline: ingesting documents into a vector database and retrieving relevant passages to augment LLM prompts. The examples use `example_RAG_01_load.ipynb` for ingestion and `example_RAG_01_query.ipynb` for retrieval.

### The RAG Pipeline

RAG systems operate in two distinct phases. The ingestion phase transforms raw documents into searchable embeddings stored in a vector database. This happens once, or whenever the corpus changes. The retrieval phase takes a user query, finds semantically similar documents, and uses them to ground the LLM's response. This happens on every query.

The separation matters because ingestion is expensive (embedding all documents) while retrieval is cheap (embedding one query and looking up neighbors). A well-designed RAG system invests heavily in ingestion quality because that investment pays off across all subsequent queries.

### Part 1: Document Ingestion

The ingestion notebook (`example_RAG_01_load.ipynb`) demonstrates the three core steps: loading documents, chunking them, and storing the chunks as embeddings.

#### Setting Up the Vector Database

The notebook begins by creating a connection to a Chroma vector database:

```python
from agentic_patterns.core.vectordb import get_vector_db

vdb = get_vector_db('books')
```

The `get_vector_db` function handles database initialization and configuration. The collection name `'books'` identifies this particular set of documents. Chroma persists the data to disk, so the database survives across notebook sessions.

#### Chunking Strategy

`ChunkerParagraph` splits a document at blank lines and filters out blocks that are too short:

```python
from pathlib import Path
from agentic_patterns.core.vectordb import ChunkerParagraph
from agentic_patterns.core.doc_ingestion.models import DocumentProvenance

txt_file = Path("data/books/hhgttg.txt")
text = txt_file.read_text()
provenance = DocumentProvenance(original_file=txt_file, source=txt_file.stem)
chunker = ChunkerParagraph(min_lines=3)
chunks = chunker.chunk(text, provenance)
```

This is the simplest useful chunking strategy: split on double newlines (paragraph boundaries) and discard blocks shorter than `min_lines`. Each `Chunk` object carries a unique `doc_id` derived from the filename and paragraph position, a `level` of `ChunkLevel.PARAGRAPH`, and a `metadata` dict containing the provenance fields. The provenance captures the source filename so that retrieved passages can be traced back to their origin.

The `min_lines` filter removes trivial blocks like chapter headings or blank sections. Without it, the vector database fills with short, semantically weak chunks that add noise to retrieval results.

All chunkers implement the `Chunker` ABC, which defines a single `chunk(text, provenance)` method (plus an async `achunk` variant). The library provides several built-in chunkers: `ChunkerParagraph` for simple paragraph splitting, `ChunkerMarkdown` for heading-aware splitting, `ChunkerSmart` which auto-selects a strategy based on document size and structure, and `ChunkerLLM` for LLM-based semantic chunking.

#### Loading Documents

`vdb.ingest` stores the chunks as embeddings in the vector database:

```python
chunker = ChunkerParagraph(min_lines=3)
for txt_file in DOCS_DIR.glob('*.txt'):
    text = txt_file.read_text()
    provenance = DocumentProvenance(original_file=txt_file, source=txt_file.stem)
    chunks = chunker.chunk(text, provenance)
    added = vdb.ingest(chunks, force=False)
    print(f"{txt_file.name}: {added} chunks added")
```

`ingest` embeds and stores each chunk and returns the count actually added. The `force=False` argument skips chunks whose `doc_id` already exists in the collection, making ingestion idempotent. Rerunning the notebook does not create duplicate entries.

### Part 2: Document Retrieval

The retrieval notebook (`example_RAG_01_query.ipynb`) demonstrates querying the vector database and using retrieved documents to augment an LLM prompt.

#### Querying the Vector Database

The query process starts by embedding the user's question and finding similar documents:

```python
from agentic_patterns.core.vectordb import get_vector_db

vdb = get_vector_db('books')
query = "Who is a man with two heads?"
results = vdb.retrieve(query=query, max_results=5)
```

`vdb.retrieve` converts the query string to an embedding using the same model that embedded the documents, performs a similarity search, deduplicates by `doc_id` (keeping the highest score per document), and returns results sorted by descending score. Each result is a `RetrievedDocument` with `.text`, `.score`, `.doc_id`, `.level`, `.parent_id`, and `.metadata` attributes.

#### Building the Augmented Prompt

The retrieved documents become part of the LLM prompt:

```python
docs_str = ''
for doc in results:
    docs_str += f"Similarity Score: {doc.score:.3f}\nDocument:\n{doc.text}\n\n"

prompt = f"""
Given the following documents, answer the question:

{docs_str}

Question:
{query}
"""
```

This prompt structure is the essence of RAG. Instead of asking the LLM to answer from its training data alone, we provide specific documents that should contain the answer. The LLM's job shifts from recall to comprehension: it reads the provided documents and synthesizes an answer.

Including the similarity score in the prompt is optional but can help the LLM weight its confidence. A document with score 0.95 is a strong match; one with score 0.60 might be tangentially relevant.

#### Generating the Answer

The augmented prompt goes to the LLM:

```python
from agentic_patterns.core.agents import get_agent, run_agent

agent = get_agent()
answer, nodes = await run_agent(agent, prompt=prompt, verbose=True)
```

The LLM now has access to relevant passages from the corpus. If the question asks about a character from a book, and the retrieved documents contain paragraphs describing that character, the LLM can answer accurately even if that information wasn't in its training data.

### Why This Pattern Works

The RAG pattern succeeds because it separates concerns. Embeddings capture semantic similarity without requiring exact keyword matches. Vector search scales to large corpora with sub-linear query time. LLMs excel at reading comprehension and synthesis but struggle with precise recall. By combining these components, RAG gets the best of each: broad semantic matching, efficient retrieval, and fluent answer generation.

The simple paragraph-based chunking works well for narrative text where paragraphs correspond to coherent units of meaning. For technical documentation, code, or structured data, more sophisticated chunking strategies (covered in later examples) may be needed.

### Limitations of Simple RAG

This basic implementation has several limitations that motivate the advanced techniques covered in subsequent examples.

The paragraph chunking is naive. It does not consider semantic boundaries, so a topic that spans two paragraphs gets split into separate chunks. A query might retrieve only half of the relevant context.

The retrieval uses a single query. If the user's question could be phrased multiple ways, the system might miss relevant documents that match an alternate phrasing. Query expansion addresses this.

There is no re-ranking. The initial similarity scores from the vector database are approximate. A dedicated re-ranker that jointly considers query-document pairs can improve precision, especially at the top of the ranking.

There is no metadata filtering. In a production system, you might want to restrict retrieval to documents from a specific time period, author, or category. The metadata is captured during ingestion but not used during retrieval in this basic example.

These limitations do not diminish the value of the simple approach. For many use cases, paragraph chunking and direct retrieval work well. The advanced techniques add complexity that should be justified by measured improvements in retrieval quality for your specific domain.

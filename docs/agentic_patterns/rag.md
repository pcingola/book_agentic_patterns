# RAG (Retrieval-Augmented Generation)

RAG lets agents ground their responses in external documents rather than relying solely on training data. The library provides a vector database module (`agentic_patterns.core.vectordb`) that handles embedding generation, storage, and similarity search via Chroma. You write the chunking and prompt assembly logic; the module handles everything from embedding text to querying for relevant passages.

## Configuration

Embedding and vector database settings live in `config.yaml` under `embeddings:` and `vectordb:` sections. Environment variables are expanded via `${VAR}` syntax.

```yaml
embeddings:
  default:
    provider: openai
    model_name: text-embedding-3-small
    api_key: ${OPENAI_API_KEY}
    dimensions: 1536

  local:
    provider: ollama
    model_name: nomic-embed-text
    url: http://localhost:11434

vectordb:
  default:
    backend: chroma
    persist_directory: data/vectordb
```

Supported embedding providers:

| Provider | Required fields | Notes |
|---|---|---|
| `openai` | `model_name` | Optional `api_key`, `dimensions` |
| `ollama` | `model_name` | Optional `url` (defaults to `http://localhost:11434`) |
| `sentence_transformers` | `model_name` | Optional `device` (defaults to `cpu`) |
| `openrouter` | `model_name` | Optional `api_key`, `api_url`, `dimensions` |

Supported vector database backends:

| Backend | Required fields |
|---|---|
| `chroma` | `persist_directory` |
| `pgvector` | `connection_string` |

Only Chroma is implemented. The `persist_directory` can be relative (resolved against the project root) or absolute.


## Embeddings

`get_embedder()` creates an embedder instance from configuration. It uses a singleton cache keyed by `provider:model_name`, so repeated calls with the same config return the same instance.

```python
from agentic_patterns.core.vectordb import get_embedder, embed_text, embed_texts

# Create from config.yaml "default" entry
embedder = get_embedder()

# Create from a named config
embedder = get_embedder("local")

# Embed a single text
vector = await embed_text("Hello world", embedder)
# Returns list[float]

# Embed multiple texts
vectors = await embed_texts(["Hello", "World"], embedder)
# Returns list[list[float]]
```

**Signature:**

```python
def get_embedder(
    config: EmbeddingConfig | str | None = None,
    config_path: Path | str | None = None,
) -> Embedder
```

The `config` parameter accepts a named config string (looked up in config.yaml), an `EmbeddingConfig` object directly, or `None` for the default. The optional `config_path` parameter specifies which YAML file to load settings from; when omitted it defaults to the project's `config.yaml`.

When no embedder is passed to `embed_text()` or `embed_texts()`, they create one from the default config automatically.


## Vector Database

### Creating a collection

`get_vector_db()` creates or retrieves a Chroma collection. It uses a singleton cache, so calling it twice with the same collection name returns the same collection.

```python
from agentic_patterns.core.vectordb import get_vector_db

vdb = get_vector_db("books")
```

The collection is persisted to disk. Data survives across process restarts. The embedding function is attached to the collection automatically -- you do not need to manage embeddings manually when adding or querying documents.

**Signature:**

```python
def get_vector_db(
    collection_name: str,
    embedding_config: str | None = None,
    vectordb_config: str | None = None,
    config_path: Path | str | None = None,
) -> VectorDB
```

`embedding_config` and `vectordb_config` select named entries from `config.yaml`. Both default to `"default"`. Returns a `VectorDB` instance wrapping a Chroma collection.


### Adding documents

```python
vdb.add(text="The answer is 42.", doc_id="doc-1", meta={"source": "guide"})
```

`add()` is idempotent by default -- if `doc_id` already exists, the call is a no-op and returns `None`. Pass `force=True` to overwrite. Metadata is optional but useful for filtering during retrieval.

**Signature:** `vdb.add(text, doc_id, meta=None, force=False) -> str | None`


### Querying

```python
results = vdb.query(query="What is the answer?")

for result in results:
    print(f"[{result.score:.3f}] {result.text[:80]}...")
```

Each result is a `RetrievedDocument` with fields: `doc_id`, `text`, `score`, `level` (`ChunkLevel`), `parent_id`, `metadata`. Scores are similarity values (higher is better), converted from Chroma's distance metric via `1.0 - distance`.

**Signature:** `vdb.query(query, filter=None, where_document=None, max_items=10, similarity_threshold=None) -> list[RetrievedDocument]`

| Parameter | Description |
|---|---|
| `filter` | Metadata filter applied at the database level (e.g., `{"source": "guide"}`) |
| `where_document` | Full-text filter on document content |
| `max_items` | Maximum number of results (default 10) |
| `similarity_threshold` | Drop results below this score |


### Higher-level retrieval

`vdb.retrieve(query, max_results=10, filter=None, level=None)` queries with deduplication and optional chunk-level filtering. Use `level=ChunkLevel.SECTION` to restrict to a specific chunk granularity.

`vdb.fetch_parent(doc)` fetches the parent chunk by following `parent_id` for context widening.

### Ingestion

`vdb.ingest(chunks, force=False)` stores a list of `Chunk` objects. Returns count of added chunks.

`vdb.ingest_file(file, provenance, pipeline="standard", force=False)` loads a file (PDF, DOCX, PPTX, HTML, markdown), chunks it, and stores in the collection.

### Lookup and existence check

```python
exists = vdb.has("doc-1")
record = vdb.get_by_id("doc-1")
count = vdb.count()
```

`vdb.collection` provides direct access to the underlying Chroma collection as an escape hatch.


## The RAG Pattern

The typical workflow has two phases.

**Ingestion** (run once or when the corpus changes): load documents, split them into chunks, and add each chunk to the vector database with metadata.

```python
from pathlib import Path
from agentic_patterns.core.vectordb import get_vector_db

vdb = get_vector_db("books")

for txt_file in Path("data/docs").glob("*.txt"):
    text = txt_file.read_text()
    for i, paragraph in enumerate(text.split("\n\n")):
        if len(paragraph.strip()) < 50:
            continue
        vdb.add(text=paragraph, doc_id=f"{txt_file.stem}-{i}", meta={"source": txt_file.stem})
```

**Retrieval** (run on every query): embed the user's question, find similar chunks, and pass them as context to the agent.

```python
from agentic_patterns.core.agents import get_agent, run_agent

results = vdb.query(query="Who is a man with two heads?")

docs_str = "\n\n".join(f"[{r.score:.3f}] {r.text}" for r in results)

prompt = f"Given these documents, answer the question.\n\n{docs_str}\n\nQuestion: Who is a man with two heads?"
agent = get_agent()
run, _ = await run_agent(agent, prompt)
```

The library handles embedding and search. You control chunking strategy, prompt construction, and any retrieval enhancements (query expansion, re-ranking, metadata filtering).


## Advanced Retrieval Techniques

The vector database module supports several techniques that improve retrieval quality beyond simple single-query search.

**Metadata filtering.** Pass `filter` to `vdb.query()` to restrict results at the database level. This is more efficient than post-retrieval filtering and useful for access control, source restriction, or temporal constraints.

```python
results = vdb.query(query="main character", filter={"source": "hhgttg"})
```

**Query expansion.** Generate multiple reformulations of the user's query using an LLM, then query the vector database with each reformulation. Combine and deduplicate the results. This increases recall when documents use different terminology than the query.

**Semantic chunking.** Instead of splitting on paragraph boundaries, use an LLM to identify topic boundaries. Pass `output_type=list[str]` to `get_agent()` to get structured chunk lists. For large documents, batch the text and carry incomplete chunks across batches.

**Re-ranking.** After retrieving a candidate set from multiple queries, sort by similarity score and limit to top-N results. For higher precision, use a cross-encoder model to re-score query-document pairs.

These techniques compose naturally with `vdb.query()` and `vdb.retrieve()` -- they operate on the inputs (query expansion) or outputs (deduplication, re-ranking) of the same API.

`MultiSourceRetriever` (`agentic_patterns.core.vectordb.multi_source`) queries multiple VectorDB collections in parallel and merges results.

`cluster()` and `label_clusters()` (`agentic_patterns.core.vectordb.clustering`) group documents by embedding similarity using HDBSCAN or K-Means.


## API Reference

### `agentic_patterns.core.vectordb`

| Name | Kind | Description |
|---|---|---|
| `EmbeddingConfig` | Type alias | Union of all embedding config types (OpenAI, Ollama, SentenceTransformers, OpenRouter) |
| `VectorDBConfig` | Type alias | Union of all vector DB config types (Chroma, PgVector) |
| `VectorDB` | Class | Wraps a Chroma collection with add, query, retrieve, ingest operations |
| `VectorDB.add(text, doc_id, meta, force)` | Method | Add a document (idempotent by default) |
| `VectorDB.query(query, filter, ...)` | Method | Similarity search returning `list[RetrievedDocument]` |
| `VectorDB.retrieve(query, max_results, filter, level)` | Method | Query with deduplication and chunk-level filtering |
| `VectorDB.fetch_parent(doc)` | Method | Fetch parent chunk for context widening |
| `VectorDB.ingest(chunks, force)` | Method | Store `Chunk` objects, returns count added |
| `VectorDB.ingest_file(file, provenance, ...)` | Method | Load, chunk, and store a file |
| `VectorDB.get_by_id(doc_id)` | Method | Retrieve a document by ID |
| `VectorDB.has(doc_id)` | Method | Check if a document ID exists |
| `VectorDB.count()` | Method | Return document count |
| `VectorDB.collection` | Property | Direct access to underlying Chroma collection |
| `RetrievedDocument` | Pydantic model | doc_id, text, score, level, parent_id, metadata |
| `Chunk` | Pydantic model | doc_id, text, level, parent_id, metadata |
| `ChunkLevel` | Enum | DOCUMENT, CHAPTER, SECTION, PARAGRAPH |
| `ClusterResult` | Pydantic model | clusters: list[Cluster] |
| `get_vector_db(collection_name, ...)` | Function | Get or create a VectorDB with singleton caching |
| `get_embedder(config, config_path)` | Function | Get or create an embedder with singleton caching |
| `embed_text(text, embedder)` | Async function | Embed a single text string |
| `embed_texts(texts, embedder)` | Async function | Embed multiple text strings |
| `load_vectordb_settings(config_path)` | Function | Load settings from YAML (`config_path` is required, no default) |

### Configuration models (`agentic_patterns.core.vectordb.config`)

| Name | Kind | Description |
|---|---|---|
| `VectorDBSettings` | Pydantic model | Container for embedding and vector DB configs. Not exported in `__all__`; import directly from `agentic_patterns.core.vectordb.config`. Provides `get_embedding(name)` and `get_vectordb(name)` lookup methods. |
| `OpenAIEmbeddingConfig` | Pydantic model | OpenAI embedding settings |
| `OllamaEmbeddingConfig` | Pydantic model | Ollama embedding settings |
| `SentenceTransformersEmbeddingConfig` | Pydantic model | Sentence Transformers settings |
| `OpenRouterEmbeddingConfig` | Pydantic model | OpenRouter embedding settings |
| `ChromaVectorDBConfig` | Pydantic model | Chroma persistence settings |
| `PgVectorDBConfig` | Pydantic model | PostgreSQL + pgvector settings |


## Examples

See the notebooks in `agentic_patterns/examples/rag/`:

- `example_RAG_01_load.ipynb` -- simple paragraph-based document ingestion
- `example_RAG_01_query.ipynb` -- basic similarity search and prompt augmentation
- `example_RAG_02_load.ipynb` -- LLM-based semantic chunking with batch handling
- `example_RAG_02_query.ipynb` -- query expansion, metadata filtering, deduplication, and re-ranking
- `example_RAG_03_multi_source.ipynb` -- querying multiple collections via `MultiSourceRetriever`
- `example_RAG_04_clustering.ipynb` -- semantic clustering with `cluster()` and `label_clusters()`

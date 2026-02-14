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
) -> chromadb.Collection
```

`embedding_config` and `vectordb_config` select named entries from `config.yaml`. Both default to `"default"`.


### Adding documents

```python
from agentic_patterns.core.vectordb import vdb_add

vdb_add(vdb, text="The answer is 42.", doc_id="doc-1", meta={"source": "guide"})
```

`vdb_add` is idempotent by default -- if `doc_id` already exists, the call is a no-op and returns `None`. Pass `force=True` to overwrite. Metadata is optional but useful for filtering during retrieval.

**Signature:**

```python
def vdb_add(
    vdb: chromadb.Collection,
    text: str,
    doc_id: str,
    meta: dict | None = None,
    force: bool = False,
) -> str | None
```


### Querying

```python
from agentic_patterns.core.vectordb import vdb_query

results = vdb_query(vdb, query="What is the answer?")

for doc, meta, score in results:
    print(f"[{score:.3f}] {doc[:80]}...")
```

Each result is a `(document_text, metadata, similarity_score)` tuple. Scores are similarity values (higher is better), converted from Chroma's distance metric via `1.0 - distance`.

**Signature:**

```python
def vdb_query(
    vdb: chromadb.Collection,
    query: str,
    filter: dict[str, str] | None = None,
    where_document: dict[str, str] | None = None,
    max_items: int = 10,
    similarity_threshold: float | None = None,
) -> list[tuple[str, dict, float]]
```

| Parameter | Description |
|---|---|
| `filter` | Metadata filter applied at the database level (e.g., `{"source": "guide"}`) |
| `where_document` | Full-text filter on document content |
| `max_items` | Maximum number of results (default 10) |
| `similarity_threshold` | Drop results below this score |


### Lookup and existence check

```python
from agentic_patterns.core.vectordb import vdb_get_by_id, vdb_has_id

exists = vdb_has_id(vdb, "doc-1")
record = vdb_get_by_id(vdb, "doc-1")
```


## The RAG Pattern

The typical workflow has two phases.

**Ingestion** (run once or when the corpus changes): load documents, split them into chunks, and add each chunk to the vector database with metadata.

```python
from pathlib import Path
from agentic_patterns.core.vectordb import get_vector_db, vdb_add

vdb = get_vector_db("books")

for txt_file in Path("data/docs").glob("*.txt"):
    text = txt_file.read_text()
    for i, paragraph in enumerate(text.split("\n\n")):
        if len(paragraph.strip()) < 50:
            continue
        vdb_add(vdb, text=paragraph, doc_id=f"{txt_file.stem}-{i}", meta={"source": txt_file.stem})
```

**Retrieval** (run on every query): embed the user's question, find similar chunks, and pass them as context to the agent.

```python
from agentic_patterns.core.vectordb import vdb_query
from agentic_patterns.core.agents import get_agent, run_agent

results = vdb_query(vdb, query="Who is a man with two heads?")

docs_str = "\n\n".join(f"[{score:.3f}] {doc}" for doc, meta, score in results)

prompt = f"Given these documents, answer the question.\n\n{docs_str}\n\nQuestion: Who is a man with two heads?"
agent = get_agent()
run, _ = await run_agent(agent, prompt)
```

The library handles embedding and search. You control chunking strategy, prompt construction, and any retrieval enhancements (query expansion, re-ranking, metadata filtering).


## Advanced Retrieval Techniques

The vector database module supports several techniques that improve retrieval quality beyond simple single-query search.

**Metadata filtering.** Pass `filter` to `vdb_query()` to restrict results at the database level. This is more efficient than post-retrieval filtering and useful for access control, source restriction, or temporal constraints.

```python
results = vdb_query(vdb, query="main character", filter={"source": "hhgttg"})
```

**Query expansion.** Generate multiple reformulations of the user's query using an LLM, then query the vector database with each reformulation. Combine and deduplicate the results. This increases recall when documents use different terminology than the query.

**Semantic chunking.** Instead of splitting on paragraph boundaries, use an LLM to identify topic boundaries. Pass `output_type=list[str]` to `get_agent()` to get structured chunk lists. For large documents, batch the text and carry incomplete chunks across batches.

**Re-ranking.** After retrieving a candidate set from multiple queries, sort by similarity score and limit to top-N results. For higher precision, use a cross-encoder model to re-score query-document pairs.

These techniques compose naturally with the core `vdb_query()` function -- they operate on the inputs (query expansion) or outputs (deduplication, re-ranking) of the same API.


## API Reference

### `agentic_patterns.core.vectordb`

| Name | Kind | Description |
|---|---|---|
| `get_vector_db(collection_name, ...)` | Function | Get or create a Chroma collection with singleton caching |
| `vdb_add(vdb, text, doc_id, meta, force)` | Function | Add a document (idempotent by default) |
| `vdb_query(vdb, query, filter, ...)` | Function | Similarity search returning `(doc, meta, score)` tuples |
| `vdb_get_by_id(vdb, doc_id)` | Function | Retrieve a document by ID |
| `vdb_has_id(vdb, doc_id)` | Function | Check if a document ID exists |
| `get_embedder(config)` | Function | Get or create an embedder with singleton caching |
| `embed_text(text, embedder)` | Async function | Embed a single text string |
| `embed_texts(texts, embedder)` | Async function | Embed multiple text strings |
| `load_vectordb_settings(config_path)` | Function | Load settings from YAML |

### Configuration models (`agentic_patterns.core.vectordb.config`)

| Name | Kind | Description |
|---|---|---|
| `VectorDBSettings` | Pydantic model | Container for embedding and vector DB configs |
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

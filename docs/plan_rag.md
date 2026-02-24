# RAG Core Library Plan

## Current State (`core/vectordb/`)

- `config.py`: `OpenAIEmbeddingConfig`, `OllamaEmbeddingConfig`, `SentenceTransformersEmbeddingConfig`, `OpenRouterEmbeddingConfig`, `ChromaVectorDBConfig`, `PgVectorDBConfig`, `VectorDBSettings`, `load_vectordb_settings()`
- `embeddings.py`: `get_embedder(config, config_path)`, `embed_text(text, embedder)`, `embed_texts(texts, embedder)`
- `vectordb.py`: `get_vector_db(collection_name, ...)`, `vdb_add(vdb, text, doc_id, meta, force)`, `vdb_get_by_id(vdb, doc_id)`, `vdb_has_id(vdb, doc_id)`, `vdb_query(vdb, query, ...)` returns `list[RetrievedDocument]`

## Architecture Notes

- `core/` is pure Python — no LLM calls, no PydanticAI agents.
- `agents/rag/` contains functions that use agents internally (via `get_agent()` / `run_agent()`). They are agent-powered operations, not agents that expose tools.
- All models use Pydantic `BaseModel`. All file paths use `Path`.
- Chunkers return `list[Chunk]`. Loaders return markdown text. Ingestion composes both.

## Items to Create

- [x] `core/doc_ingestion/models.py` — `DocumentProvenance(BaseModel)` capturing three reference levels: `original_file: Path | None` (source PDF/DOCX/etc.), `markdown_file: Path | None` (intermediate markdown), `source: str | None` (URL, document title, or paper reference). Attached to every chunk's metadata so provenance survives all the way to `RetrievedDocument`.

- [x] `core/doc_ingestion/loader.py` — two loaders, both return a markdown string:
  - `load_document(file: Path, provenance: DocumentProvenance, pipeline: str = "standard") -> str`: parses any format (PDF, DOCX, PPTX, HTML, images) via docling. `pipeline="standard"` uses docling's text extraction; `pipeline="vlm"` uses docling's vision-model pipeline for complex layouts (dense slides, charts).
  - `load_markdown(file: Path, provenance: DocumentProvenance) -> str`: reads an already-converted markdown file directly.

- [x] `core/vectordb/models.py` — all shared data models:
  - `ChunkLevel(str, Enum)`: `DOCUMENT`, `CHAPTER`, `SECTION`, `PARAGRAPH`.
  - `Chunk(BaseModel)`: `doc_id: str`, `text: str`, `level: ChunkLevel`, `parent_id: str | None`, `metadata: dict`. Metadata always includes serialized `DocumentProvenance` fields.
  - `RetrievedDocument(BaseModel)`: `doc_id: str`, `text: str`, `score: float`, `level: ChunkLevel`, `parent_id: str | None`, `metadata: dict`. Replaces `tuple[str, dict, float]` returned by `vdb_query()`.
  - `ClusterItem(BaseModel)`: `doc_id: str`, `text: str`, `metadata: dict`.
  - `Cluster(BaseModel)`: `cluster_id: int`, `label: str | None`, `summary: str | None`, `items: list[ClusterItem]`. `label` and `summary` start as `None`, populated by `agents/rag/clustering.py`.
  - `ClusterResult(BaseModel)`: `clusters: list[Cluster]`.

- [x] `core/vectordb/vectordb.py` (update) — change `vdb_query()` return type from `list[tuple[str, dict, float]]` to `list[RetrievedDocument]`.

- [x] `core/vectordb/chunking.py` — pure text, no LLM. All chunkers return `list[Chunk]` with `level` and `parent_id` populated, preserving hierarchy in the VDB. Heading mapping: `#`→DOCUMENT, `##`→CHAPTER, `###`→SECTION, paragraph→PARAGRAPH. `doc_id` scheme: `{stem}-doc`, `{stem}-ch{i}`, `{stem}-ch{i}-sec{j}`, `{stem}-ch{i}-sec{j}-p{k}`.
  - `chunk_by_paragraphs(text: str, provenance: DocumentProvenance, min_lines: int = 3) -> list[Chunk]`: naive splitter, all chunks at `PARAGRAPH` level, `parent_id=None`.
  - `chunk_by_markdown(text: str, provenance: DocumentProvenance, max_chunk_size: int = 2000) -> list[Chunk]`: splits at heading boundaries, never breaks code blocks or tables, sets `parent_id` to the parent heading chunk's `doc_id`.
  - `chunk(text: str, provenance: DocumentProvenance) -> list[Chunk]`: auto-selects `chunk_by_markdown` if text contains markdown headings, otherwise `chunk_by_paragraphs`. LLM-based chunking is an explicit opt-in via `agents/rag/chunking.py`.

- [x] `core/vectordb/ingestion.py` — composes loading, chunking, and storing:
  - `ingest(vdb: chromadb.Collection, chunks: list[Chunk], force: bool = False) -> int`: calls `vdb_add()` for each chunk, returns count of added chunks.
  - `ingest_file(vdb: chromadb.Collection, file: Path, provenance: DocumentProvenance, pipeline: str = "standard", force: bool = False) -> int`: convenience wrapper — calls `load_document()` or `load_markdown()` based on file extension, then `chunk()`, then `ingest()`.

- [x] `core/vectordb/retrieval.py` — retrieval pipeline, no LLM:
  - `retrieve(vdb: chromadb.Collection, query: str, max_results: int = 10, filter: dict | None = None, level: ChunkLevel | None = None) -> list[RetrievedDocument]`: wraps `vdb_query()` with deduplication and sorting. `level` adds a metadata filter to restrict to a specific granularity.
  - `fetch_parent(vdb: chromadb.Collection, doc: RetrievedDocument) -> RetrievedDocument | None`: fetches the parent chunk by following `parent_id`, allowing callers to widen context after a fine-grained match (e.g. find paragraph, then fetch its section).

- [x] `core/vectordb/multi_source.py` — `MultiSourceRetriever`: holds `sources: dict[str, chromadb.Collection]` (named collections). `retrieve_all(query: str, max_results: int = 10, level: ChunkLevel | None = None) -> list[RetrievedDocument]`: queries all sources in parallel, merges and deduplicates. Source name is preserved in each `RetrievedDocument`'s metadata for provenance.

- [x] `core/vectordb/clustering.py` — `cluster(input: list[Chunk] | chromadb.Collection, n_clusters: int | None = None, algorithm: str = "hdbscan", embedder=None) -> ClusterResult`: clusters by embedding. When input is a `chromadb.Collection`, fetches stored embeddings directly (no re-embedding). `algorithm="kmeans"` requires `n_clusters`; `algorithm="hdbscan"` auto-discovers k. Returns `ClusterResult` with `label=None` and `summary=None` on each cluster.

- [x] `agents/rag/chunking.py` — `chunk_with_llm(text: str, provenance: DocumentProvenance, agent=None, batch_size: int = 15000) -> list[Chunk]`: semantic chunking via LLM. Splits text into batches at paragraph boundaries, prompts the agent to identify topic boundaries, handles leftover logic across batches (last chunk of each batch prepended to the next). Returns chunks at `SECTION` level.

- [x] `agents/rag/retrieval.py` — `expand_query(query: str, agent=None) -> list[str]`: prompts LLM to reformulate a query into multiple variants for broader retrieval coverage. Used before calling `retrieve()` to improve recall.

- [x] `agents/rag/clustering.py` — `label_clusters(result: ClusterResult, agent=None) -> ClusterResult`: prompts LLM to assign a short `label` and a `summary` to each cluster based on its items. Returns an updated `ClusterResult`.

## File Layout

```
core/doc_ingestion/
    models.py        (done - DocumentProvenance)
    loader.py        (done - load_document, load_markdown)

core/vectordb/
    config.py        (exists)
    embeddings.py    (exists)
    vectordb.py      (updated - vdb_query returns list[RetrievedDocument])
    models.py        (done - ChunkLevel, Chunk, RetrievedDocument, ClusterItem, Cluster, ClusterResult)
    chunking.py      (done - chunk_by_paragraphs, chunk_by_markdown, chunk)
    ingestion.py     (done - ingest, ingest_file)
    retrieval.py     (done - retrieve, fetch_parent)
    multi_source.py  (done - MultiSourceRetriever)
    clustering.py    (done - cluster)

agents/rag/
    chunking.py      (done - chunk_with_llm)
    retrieval.py     (done - expand_query)
    clustering.py    (done - label_clusters)

prompts/rag/
    chunk_boundaries.md  (done)
    expand_query.md      (done)
    label_clusters.md    (done)
```

## Clarifications

- LlamaIndex and LangChain are not used — the book teaches the patterns, not library abstractions.
- Chroma is used for examples; `PgVectorDBConfig` exists in config for production use but is not implemented in this plan.
- `agents/rag/` functions are agent-powered operations (they call `get_agent()` / `run_agent()` internally), not agents that expose tools to other agents.
- The `chunk_with_llm` leftover logic: the last chunk of each batch is assumed potentially incomplete and is prepended to the next batch so the LLM can finish it with full context.
- Multi-level chunking means every level (DOCUMENT, CHAPTER, SECTION, PARAGRAPH) is stored as a separate document in the VDB. `parent_id` links child to parent, enabling context widening at retrieval time via `fetch_parent()`.
- `DocumentProvenance` fields are serialized into chunk metadata as flat strings so they survive the round-trip through Chroma (which only supports flat metadata values).
- `ingest_file` routes `.md` files to `load_markdown()`, all other extensions to `load_document()`.
- New dependencies added to `pyproject.toml`: `docling`, `hdbscan` (scikit-learn was already present).
- Prompt templates for `agents/rag/` go in `prompts/rag/` following project conventions, loaded via `load_prompt()`.
- Existing caller `core/connectors/vocabulary/strategy_rag.py` updated to use `RetrievedDocument` attributes instead of tuple unpacking.
- Existing notebooks `example_RAG_01_query.ipynb` and `example_RAG_02_query.ipynb` updated to use `RetrievedDocument` attributes.

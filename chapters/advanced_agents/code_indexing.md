## Code Indexing and Search Agent

A code indexing and search agent maintains an always-up-to-date, structure-aware representation of a repository, and answers natural-language (and symbol-level) questions by retrieving the smallest, most relevant code slices with traceable provenance.

### Why “code indexing” is different from generic RAG

Generic document RAG treats code as text, but most developer questions are about structure: “Where is this function called?”, “Which implementation is used on Linux?”, “What invariants does this type enforce?”, or “Show me similar patterns in the repo.” A code index that preserves syntax boundaries, symbol identity, and file/line provenance improves both precision (you retrieve coherent units like functions/classes) and usability (results can be navigated, cited, and patched reliably).

A second difference is freshness. For interactive coding agents, stale context is often worse than missing context: the agent reasons correctly over an outdated snapshot. CocoIndex’s examples frame the practical goal as near-real-time incremental updates, reprocessing only what changed, so the index behaves like a live substrate rather than a periodically rebuilt artifact. ([GitHub][1])

### Index construction as a dataflow with incremental recomputation

A practical indexing pipeline is easiest to reason about when it is explicit: sources produce records, transforms derive new fields, collectors persist derived artifacts. CocoIndex follows a dataflow model in which each transformation derives outputs from inputs without hidden mutation, enabling lineage tracking and incremental recomputation. ([GitHub][2])

In the CocoIndex code indexing example, the source is a filesystem scan (with include/exclude patterns), the transform computes language hints from file extensions, chunking is done with Tree-sitter-aware splitting, embeddings are computed for each chunk, and the resulting vectors plus metadata are exported to Postgres with pgvector. ([CocoIndex][3])

```python
@cocoindex.flow_def(name="CodeEmbedding")
def code_embedding_flow(flow_builder, data_scope):
    data_scope["files"] = flow_builder.add_source(
        cocoindex.sources.LocalFile(
            path=REPO_ROOT,
            included_patterns=["*.py", "*.rs", "*.toml", "*.md", "*.mdx"],
            excluded_patterns=[".*", "target", "**/node_modules"],
        )
    )
    code_embeddings = data_scope.add_collector()

    @cocoindex.op.function()
    def extract_extension(filename: str) -> str:
        return os.path.splitext(filename)[1]

    @cocoindex.transform_flow()
    def code_to_embedding(text):
        return text.transform(
            cocoindex.functions.SentenceTransformerEmbed(
                model="sentence-transformers/all-MiniLM-L6-v2"
            )
        )

    with data_scope["files"].row() as f:
        f["extension"] = f["filename"].transform(extract_extension)
        f["chunks"] = f["content"].transform(
            cocoindex.functions.SplitRecursively(),
            language=f["extension"],          # Tree-sitter-aware chunking
            chunk_size=1000,
            chunk_overlap=300,
        )

        with f["chunks"].row() as c:
            c["embedding"] = c["text"].call(code_to_embedding)
            code_embeddings.collect(
                filename=f["filename"],
                location=c["location"],
                code=c["text"],
                embedding=c["embedding"],
            )

    code_embeddings.export(
        "code_embeddings",
        cocoindex.storages.Postgres(),
        primary_key_fields=["filename", "location"],
        vector_indexes=[
            cocoindex.VectorIndex(
                "embedding",
                cocoindex.VectorSimilarityMetric.COSINE_SIMILARITY,
            )
        ],
    )
```

Two details are operationally important. First, chunking should be syntax-aware (Tree-sitter) so that chunks align with functions/classes rather than arbitrary line windows, which improves retrieval quality for code. ([DEV Community][4]) Second, the embedding transform should be shared between indexing and query; CocoIndex’s example uses `@cocoindex.transform_flow()` to ensure the exact same embedding logic is reused, preventing “index/query embedding drift.” ([CocoIndex][3])

### Query-time retrieval, scoring, and cross-reference resolution

At query time, the agent converts the user prompt into an embedding using the same transform, then executes a vector similarity search in Postgres/pgvector. The CocoIndex example shows using the `<=>` operator to compute distance and deriving a similarity score from it. ([CocoIndex][3])

```python
def search(pool, query: str, top_k: int = 8):
    table_name = cocoindex.utils.get_target_storage_default_name(
        code_embedding_flow, "code_embeddings"
    )
    q_vec = code_to_embedding.eval(query)

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT filename, location, code,
                       embedding <=> %s::vector AS distance
                FROM {table_name}
                ORDER BY distance
                LIMIT %s
            """, (q_vec, top_k))
            rows = cur.fetchall()

    return [
        {
            "filename": r[0],
            "location": r[1],
            "code": r[2],
            "score": 1.0 - r[3],
        }
        for r in rows
    ]
```

In practice, “code search” often needs a second stage beyond raw vector similarity. A code indexing agent can take the initial candidates and resolve cross-references by enriching context around each chunk: pull enclosing symbol names, signatures, docstrings/comments, import dependencies, and call sites. This turns a flat “top-k snippets” response into navigable context the coding agent can act on. Recent research systems increasingly combine retrieval with structure-aware navigation over repositories; for example, CodeNav emphasizes iterative repository navigation and selective import of relevant blocks, while graph-based approaches like CodexGraph extract a code graph to support more precise structure-aware queries. ([arXiv][5])

A simple, effective pattern is to treat cross-reference resolution as a follow-on retrieval step driven by the first retrieval:

```python
def expand_context(hit):
    # lightweight “symbol neighborhood” expansion
    symbol = infer_primary_symbol(hit["code"])
    defs = lexical_lookup(f"def {symbol}")          # fast exact/regex search
    refs = lexical_lookup(f"{symbol}(")             # call sites
    near = fetch_file_window(hit["filename"], hit["location"], radius=40)
    return merge(hit, defs=defs, refs=refs, near=near)

def answer(question):
    hits = search(pool, question, top_k=8)
    expanded = [expand_context(h) for h in hits[:3]]
    return synthesize_with_citations(question, expanded)
```

Even when you later add a richer symbol index (Tree-sitter AST to symbol table, or a graph store), the control flow stays stable: embed-and-retrieve for recall, then structure-aware expansion for faithfulness and editability.

### Tight integration with an interactive coding agent

In an “AI coding agent” loop, code search is rarely a one-shot. The agent alternates between proposing hypotheses (“the bug is in request parsing”), retrieving evidence (relevant functions, tests, config), and refining the hypothesis until it can implement and validate a change. The code indexing agent supplies three capabilities that keep this loop efficient:

It provides low-latency, high-recall candidate retrieval through embeddings over syntax-coherent chunks. ([DEV Community][4]) It provides freshness through incremental updates, so edits made during the session are quickly reflected in subsequent searches without a full rebuild. ([GitHub][1]) And it provides provenance (filename/location) so the coding agent can open the correct file regions and generate minimal diffs rather than rewriting large sections.

### References (references.md)

1. CocoIndex. *Real-time Codebase Indexing (Example)*. CocoIndex Documentation, 2026. ([CocoIndex][3])
2. cocoindex-io. *realtime-codebase-indexing*. GitHub repository, 2026. ([GitHub][1])
3. Jin, Linghua (CocoIndex). *Build Real-Time Codebase Indexing for AI Coding agents*. DEV Community, 2025. ([DEV Community][4])
4. cocoindex-io. *cocoindex: Data transformation framework for AI*. GitHub repository, 2026. ([GitHub][2])
5. Tree-sitter contributors. *Tree-sitter: an incremental parsing system*. Project documentation, ongoing. ([DEV Community][4])
6. Gupta, T., Weihs, L., Kembhavi, A. *CodeNav: Beyond tool-use to using real-world codebases with LLM agents*. arXiv, 2024. ([arXiv][5])
7. Liu, X. et al. *CodexGraph: Bridging Large Language Models and Code Repositories via Code Graph Databases*. arXiv, 2024. ([arXiv][6])

[1]: https://github.com/cocoindex-io/realtime-codebase-indexing "GitHub - cocoindex-io/realtime-codebase-indexing: build codebase index with tree-sitter. works with large codebases, and can be updated in near real-time with incremental processing - only reprocess what's changed."
[2]: https://github.com/cocoindex-io/cocoindex "GitHub - cocoindex-io/cocoindex: Data transformation framework for AI. Ultra performant, with incremental processing.   Star if you like it!"
[3]: https://cocoindex.io/examples/code_index "Real-time Codebase Indexing | CocoIndex"
[4]: https://dev.to/cocoindex/build-real-time-codebase-indexing-for-ai-coding-agents-5eb2 "Build Real-Time Codebase Indexing for AI Coding agents - DEV Community"
[5]: https://arxiv.org/abs/2406.12276?utm_source=chatgpt.com "CodeNav: Beyond tool-use to using real-world codebases with LLM agents"
[6]: https://arxiv.org/abs/2408.03910?utm_source=chatgpt.com "CodexGraph: Bridging Large Language Models and Code Repositories via Code Graph Databases"

## Code Indexing and Search Agent

A code indexing and search agent maintains an always-up-to-date, structure-aware representation of a repository, and answers natural-language (and symbol-level) questions by retrieving the smallest, most relevant code slices with traceable provenance.

### Why "code indexing" is different from generic RAG

Generic document RAG treats code as text, but most developer questions are about structure: "Where is this function called?", "Which implementation is used on Linux?", "What invariants does this type enforce?", or "Show me similar patterns in the repo." A code index that preserves syntax boundaries, symbol identity, and file/line provenance improves both precision (you retrieve coherent units like functions/classes) and usability (results can be navigated, cited, and patched reliably).

A second difference is freshness. For interactive coding agents, stale context is often worse than missing context: the agent reasons correctly over an outdated snapshot. CocoIndex's examples frame the practical goal as near-real-time incremental updates, reprocessing only what changed, so the index behaves like a live substrate rather than a periodically rebuilt artifact. ([GitHub][1])

### Three-index architecture

Our implementation uses a `CodeIndex` class that maintains three parallel vector collections for every indexed repository, all sharing the same `doc_id` per symbol:

The **code index** (`{name}_code`) stores raw source code. This serves pattern-level and syntax-level queries -- when a developer asks "show me the retry logic" or "find classes that inherit from Connector", the actual code is what gets matched and returned.

The **descriptions index** (`{name}_descriptions`) stores LLM-generated one-sentence semantic descriptions of what each symbol does. This serves intent-level queries -- "how does the system handle connection failures?" matches against descriptions like "Establishes a connection to a remote server with retry logic, attempting up to MAX_RETRIES times."

The **breadcrumbs index** (`{name}_breadcrumbs`) stores structural context for each symbol: its module path, parent class (for methods), signature, imports from the same file, and sibling symbols. This serves navigational queries -- "what uses ConnectionPool?" or "what else is in the chunker module?" matches against the structural relationships between symbols.

At query time, all three collections are searched in parallel via `MultiSourceRetriever`, which merges results by score and deduplicates by `doc_id`. A hit from any index resolves back to code (since all three share the same `doc_id`), and from there the agent can navigate up to the parent class, across to callers, or down to method implementations.

```python
code_index = CodeIndex(repo_path, "my_project")
stats = await code_index.index(include_patterns=["*.py"])
```

### Index construction: chunking, describing, and breadcrumbing

Index construction proceeds file by file. For each source file:

First, `ChunkerCode` parses the file with Tree-sitter and extracts syntax-coherent chunks -- one per function, class, or method, plus a preamble chunk for top-level imports and constants. Each chunk carries metadata: `symbol_name`, `symbol_type`, `start_line`, `end_line`, and the file's relative path. All chunks are stored in the code index. This syntax-aware chunking is the foundation -- chunks align with the units developers think about (functions, classes) rather than arbitrary line windows. ([DEV Community][4])

Second, `build_breadcrumbs()` deterministically constructs a structural breadcrumb for each symbol from the chunk metadata and file content. No LLM call is needed; the breadcrumb is derived from the AST structure that Tree-sitter already extracted.

Third, `describe_symbols()` generates semantic descriptions by sending all symbols from a file to an LLM in a single batched call. The LLM returns a structured list of `SymbolDescription` objects (one per symbol), each with the symbol name, type, and a one-sentence description focusing on purpose and behavior. This means one LLM call per file rather than one per symbol -- a file with 15 methods is one call, not 15.

```python
# Breadcrumb example (deterministic, from AST):
# module: core/rag/chunker_code.py | parent: class ChunkerCode |
#   signature: def chunk(self, text, provenance) | imports: pathlib, ...

# Description example (LLM-generated):
# "Parses source code with tree-sitter and splits it into syntax-coherent
#  chunks aligned to function and class boundaries."
```

Two details from the CocoIndex literature remain operationally important here. First, chunking should be syntax-aware (Tree-sitter) so that chunks align with functions/classes rather than arbitrary line windows, which improves retrieval quality for code. ([DEV Community][4]) Second, embedding drift between indexing and query must be avoided; our implementation uses the same embedding model for both paths via the shared `VectorDB` configuration. ([CocoIndex][3])

### Query-time retrieval and navigation

At query time, the agent has two complementary operations: `search` and `expand`.

`search(query, top_k)` queries all three indexes in parallel and returns `CodeSearchResult` objects. Each result carries the code, its description, its breadcrumb, symbol metadata, and the score. Because the multi-source retriever merges across indexes, a query like "how does retry work" might match via the description index while "def connect" matches via the code index -- both surface the same symbol with complementary evidence.

```python
results = await code_index.search("split text into paragraphs", top_k=5)
for r in results:
    print(f"[{r.score:.3f}] {r.symbol_type} {r.symbol_name} in {r.file_path}:{r.start_line}")
    print(f"  {r.description}")
```

`expand(doc_id)` takes a specific symbol and retrieves its full navigable context: the code, description, and breadcrumb, plus the parent class (for methods) and sibling symbols. This is more precise than the old "expand top-k with cross-references" approach -- the agent picks which result to expand based on the search results, then navigates structurally from there.

```python
expanded = code_index.expand(results[0].doc_id)
# Returns: code, description, breadcrumb, parent class info, sibling symbols
```

In practice, "code search" often needs this second stage beyond raw vector similarity. Recent research systems increasingly combine retrieval with structure-aware navigation over repositories; for example, CodeNav emphasizes iterative repository navigation and selective import of relevant blocks, while graph-based approaches like CodexGraph extract a code graph to support more precise structure-aware queries. ([arXiv][5])

### Tight integration with an interactive coding agent

In an "AI coding agent" loop, code search is rarely a one-shot. The agent alternates between proposing hypotheses ("the bug is in request parsing"), retrieving evidence (relevant functions, tests, config), and refining the hypothesis until it can implement and validate a change. The code indexing agent supplies three capabilities that keep this loop efficient:

It provides low-latency, high-recall candidate retrieval through embeddings over syntax-coherent chunks, with the added dimension that intent-level queries hit descriptions while structural queries hit breadcrumbs. ([DEV Community][4]) It provides navigability through the `expand` operation, so the agent can follow the structure from a search hit to its parent class, siblings, and related symbols without additional keyword searches. And it provides provenance (filename/line numbers) so the coding agent can open the correct file regions and generate minimal diffs rather than rewriting large sections.

Indexing is a user-initiated setup step -- you create a `CodeIndex` and call `index()`:

```python
code_index = CodeIndex(repo_path, "my_project")
stats = await code_index.index(include_patterns=["*.py"])
```

At the end of indexing, `CodeIndex` automatically generates a description from the symbol summaries it already produced and stores it in a registry (a YAML file for visibility, backed by a vector DB for semantic search). When the agent later needs a `CodeIndex` object, it reconstructs it automatically from the registry metadata -- no manual registration step is needed. At enterprise scale, an organization might index hundreds of GitHub repos, each as a separate collection. When the user asks a question without specifying a collection, the agent calls `code_list_indexes(query)` to semantically search this registry and find which repos are relevant -- the user never needs to know collection names. For example, if a repo's auto-generated description includes terms like "Stripe integration, invoicing, webhooks", asking "how does retry logic work in the payment service" would match and route the search to the right collection automatically.

The agent is created via `create_agent()` which loads the system prompt and wires up the tools (`code_list_indexes`, `code_search`, `code_expand`, `code_lexical_search`). The system prompt describes the three-index architecture so the agent knows to use intent-level queries for "how does X work" questions and structural queries for "what uses X" questions.

### Hands-on

See `example_code_indexing.ipynb` for a working notebook that demonstrates syntax-aware chunking, indexing a real directory, and using the agent for overview, intent-level search, structural navigation, and lexical cross-referencing.

[1]: https://github.com/cocoindex-io/realtime-codebase-indexing "GitHub - cocoindex-io/realtime-codebase-indexing"
[2]: https://github.com/cocoindex-io/cocoindex "GitHub - cocoindex-io/cocoindex"
[3]: https://cocoindex.io/examples/code_index "Real-time Codebase Indexing | CocoIndex"
[4]: https://dev.to/cocoindex/build-real-time-codebase-indexing-for-ai-coding-agents-5eb2 "Build Real-Time Codebase Indexing for AI Coding agents - DEV Community"
[5]: https://arxiv.org/abs/2406.12276 "CodeNav: Beyond tool-use to using real-world codebases with LLM agents"
[6]: https://arxiv.org/abs/2408.03910 "CodexGraph: Bridging Large Language Models and Code Repositories via Code Graph Databases"

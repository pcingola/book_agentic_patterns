## Hands-On: Code Indexing and Search

This exercise (`example_code_indexing.ipynb`) demonstrates the code indexing agent on a real directory. After a quick look at syntax-aware chunking (what the agent works with), we index a directory as a setup step, then let the agent search and navigate the pre-built index across four tasks.

### Syntax-aware chunking (the foundation)

`ChunkerCode` uses Tree-sitter to parse source files and extract functions, classes, and methods as individual chunks. Each chunk carries symbol metadata (name, type, line range). This is what the agent's tools operate on internally.

```python
chunker = ChunkerCode()
provenance = DocumentProvenance(original_file=Path("example.py"), source="example.py")
chunks = chunker.chunk(sample_code, provenance)
```

Each chunk's `doc_id` encodes the symbol structure: `example-function-1-connect`, `example-class-2-ConnectionPool`, `example-class2-method-1-__init__`, etc. The format is `{stem}-{symbol_type}-{index}-{name}` with lowercase type names and 1-based indexes.

### Indexing (setup)

Indexing is a user-initiated step, not something the agent decides to do. We create a `CodeIndex`, call `index()` to populate the three parallel collections, and register it with a description. The description is stored in a registry vector DB so the agent can discover relevant indexes via semantic search -- the user never needs to mention collection names in their prompts.

```python
code_index = CodeIndex(target_dir, "code_demo")
stats = await code_index.index(include_patterns=["*.py"])
register_index(code_index, description="RAG pipeline: chunking, clustering, retrieval, and code-aware parsing")
```

The stats report files indexed, chunks created, and any errors. Indexing generates descriptions concurrently, so it makes LLM calls proportional to the number of symbols.

### The agent

The agent has four tools: `code_list_indexes` (discover relevant collections by semantically searching index descriptions), `code_search` (semantic search across code, descriptions, and breadcrumbs), `code_expand` (navigate from a symbol to its parent, siblings, and full context), and `code_lexical_search` (exact/regex match on source files). It operates on a pre-built index -- it does not decide when to index.

### Task 1: Overview

Ask the agent to explore the indexed codebase and summarize it. Since no collection name is given, it will call `code_list_indexes` to discover the right collection, then use `code_search` to find the main symbols and their descriptions.

### Task 2: Intent-level search

A "how does X work" question exercises the descriptions index. The agent searches by intent (matching against LLM-generated summaries), then expands results to show the actual code and structural context.

### Task 3: Structural navigation

Asking about a specific class and its methods exercises `code_expand`. The agent finds the class via `code_search`, then navigates its structure -- expanding to see parent, sibling methods, and breadcrumbs -- to build a complete picture without additional keyword searches.

### Task 4: Lexical search + cross-referencing

Asking "where is X referenced" exercises `code_lexical_search` (exact match on source files) combined with `code_search` to understand what each usage site does. This is the pattern for real-world cross-reference resolution: find all references first, then understand each one.

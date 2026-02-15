# Vocabulary Connector

`VocabularyConnector` resolves free-text terms into standardized vocabulary codes. It bridges natural language and structured databases by providing term discovery, validation, and hierarchy navigation.

## Strategies

Three resolution strategies are selected based on vocabulary size:

**StrategyEnum** (fewer than 100 terms) -- stores terms in memory with exact lookup and fuzzy matching via `difflib.get_close_matches`. No hierarchy support.

**StrategyTree** (fewer than 1,000 terms) -- stores terms in an adjacency list with parent-child relationships. Supports BFS traversal for hierarchical queries (ancestors, descendants, siblings, subtree), plus exact and substring search.

**StrategyRag** (1,000+ terms) -- indexes terms into a Chroma vector database using embeddings. Supports semantic search where "cell death" finds "apoptotic process" even without word overlap. Also provides `suggest()` for free-text-to-code resolution.

All strategies implement the same `Strategy` protocol, so the connector works identically regardless of backend.

## Configuration

Vocabularies are declared in `vocabularies.yaml`:

```yaml
vocabularies:
  ensembl_biotypes:
    strategy: enum
    source: ensembl_biotypes.json
    source_format: json_flat

  sequence_ontology:
    strategy: tree
    source: so.obo
    source_format: obo

  gene_ontology:
    strategy: rag
    source: go.obo
    source_format: obo
    collection: gene_ontology

  hgnc:
    strategy: rag
    source: hgnc_complete_set.txt
    source_format: tsv
    collection: hgnc
    parser_options:
      id_field: hgnc_id
      label_field: symbol
      definition_field: name
```

Each entry declares `strategy` (`enum`, `tree`, or `rag`), `source` (file path relative to the vocabulary data directory), and `source_format`. RAG vocabularies require a `collection` name for the vector database. For tabular formats (CSV, TSV, JSON), `parser_options` can override which fields map to id, label, and definition.

Supported source formats: `obo`, `owl`, `rf2`, `json_flat`, `json_hierarchical`, `csv`, `tsv`, `mesh_xml`, `gmt`.

`load_all()` loads all declared vocabularies, dispatching each source file to its format-specific parser and populating the appropriate strategy backend. Parsed terms are cached as JSON to skip re-parsing on subsequent loads.

## Programmatic Registration

```python
from agentic_patterns.core.connectors.vocabulary.registry import register_vocabulary, reset
from agentic_patterns.core.connectors.vocabulary.strategy_tree import StrategyTree

reset()
register_vocabulary("sequence_ontology", StrategyTree(name="sequence_ontology", terms=terms))
```

## Operations

`list_vocabularies()` -- all registered vocabularies with strategy type and term count.

`info(vocab_name)` -- metadata for a specific vocabulary.

`search(vocab_name, query, max_results=10)` -- search for terms matching a query. Uses substring/fuzzy matching for Enum/Tree, semantic search for RAG.

`suggest(vocab_name, text, max_results=10)` -- semantic suggestions (RAG strategy only).

`lookup(vocab_name, term_code)` -- look up a term by code/ID.

`validate(vocab_name, term_code)` -- check whether a code is valid. Returns validity status and a suggestion if invalid.

`parent(vocab_name, term_code)` -- direct parent(s).

`children(vocab_name, term_code)` -- direct children.

`ancestors(vocab_name, term_code, max_depth=10)` -- ancestor chain to root.

`descendants(vocab_name, term_code, max_depth=10)` -- all descendants.

`siblings(vocab_name, term_code)` -- terms sharing the same parent.

`roots(vocab_name)` -- top-level terms.

`subtree(vocab_name, term_code, max_depth=3)` -- hierarchical view for browsing.

`relationships(vocab_name, term_code)` -- all typed relationships for a term.

`related(vocab_name, term_code, relation_type)` -- terms connected by a specific relation type.

## Vocabulary Agent

```python
from agentic_patterns.agents.vocabulary import create_agent

agent = create_agent(vocab_names=["sequence_ontology", "gene_ontology"])
result, nodes = await run_agent(agent, "Find the code for 'programmed cell death' in Gene Ontology")
```

The agent's instructions list available vocabularies with strategy and term count, so the model knows which vocabulary to query.

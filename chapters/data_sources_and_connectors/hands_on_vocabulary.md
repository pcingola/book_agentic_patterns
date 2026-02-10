## Hands-On: Controlled Vocabularies

This hands-on walks through `example_vocabulary.ipynb`, where an agent resolves free-text terms into standardized vocabulary codes. The example registers two toy vocabularies -- one using the Tree strategy (exact and fuzzy matching for medium-sized vocabularies) and another using the RAG strategy (semantic vector search for large vocabularies) -- then demonstrates both direct connector usage and autonomous agent resolution.

The practical motivation is straightforward: a clinical database stores diseases, genes, or sequence features using controlled vocabulary codes, not free text. Before an agent can query that database, it needs to translate the user's natural language ("programmed cell death") into the corresponding code (`GO:0006915`). The VocabularyConnector handles this translation.

## Two Resolution Strategies

The vocabulary system offers two strategies selected based on vocabulary size.

The Tree strategy stores terms in an adjacency list with parent-child relationships and typed edges. It supports exact matching by label, substring matching, and fuzzy matching via `difflib.get_close_matches`. It also supports hierarchy traversal: ancestors, descendants, siblings, subtree. This works well for vocabularies up to about 1,000 terms where the full structure fits in memory and exact/fuzzy matching is sufficient. The toy example uses a subset of Sequence Ontology (~20 terms describing genomic features like CDS, exon, SNV).

The RAG strategy indexes terms into a vector database (Chroma) using embeddings. Search is semantic: the query "cell death" finds "apoptotic process" even though the words don't overlap, because the embeddings capture meaning. This strategy scales to vocabularies with thousands or millions of terms where exact matching would miss synonyms and related concepts. The toy example uses a subset of Gene Ontology (~15 terms for biological processes and molecular functions).

Both strategies implement the same interface, so the VocabularyConnector and the agent tools work identically regardless of which strategy backs a given vocabulary.

## Registering Vocabularies

The notebook registers both vocabularies programmatically using in-memory toy data. In production, vocabularies would be loaded from files (OBO, OWL, tabular formats) declared in `vocabularies.yaml`:

```python
reset()

tree_backend = StrategyTree(name="sequence_ontology", terms=get_toy_tree_terms())
register_vocabulary("sequence_ontology", tree_backend)

rag_backend = StrategyRag(name="gene_ontology", collection="gene_ontology_demo")
for term in get_toy_rag_terms():
    rag_backend.add_term(term)
register_vocabulary("gene_ontology", rag_backend)
```

`reset()` clears any previously registered vocabularies, which matters in notebook environments where cells may be re-executed. The Tree backend receives all terms at construction. The RAG backend receives terms one at a time via `add_term()`, which computes the embedding and indexes each term into the vector database. The document text for embedding is built from the term's label, synonyms, and definition concatenated together -- this gives the embedding model enough surface to match semantically similar queries.

## Using the Connector Directly

The VocabularyConnector provides a uniform API over both strategies. Every method returns a formatted string, not raw objects, because the connector is designed to be called by agents that consume text:

```python
connector = VocabularyConnector()

connector.search("sequence_ontology", "coding sequence")
connector.ancestors("sequence_ontology", "SO:0000316")
connector.validate("sequence_ontology", "SO:0000317")
```

The `search` call on the Tree backend finds "CDS" because "coding sequence" is listed as a synonym. The `ancestors` call traverses the parent chain from CDS up to the root. The `validate` call checks whether `SO:0000317` exists; since it doesn't, the Tree strategy uses fuzzy matching to suggest the closest valid code.

For the RAG backend, search is semantic:

```python
connector.search("gene_ontology", "cell death", max_results=3)
connector.suggest("gene_ontology", "inflammation in tissues", max_results=3)
```

The query "cell death" retrieves "apoptotic process" because the embedding of "cell death" is close to the embedding of "apoptotic process / programmed cell death / apoptosis". The `suggest` method is a RAG-only operation that works identically to `search` but signals intent: the caller is looking for the best matching term for a free-text description.

## The Vocabulary Agent

The final section creates an agent with vocabulary tools and gives it a multi-part natural language query:

```python
agent = create_agent(vocab_names=["sequence_ontology", "gene_ontology"])

query = (
    "I need the controlled vocabulary code for 'programmed cell death' in Gene Ontology. "
    "Also find the code for 'single nucleotide variant' in Sequence Ontology "
    "and show me its parent terms."
)

result, nodes = await run_agent(agent, query, verbose=True)
```

`create_agent()` (in `agents/vocabulary`) builds a PydanticAI agent with tools wrapping every connector method: `vocab_search`, `vocab_lookup`, `vocab_ancestors`, `vocab_validate`, and others. The agent's instructions list the available vocabularies with their strategy type and term count, so the model knows which vocabulary to query for each part of the request.

Given this prompt, the agent typically proceeds in three steps. It searches Gene Ontology for "programmed cell death" and gets back `GO:0006915` (apoptotic process). It searches Sequence Ontology for "single nucleotide variant" and gets back `SO:0001483` (SNV). It then calls `vocab_ancestors` on `SO:0001483` to retrieve the parent chain through `sequence_alteration` up to `sequence_feature`. The agent composes these results into a final answer with the resolved codes and hierarchy.

This is the pattern that would precede a SQL query in a clinical database pipeline: the user says "find trials for programmed cell death", the vocabulary agent resolves that to `GO:0006915`, and the downstream NL2SQL agent uses that code in a WHERE clause.

## Key Takeaways

Controlled vocabularies bridge natural language and structured databases. The Tree strategy handles medium vocabularies with exact and fuzzy matching over an in-memory adjacency list. The RAG strategy handles large vocabularies with semantic search via vector embeddings. Both strategies share the same interface, so the VocabularyConnector and agent tools are strategy-agnostic. The vocabulary agent autonomously decides which vocabulary to search, resolves terms, and navigates hierarchies, producing standardized codes that downstream agents can use directly in SQL queries.

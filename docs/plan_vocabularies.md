# Plan: Vocabulary and Ontology Connector

## Overview

A `VocabularyConnector` for the core library that provides term resolution across controlled vocabularies and ontologies. Three resolution strategies based on vocabulary size, plus ontology-aware relationship traversal.


## Resolution Strategies

**Enum (< 100 terms)**: Full vocabulary loaded as a Python Enum or dict. In-memory exact/fuzzy lookup. Example: Ensembl Biotypes (~50 terms).

**Tree (< 1,000 terms)**: Loaded as a tree structure with parent/child/typed relationships. Supports hierarchy traversal, prefix search, ancestor/descendant queries. Example: Sequence Ontology (~2.5K), Cell Ontology (~2.7K).

**RAG (1,000+ terms)**: Indexed into a vector DB using the existing `vectordb` module. Term resolution via semantic search. Labels, synonyms, and definitions are embedded for rich matching. Example: Gene Ontology (~45K), NCI Thesaurus (~170K), NCBI Taxonomy (~2.4M).


## Connector Interface

Follows the existing connector pattern: static methods, `@tool_permission` decorator, string returns, workspace sandbox isolation via `ctx`.

```
VocabularyConnector

  # Term resolution
  lookup(vocab_name, term_code) -> term details (id, label, synonyms, definition)
  search(vocab_name, query, max_results) -> matching terms
  validate(vocab_name, term_code) -> bool + suggestion if invalid
  suggest(vocab_name, text, max_results) -> semantic matches (RAG strategy)

  # Hierarchy
  parent(vocab_name, term_code) -> direct parent(s)
  children(vocab_name, term_code) -> direct children
  siblings(vocab_name, term_code) -> terms sharing same parent
  ancestors(vocab_name, term_code, max_depth) -> parent chain to root
  descendants(vocab_name, term_code, max_depth) -> subtree
  roots(vocab_name) -> top-level terms

  # Ontology relationships
  relationships(vocab_name, term_code) -> all typed relations (is_a, part_of, regulates, has_role...)
  related(vocab_name, term_code, relation_type) -> terms connected by specific relation
  subtree(vocab_name, term_code, max_depth) -> hierarchical view for browsing

  # Metadata
  list_vocabularies() -> available vocabularies with stats
  info(vocab_name) -> vocabulary metadata (version, term count, relation types, source format)
```


## Data Model

```python
class VocabularyTerm:
    id: str
    label: str
    synonyms: list[str]
    definition: str | None
    parents: list[str]          # term IDs
    children: list[str]         # term IDs
    relationships: dict[str, list[str]]  # relation_type -> [term_ids]
    metadata: dict[str, str]    # source-specific fields

class VocabularyInfo:
    name: str
    strategy: str               # enum, tree, rag
    source_format: str          # obo, owl, json, csv, tsv
    version: str | None
    term_count: int
    relation_types: list[str]
```


## Vocabulary Registry

YAML config (`vocabularies.yaml`) defining available vocabularies:

```yaml
vocabularies:
  ensembl_biotypes:
    strategy: enum
    source: ensembl_biotypes.json

  sequence_ontology:
    strategy: tree
    source: so.obo

  gene_ontology:
    strategy: rag
    collection: gene_ontology
    embedding_config: default
    source: go.obo
```

Each strategy backend:
- **enum**: dict keyed by term code, loaded at first access, kept in memory.
- **tree**: adjacency list with typed edges, loaded at first access, kept in memory. Supports BFS/DFS for ancestor/descendant queries.
- **rag**: terms indexed into Chroma via existing `vectordb` module. Each document is `label | synonyms | definition`. Metadata stores id, parents, relationships. Hierarchy queries use metadata filters + graph traversal on stored relationships.


## Loader

`VocabularyLoader` reads source files and populates the appropriate backend:

- **OBO parser**: Handles GO, ChEBI, HPO, DO, SO, CL (standard OBO format). Extracts id, name, def, synonym, is_a, relationship, xref.
- **OWL/XML parser**: Handles OBI, EFO, NCIt, CDISC, Reactome. Uses `owlready2` or XML parsing for class hierarchy and object properties.
- **JSON/CSV/TSV parser**: Handles NDC, UNII (OpenFDA JSON), HGNC (TSV/JSON), Ensembl Biotypes, MeSH (XML), WikiPathways (GMT).
- **SNOMED-CT/RxNorm parser**: RF2 format (tab-separated concept/description/relationship files from UMLS).

The loader is run once per vocabulary (or on version update). For RAG vocabularies, it calls `vdb_add()` for each term. For tree/enum, it writes a processed JSON file for fast reload.


## Agent Integration

A tool-equipped agent that uses VocabularyConnector methods as PydanticAI tools. The agent can:
- Resolve ambiguous free-text to controlled terms (e.g., "heart attack" -> MI codes across MedDRA, SNOMED, DO)
- Validate a dataset column against a vocabulary and report mismatches
- Navigate ontology hierarchies to find appropriate level of specificity
- Cross-reference terms across vocabularies using xrefs (GO <-> KEGG, DO <-> ICD, NCIt <-> SNOMED)


## File Structure

```
agentic_patterns/core/connectors/
  vocabulary.py              # VocabularyConnector (static methods)
  vocabulary_loader.py       # VocabularyLoader (parsers, indexing)
  vocabulary_models.py       # VocabularyTerm, VocabularyInfo, VocabularyConfig
  vocabulary_registry.py     # Registry: load config, route to strategy backend
  vocabulary_backends/
    enum_backend.py          # In-memory dict backend
    tree_backend.py          # Tree/graph backend with traversal
    rag_backend.py           # Vector DB backend using existing vectordb module
```


## Example Vocabularies

All freely downloadable, covering pharma, genomics, and clinical trials:

 #  | Vocabulary | Domain | ~Size | Format | Strategy
----|-----------|--------|-------|--------|----------
 1  | Ensembl Biotypes | Genomics | 50 | JSON | enum
 2  | Sequence Ontology (SO) | Genomics | 2.5K | OBO | tree
 3  | Cell Ontology (CL) | Genomics | 2.7K | OBO | tree
 4  | Ontology of Biomedical Investigations (OBI) | Clinical/Lab | 4.5K | OWL | tree
 5  | WikiPathways | Pathways | 1.3K | GMT/RDF | tree
 6  | Disease Ontology (DO) | Disease | 12K | OBO | rag
 7  | Human Phenotype Ontology (HPO) | Phenotype | 17K | OBO | rag
 8  | MeSH | Biomedical | 30K | XML | rag
 9  | HGNC | Gene names | 43K | TSV/JSON | rag
10  | Gene Ontology (GO) | Molecular/Biological | 45K | OBO | rag
11  | Experimental Factor Ontology (EFO) | Experimental | 50K | OWL | rag
12  | ChEBI | Chemistry/Drugs | 60K | OBO | rag
13  | CDISC Terminology | Clinical trials | 70K | OWL/CSV | rag
14  | NDC Directory | Drug products (US) | 100K+ | JSON | rag
15  | UNII | Substances | 100K | JSON | rag
16  | RxNorm | Drug names | 115K | UMLS RF2 | rag
17  | NCI Thesaurus (NCIt) | Cancer/Clinical | 170K | OWL/OBO | rag
18  | Reactome | Pathways | 2.7K pathways | BioPAX/JSON | rag
19  | SNOMED-CT | Clinical | 300K+ | UMLS RF2 | rag
20  | NCBI Taxonomy | Organisms | 2.4M | Flat files | rag


## Implementation Order

### Phase 1 -- Skeleton with toy data

Build the full connector structure using small, hardcoded toy vocabularies (~10-20 terms per backend) so the interfaces, registry, backends, and tests can be validated end-to-end without downloading real ontology files.

1. Data model (`vocabulary_models.py`)
2. Enum backend with toy vocabulary (hardcoded JSON, ~10 terms)
3. Tree backend with toy hierarchical data (hardcoded, ~20 terms with parent/child relationships)
4. RAG backend using existing `vectordb` module with toy data
5. Vocabulary registry and YAML config
6. `VocabularyConnector` with full interface
7. Tests against toy vocabularies

### Phase 2 -- Real vocabularies and parsers

Add real-world vocabulary sources and their format-specific parsers. Each parser is an independent task since the backends are already proven.

8. OBO parser (covers GO, ChEBI, HPO, DO, SO, CL)
9. OWL parser (covers OBI, EFO, NCIt, CDISC, Reactome)
10. JSON/CSV/TSV parsers (NDC, UNII, HGNC, Ensembl, MeSH, WikiPathways)
11. UMLS RF2 parser (SNOMED-CT, RxNorm)
12. Agent integration (PydanticAI tools)
13. Examples for the book chapter

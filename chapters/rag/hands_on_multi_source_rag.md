## Hands-On: Multi-Source RAG

This hands-on demonstrates how to query multiple independent vector database collections through a unified retrieval interface and preserve source provenance in the generated answer. The example uses `example_RAG_03_multi_source.ipynb`.

### Setup: Two Independent Collections

The exercise ingests the same book texts used in previous examples, but this time splits them into two named collections: one for science fiction titles (`books_scifi`) and one for everything else (`books_other`). This simulates a realistic scenario where different document types are maintained in separate indices.

```python
from agentic_patterns.core.vectordb import get_vector_db
from agentic_patterns.core.doc_ingestion.models import DocumentProvenance

vdb_scifi = get_vector_db("books_scifi")
vdb_other = get_vector_db("books_other")

SCIFI_TITLES = {"hhgttg", "foundation"}

for txt_file in DOCS_DIR.glob("*.txt"):
    vdb = vdb_scifi if txt_file.stem in SCIFI_TITLES else vdb_other
    provenance = DocumentProvenance(original_file=txt_file, source=txt_file.stem)
    vdb.ingest_file(txt_file, provenance, force=False)
```

Each collection uses the same embedding model and the same chunking strategy (markdown-aware chunking, falling back to paragraph splitting). The only difference is which files are ingested into which collection.

### Querying with MultiSourceRetriever

`MultiSourceRetriever` holds a dictionary of named collections and queries all of them in parallel when `retrieve_all` is called.

```python
from agentic_patterns.core.vectordb.multi_source import MultiSourceRetriever

retriever = MultiSourceRetriever(sources={
    "scifi": vdb_scifi,
    "other": vdb_other,
})

results = retriever.retrieve_all(query="Who is Zaphod?", max_results=5)
for doc in results:
    source = doc.metadata.get("source_collection")
    print(f"[{source}] score={doc.score:.3f} | {doc.text[:80]}...")
```

The `source_collection` field is injected into each document's metadata by `retrieve_all` before returning results. Documents from different collections compete on score after rank normalization, and the final list is deduplicated by `doc_id`.

### Provenance in the Generation Prompt

The retrieved documents are formatted with their source collection name so the language model can include it in citations:

```python
context_blocks = []
for doc in results:
    source = doc.metadata.get("source_collection", "unknown")
    context_blocks.append(f"[{source}]\n{doc.text}")

context = "\n\n---\n\n".join(context_blocks)

prompt = f"""Answer the question using the sources below.
For each claim, cite the source in brackets (e.g. [scifi], [other]).

## Sources

{context}

## Question

{query}
"""
```

The separator `---` between blocks helps the model distinguish source boundaries. The instruction to cite sources in brackets is explicit: language models follow explicit citation conventions more reliably than implicit ones.

### What the Provenance Shows

Running the notebook with a query about Zaphod Beeblebrox produces results exclusively from the `scifi` collection. A query about general character archetypes in fiction might draw from both collections. The source labels in the response let users verify that claims originate from the expected domain—important in scenarios where source credibility varies (for example, authoritative documentation versus community-contributed content).

### Extending to Real Enterprise Scenarios

The pattern scales directly. An enterprise deployment might have collections for `product_docs`, `support_history`, `regulatory`, and `engineering_runbooks`. A query about a customer's error message would retrieve from `support_history` and `product_docs` and route away from `regulatory`. Adding a new source requires creating a new collection, ingesting documents, and adding it to the `sources` dictionary—no other code changes are required.

The `MultiSourceRetriever` can also be extended with per-source filters. If a user's session has access only to certain collections, the retriever's `sources` dictionary is constructed to include only those collections, enforcing access control at the retrieval layer without modifying the generation code.

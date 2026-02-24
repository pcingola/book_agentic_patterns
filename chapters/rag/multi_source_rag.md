## Multi-Source RAG & Evidence Grounding

Real-world RAG systems rarely operate over a single homogeneous corpus. Enterprise knowledge is distributed across product documentation, internal wikis, regulatory filings, support tickets, and structured databases. Each source has different update cadences, access controls, and reliability levels. Treating them all as a flat pool of documents loses this structure and forces every query to compete globally, which degrades precision and makes attribution impossible at the source level. Multi-source RAG addresses this by managing named, independent indices and presenting them through a unified retrieval interface.

#### Named indices and domain isolation

The core architectural decision in multi-source RAG is whether retrieval should be *federated* (each source queried independently, results merged) or *routed* (the query directed to one or a few sources based on its intent). Both approaches require treating each source as a first-class, named object rather than a segment of a shared index.

Domain isolation provides several practical benefits beyond architecture. Different domains may require different embedding models. Legal documents often benefit from models trained on legal corpora; code snippets are better served by code-aware embedders; general prose works well with general-purpose models. When sources are isolated, each collection can use the most appropriate embedder without compromise. Isolation also enables independent update schedules: a daily crawl of external news can be re-ingested without touching the curated product documentation that changes quarterly.

Access control is another reason to isolate indices. In multi-tenant systems, documents from one organization should never appear in another's retrieval results, even accidentally. A named collection that is provisioned per tenant enforces this boundary structurally rather than relying on post-retrieval filtering, which is error-prone.

#### Federated retrieval and result merging

Federated retrieval queries all named sources simultaneously and merges the results. The principal challenge is that similarity scores are not directly comparable across collections. A score of 0.82 from a dense technical documentation index reflects a different retrieval regime than a score of 0.82 from a sparse conversational knowledge base. Naive score-based merging can therefore produce rankings dominated by whichever source generates the highest raw scores.

Several strategies address this. Rank fusion combines results by their positions rather than their scores: documents are interleaved according to their rank in each source's result list. Reciprocal Rank Fusion is a common instance, assigning a weight to each document that is inversely proportional to its rank:

```python
def reciprocal_rank_fusion(results_per_source: dict[str, list], k: int = 60) -> list:
    scores: dict[str, float] = {}
    for source_results in results_per_source.values():
        for rank, doc in enumerate(source_results):
            doc_id = doc.doc_id
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

This approach is robust to score scale differences because it uses only rank ordering. The constant `k` controls the influence of lower-ranked documents: smaller values give more weight to top-ranked items.

Score normalization within each source before merging is an alternative. Each source's scores are linearly mapped to the range [0, 1], making them comparable. This preserves relative information within a source but loses the signal embedded in absolute score magnitude.

In practice, the right approach depends on the uniformity of the sources. When sources have similar domains and embedding models, score-based merging often works adequately. When sources are heterogeneous, rank-based fusion is safer.

#### Source metadata preservation and provenance

Every retrieved document must carry its source origin through the entire retrieval-generation pipeline. This is not merely useful for citation; it is structurally necessary for filtering, access control enforcement, and downstream evaluation.

In a multi-source system, each `RetrievedDocument` carries a `source_collection` field in its metadata, set at retrieval time. This field names the collection from which the document came, allowing the generator to distinguish a fact retrieved from regulatory guidance versus product documentation. At generation time, the language model can be instructed to cite sources by collection name, or the application layer can post-process citations into structured references.

```python
# Example: constructing the generation prompt with source attribution
context_blocks = []
for doc in retrieved:
    source = doc.metadata.get("source_collection", "unknown")
    context_blocks.append(f"[{source}] {doc.text}")

context = "\n\n".join(context_blocks)
prompt = f"Answer the question using the sources below.\n\n{context}\n\nQuestion: {query}"
```

The square-bracket prefix is a simple but effective convention: it forces the model to see source labels as part of the context, making it far more likely to include them in citations.

#### Evidence grounding

Evidence grounding is the practice of linking specific claims in a generated answer to specific retrieved passages that support them. While attribution at the document level answers "which sources were used?", evidence grounding answers "which passage supports this sentence?". This granularity is important in regulated industries, where answers may need to be audited against specific regulatory clauses, and in enterprise settings where incorrect answers must be traceable to their origin.

The simplest approach to evidence grounding is structured output. The language model is asked to produce answers as a list of claim–source pairs rather than free-form prose:

```python
class GroundedAnswer(BaseModel):
    claims: list[ClaimWithSource]

class ClaimWithSource(BaseModel):
    claim: str
    doc_id: str
    source_collection: str
    supporting_passage: str
```

By requiring the model to produce supporting passages alongside each claim, the system makes implicit reasoning explicit and auditable. Passages can be post-validated by checking whether they appear verbatim or near-verbatim in the retrieved documents, catching hallucinated citations.

A softer variant asks the model only for document identifiers and relies on semantic similarity to validate the link. This is less precise but more flexible when claims are synthesized from multiple passages rather than copied from a single one.

#### Query routing vs. broadcast retrieval

Broadcast retrieval (querying all sources every time) is the simplest approach and works well when the number of sources is small and queries are genuinely cross-cutting. As the number of sources grows, broadcast retrieval becomes expensive and may increase noise by retrieving weakly relevant results from tangentially related collections.

Query routing addresses this by selecting a subset of sources before retrieval. A lightweight router classifies the query into one or more source categories and limits retrieval to those collections. The router can be rule-based (pattern matching on query text), model-based (a small classifier trained on query–source pairs), or LLM-based (a prompt that asks which sources are relevant given the query and a description of each source).

```python
router_prompt = """
Given these sources:
- product_docs: Official product documentation and API reference
- support_history: Past support tickets and resolutions
- regulatory: Compliance and regulatory guidance

Which sources are relevant for this query? Return a JSON list of source names.

Query: {query}
"""
```

Routing reduces cost and latency at the price of recall: if the router incorrectly excludes a relevant source, those documents will never be seen. Hybrid strategies—always querying one or two core sources, routing for supplementary ones—balance these concerns.

#### Practical considerations

The design of a multi-source RAG system requires explicit decisions about index granularity, merge strategy, score calibration, and routing logic. These decisions interact: a fine-grained routing strategy can compensate for poor score calibration, while a coarser merge strategy is safer when routing is less reliable.

Operationally, multi-source systems benefit from monitoring per-source retrieval quality independently. A degraded collection (due to stale data, a schema change, or an embedding model update) may not be visible in aggregate metrics but can silently contaminate results. Source-level recall and precision metrics, tracked separately, make this visible.

Ultimately, multi-source RAG is less about adding sources and more about maintaining the integrity of the information flow from each source to the final answer. Named indices, preserved provenance, and explicit grounding are the mechanisms by which that integrity is upheld.

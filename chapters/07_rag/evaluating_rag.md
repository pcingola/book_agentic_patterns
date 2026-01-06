# Chapter 7: RAG

## Evaluating RAG Systems

**Evaluating a Retrieval-Augmented Generation (RAG) system means measuring, in a principled way, how well retrieval and generation jointly support factual, relevant, and grounded answers.**

### Historical perspective

Evaluation of RAG systems sits at the intersection of two older research traditions: information retrieval (IR) and natural language generation. Long before RAG, classical IR research in the 1960s–1990s focused on evaluating document retrieval quality using relevance judgments and set-based metrics such as precision and recall, formalized in early test collections like Cranfield and later standardized through TREC. These methods assumed a human reader as the final consumer of retrieved documents, not a generative model.

In parallel, natural language generation and question answering research developed its own evaluation practices, often relying on string-overlap metrics such as BLEU and ROUGE, or task-specific accuracy measures. With the emergence of neural open-domain QA in the 2010s, retrieval and generation began to merge, but evaluation was still typically split: retrieval was evaluated independently, and generation was evaluated against gold answers.

The first RAG-style systems, appearing around 2020 with dense retrieval and pretrained language models, exposed the limitations of this separation. A system could retrieve highly relevant documents yet fail to use them correctly, or produce fluent answers that were weakly grounded or even hallucinated. This led to a shift toward multi-level evaluation: measuring vector search quality, document retrieval effectiveness, and end-to-end answer quality together. More recent work emphasizes faithfulness, attribution, and robustness, reflecting the use of RAG in high-stakes and enterprise settings where correctness and traceability matter as much as surface-level answer quality.

---

## Evaluation layers in RAG systems

A modern RAG system is best evaluated as a pipeline with interacting components rather than a single black box. Each layer answers a different question: *are we retrieving the right things, are we selecting the right evidence, and does the final answer correctly use that evidence?*

### Metrics for vector search

Vector search evaluation focuses on the quality of nearest-neighbor retrieval in embedding space, independent of any downstream generation. The goal is to assess whether semantically relevant items are geometrically close to the query embedding.

Typical metrics are based on ranked retrieval. Recall@k measures whether at least one relevant item appears in the top-k results, which is particularly important in RAG because downstream components only see a small retrieved set. Precision@k captures how many of the retrieved items are relevant, but is often secondary to recall in early retrieval stages. Mean Reciprocal Rank (MRR) emphasizes how early the first relevant item appears, reflecting latency-sensitive pipelines. Normalized Discounted Cumulative Gain (nDCG) generalizes these ideas when relevance is graded rather than binary.

In practice, vector search evaluation requires a labeled dataset of queries paired with relevant documents or passages. These labels are often incomplete or noisy, which is why recall-oriented metrics are preferred: they are more robust to missing judgments.

```python
def recall_at_k(retrieved_ids, relevant_ids, k):
    top_k = set(retrieved_ids[:k])
    return int(len(top_k & relevant_ids) > 0)
```

This level of evaluation answers the question: *given a query embedding, does the vector index surface semantically relevant candidates?* It does not tell us whether these candidates are actually useful for answering the question.

---

### Metrics for document retrieval

Document retrieval metrics evaluate the effectiveness of the full retrieval stack, which may include query rewriting, filtering, hybrid search, and re-ranking. Unlike pure vector search, this level is concerned with the *final set of documents passed to the generator*.

The same families of metrics—Recall@k, MRR, and nDCG—are commonly used, but the unit of relevance is often more task-specific. Relevance may be defined as containing sufficient evidence to answer the question, not merely semantic similarity. This distinction is critical: a document can be topically related yet useless for grounding an answer.

Evaluation at this level often relies on human annotation or weak supervision, such as matching retrieved passages against known supporting facts. In enterprise systems, retrieval quality is frequently evaluated by measuring coverage over authoritative sources, policy documents, or curated knowledge bases.

Conceptually, this layer answers: *does the system retrieve the right evidence, in the right form, for generation?*

---

### End-to-end RAG metrics

End-to-end evaluation treats the RAG system as a whole and measures the quality of the final answer. This is the most user-visible layer and the hardest to evaluate reliably.

Traditional generation metrics such as exact match, F1, BLEU, or ROUGE are sometimes used when gold answers are available, but they are poorly aligned with the goals of RAG. A correct answer phrased differently may score poorly, while an answer that matches the gold text but is unsupported by retrieved evidence may score well.

As a result, modern RAG evaluation increasingly emphasizes three complementary properties. **Answer correctness** measures whether the answer is factually correct with respect to a reference or authoritative source. **Groundedness or faithfulness** measures whether the answer can be directly supported by the retrieved documents. **Attribution quality** measures whether the system correctly cites or points to the evidence it used.

LLM-based judges are often used to operationalize these criteria by comparing the answer against retrieved context and scoring dimensions such as correctness and support. While imperfect, this approach scales better than manual evaluation and aligns more closely with real-world usage.

```python
def judge_groundedness(answer, context):
    prompt = f"""
    Is the answer fully supported by the context?
    Answer: {answer}
    Context: {context}
    """
    return call_llm(prompt)
```

This level answers the question users actually care about: *does the system produce a correct, well-supported answer?*

---

## Measuring improvements in RAG systems

Evaluating a single snapshot of a RAG system is rarely sufficient. What matters in practice is measuring *improvement* as the system evolves.

A common baseline is a non-RAG model that answers questions without retrieval. Comparing end-to-end performance against this baseline isolates the value added by retrieval. If RAG does not outperform a strong non-RAG baseline, retrieval may be unnecessary or poorly integrated.

Ablation studies are equally important. By selectively disabling components—such as query rewriting, re-ranking, or metadata filtering—one can measure their marginal contribution. This helps avoid overfitting to complex pipelines whose benefits are not well understood.

Offline metrics should be complemented with online or human-in-the-loop evaluation where possible. User feedback, answer acceptance rates, and error analysis often reveal failure modes that are invisible to automated metrics, such as subtle hallucinations or missing caveats.

Taken together, these practices shift evaluation from a one-time score to a continuous measurement discipline, which is essential for maintaining reliable RAG systems in production.

---

## References

1. Voorhees, E. M., and Harman, D. *TREC: Experiment and Evaluation in Information Retrieval*. MIT Press, 2005.
2. Karpukhin, V., et al. *Dense Passage Retrieval for Open-Domain Question Answering*. EMNLP, 2020. [https://arxiv.org/abs/2004.04906](https://arxiv.org/abs/2004.04906)
3. Lewis, P., et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS, 2020. [https://arxiv.org/abs/2005.11401](https://arxiv.org/abs/2005.11401)
4. Thorne, J., et al. *Evidence-based Fact Checking with Retrieval-Augmented Models*. EMNLP, 2018.
5. Gao, T., et al. *RARR: Researching and Revising What Language Models Say, Using Language Models*. ACL, 2023. [https://arxiv.org/abs/2210.08726](https://arxiv.org/abs/2210.08726)

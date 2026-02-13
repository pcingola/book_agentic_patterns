## Hands-On: Advanced Document Ingestion and Retrieval

This hands-on explores techniques that improve upon the basic RAG pipeline: semantic chunking during ingestion and multi-stage retrieval with query expansion, filtering, and re-ranking. The examples use `example_RAG_02_load.ipynb` for LLM-based chunking and `example_RAG_02_query.ipynb` for advanced retrieval.

### Why Go Beyond Simple RAG

The simple paragraph-based chunking from the previous example works well when document structure aligns with semantic boundaries. But real documents often violate this assumption. A conversation might span multiple paragraphs. A technical explanation might flow continuously without clear breaks. Naive chunking splits these coherent units, forcing the retriever to find multiple partial chunks that together contain the answer.

Similarly, simple retrieval assumes the user's query directly matches how information is expressed in the documents. In practice, users ask questions in many ways, and a single embedding might miss relevant passages that use different terminology. The advanced retrieval techniques address these limitations by expanding queries, filtering results, and re-ranking for precision.

### Part 1: LLM-Based Semantic Chunking

The ingestion notebook (`example_RAG_02_load.ipynb`) replaces naive paragraph splitting with an LLM that identifies semantic boundaries.

#### The Chunking Prompt

The LLM receives explicit instructions about what makes a good chunk:

```python
CHUNKING_PROMPT = """
You are a text chunking assistant. Your task is to divide the following text into coherent chunks based on topics or themes.

Guidelines:
- Each chunk should be self-contained and focus on a single topic, scene, or theme
- Chunks should be substantial (at least a few sentences) but not too long
- Preserve the original text exactly - do not summarize or modify the content
- Return the chunks as a list of strings
- IMPORTANT: If the text ends mid-topic (incomplete), include that partial content as the LAST chunk so it can be continued in the next batch

TEXT TO CHUNK:
{text}
"""

chunking_agent = get_agent(config_name="fast", output_type=list[str])
```

The prompt emphasizes self-containment and topic coherence. Unlike heuristic approaches that count characters or split on punctuation, the LLM understands when a scene changes or a new concept begins. The instruction to preserve text exactly prevents the LLM from summarizing, which would lose detail needed for retrieval.

The `output_type=list[str]` ensures structured output. The LLM returns a list of strings rather than free-form text, making the result directly usable without parsing.

#### Batching for Large Documents

Documents often exceed LLM context limits. The notebook addresses this with a batching strategy that splits at natural boundaries:

```python
BATCH_SIZE_CHARS = 15000

def split_into_batches(text: str, batch_size: int) -> list[str]:
    """Split text into batches by paragraphs, respecting batch_size limit."""
    paragraphs = text.split('\n\n')
    batches = []
    current_batch = []
    current_size = 0

    for para in paragraphs:
        para_size = len(para) + 2
        if current_size + para_size > batch_size and current_batch:
            batches.append('\n\n'.join(current_batch))
            current_batch = [para]
            current_size = para_size
        else:
            current_batch.append(para)
            current_size += para_size

    if current_batch:
        batches.append('\n\n'.join(current_batch))

    return batches
```

The function splits on paragraph boundaries rather than at arbitrary character positions. This prevents breaking mid-sentence and gives the LLM complete paragraphs to work with. Each batch stays under 15000 characters, roughly 3000-4000 tokens, leaving headroom for the prompt template and LLM response.

#### Handling Incomplete Chunks Across Batches

When batch boundaries fall in the middle of a semantic unit, the last chunk from one batch might be incomplete. The notebook handles this with a "leftover" strategy:

```python
async def chunk_with_llm(file: Path) -> list[tuple[str, str, dict]]:
    text = file.read_text()
    batches = split_into_batches(text, BATCH_SIZE_CHARS)

    all_chunks = []
    leftover = ""

    for batch_num, batch in enumerate(batches):
        batch_text = leftover + batch if leftover else batch
        leftover = ""

        prompt = CHUNKING_PROMPT.format(text=batch_text)
        agent_run, _ = await run_agent(chunking_agent, prompt, verbose=False)
        chunks: list[str] = agent_run.result.output

        if batch_num < len(batches) - 1 and chunks:
            leftover = chunks.pop()

        all_chunks.extend(chunks)

    if leftover:
        all_chunks.append(leftover)
```

The key insight is that the LLM is instructed to place potentially incomplete content in the last chunk. By removing that last chunk and prepending it to the next batch, the LLM sees the incomplete content with additional context and can properly determine where the semantic boundary falls. This approach maintains coherence across arbitrary batch boundaries without requiring the LLM to see the entire document at once.

### Part 2: Advanced Retrieval

The retrieval notebook (`example_RAG_02_query.ipynb`) demonstrates a multi-stage pipeline that improves upon direct similarity search.

#### Query Expansion

A single query embedding might miss relevant documents that express the same concept differently. Query expansion generates multiple reformulations:

```python
prompt = f"""
Given the following user query, reformulate the query in three to five different ways to retrieve relevant documents from the vector database.

{query}
"""

agent = get_agent(output_type=list[str])
agent_run, nodes = await run_agent(agent, prompt=prompt, verbose=True)
reformulated_queries = agent_run.result.output
```

For a query like "Who is a man with two heads?", the LLM might generate variations like "character with multiple heads", "person with two heads description", and "dual-headed individual". Each reformulation captures a different lexical angle on the same semantic intent. Querying with all variations increases recall because documents matching any phrasing will be retrieved.

#### Multi-Query Retrieval with Metadata Filtering

Each reformulated query runs against the vector database with a metadata filter applied at query time:

```python
book_name = 'hhgttg'
metadata_filter = {'source': book_name}

documents_with_scores = []
for q in reformulated_queries:
    documents_with_scores.extend(vdb_query(vdb, query=q, filter=metadata_filter))
```

The `filter` parameter restricts results at the database level, which is more efficient than filtering after retrieval. This filter restricts results to a specific book. In production systems, metadata filtering handles access control (only documents the user is authorized to see), temporal constraints (only documents from a certain time period), or domain restrictions (only documents from a particular category).

The same document might appear multiple times if it matches several reformulations. This duplication is handled in the next stage.

#### Deduplication

The combined results need deduplication to remove repeated documents:

```python
seen_ids = set()
documents_deduplicated = []
for doc, meta, score in documents_with_scores:
    doc_id = f"{meta['source']}-{meta['chunk']}"
    if doc_id in seen_ids:
        continue
    documents_deduplicated.append((doc, meta, score, doc_id))
    seen_ids.add(doc_id)
```

The document ID constructed from source and chunk number provides a unique key. Documents that appear in multiple query results are kept only once.

#### Sorting and Limiting

The results are sorted by similarity score and limited to a manageable number:

```python
documents_sorted = sorted(documents_deduplicated, key=lambda x: x[2], reverse=True)

max_results = 10
if len(documents_sorted) > max_results:
    documents_sorted = documents_sorted[:max_results]
```

This example uses a simple score-based sort. Production systems often use cross-encoder models that jointly encode the query and document to produce more accurate relevance scores. The computational cost of cross-encoders makes them impractical for the initial search over thousands of documents, but they work well for re-ranking a small candidate set.

The `max_results` limit caps how many documents enter the final prompt. More documents provide more context but increase token usage and may dilute the most relevant passages.

#### Building the Final Prompt

The filtered, deduplicated, sorted documents become context for the LLM:

```python
docs_str = ''
for doc, meta, score, doc_id in documents_sorted:
    docs_str += f"Similarity Score: {score:.3f}\nDocument ID: {doc_id}\nDocument:\n{doc}\n\n"

prompt = f"""
Given the following documents, answer the user's question.
Show used references (using document ids).

## Documents

{docs_str}

## User's question

{query}
"""
```

Including document IDs enables citation. The LLM can reference specific documents in its answer, allowing users to trace claims back to sources. This transparency is valuable in applications where users need to verify the LLM's reasoning.

### The Cost-Quality Tradeoff

The advanced techniques in this hands-on improve retrieval quality but increase cost and latency. LLM-based chunking requires one or more LLM calls per document during ingestion. Query expansion adds an LLM call per query. These costs should be weighed against the improvement in retrieval quality for your specific use case.

For small corpora with well-structured documents, simple paragraph chunking and direct retrieval may suffice. For large, heterogeneous corpora where retrieval precision matters, the investment in semantic chunking and multi-stage retrieval pays off in better answers.

### Connection to the Chapter

The techniques demonstrated here correspond to concepts from the chapter sections on document ingestion and retrieval. LLM-based chunking implements the topic-aware segmentation described in the ingestion section. Query expansion, filtering, and re-ranking implement stages of the retrieval pipeline described in the retrieval section. The code makes these abstract concepts concrete and runnable.

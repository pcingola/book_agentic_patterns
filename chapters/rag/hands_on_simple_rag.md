## Hands-On: Simple Document Ingestion and Retrieval

This hands-on walks through the fundamental RAG pipeline: ingesting documents into a vector database and retrieving relevant passages to augment LLM prompts. The examples use `example_RAG_01_load.ipynb` for ingestion and `example_RAG_01_query.ipynb` for retrieval.

### The RAG Pipeline

RAG systems operate in two distinct phases. The ingestion phase transforms raw documents into searchable embeddings stored in a vector database. This happens once, or whenever the corpus changes. The retrieval phase takes a user query, finds semantically similar documents, and uses them to ground the LLM's response. This happens on every query.

The separation matters because ingestion is expensive (embedding all documents) while retrieval is cheap (embedding one query and looking up neighbors). A well-designed RAG system invests heavily in ingestion quality because that investment pays off across all subsequent queries.

### Part 1: Document Ingestion

The ingestion notebook (`example_RAG_01_load.ipynb`) demonstrates the three core steps: loading documents, chunking them, and storing the chunks as embeddings.

#### Setting Up the Vector Database

The notebook begins by creating a connection to a Chroma vector database:

```python
from agentic_patterns.core.vectordb import get_vector_db, vdb_add

vdb = get_vector_db('books')
```

The `get_vector_db` function handles database initialization and configuration. The collection name `'books'` identifies this particular set of documents. Chroma persists the data to disk, so the database survives across notebook sessions.

Before loading documents, the notebook checks whether the collection is empty:

```python
count = vdb.count()
create_vdb = (count == 0)
```

This check prevents duplicate ingestion. If documents are already loaded, the notebook skips re-ingestion. This pattern is important in practice: you want ingestion to be idempotent so that rerunning the notebook doesn't create duplicate entries.

#### Chunking Strategy

The chunking function splits documents into paragraphs:

```python
def chunks(file: Path, min_lines: int = 3):
    """Chunk a book into paragraphs, returning (document, doc_id, metadata) tuples."""
    text = file.read_text()
    paragraphs = text.split('\n\n')
    for paragraph_num, paragraph in enumerate(paragraphs):
        doc = paragraph.strip()
        if not doc or len(doc.strip().split('\n')) < min_lines:
            continue
        doc_id = f"{file.stem}-{paragraph_num}"
        metadata = {'source': str(file.stem), 'paragraph': paragraph_num}
        yield doc, doc_id, metadata
```

This is the simplest useful chunking strategy: split on double newlines (paragraph boundaries) and filter out chunks that are too short. Each chunk receives a unique ID and metadata tracking its source file and position. The metadata becomes important during retrieval for citation and filtering.

The `min_lines` filter removes trivial chunks like chapter headings or blank sections. Without this filter, the vector database would fill with short, semantically weak chunks that add noise to retrieval results.

#### Loading Documents

The loading loop processes each text file and adds its chunks to the database:

```python
for txt_file in DOCS_DIR.glob('*.txt'):
    for doc, doc_id, meta in chunks(txt_file):
        vdb_add(vdb, text=doc, doc_id=doc_id, meta=meta)
```

The `vdb_add` function handles embedding generation internally. Each chunk is converted to a dense vector and stored alongside its text and metadata. The document ID ensures that re-ingesting the same document updates rather than duplicates entries.

### Part 2: Document Retrieval

The retrieval notebook (`example_RAG_01_query.ipynb`) demonstrates querying the vector database and using retrieved documents to augment an LLM prompt.

#### Querying the Vector Database

The query process starts by embedding the user's question and finding similar documents:

```python
from agentic_patterns.core.vectordb import get_vector_db, vdb_query

vdb = get_vector_db('books')
query = "Who is a man with two heads?"
documents_with_scores = vdb_query(vdb, query=query)
```

The `vdb_query` function converts the query string to an embedding using the same model that embedded the documents. It then performs a similarity search, returning the closest matches along with their similarity scores and metadata.

The returned list contains tuples of `(document_text, metadata, score)`. The score indicates semantic similarity: higher scores mean the document is more relevant to the query. These scores help in two ways: they order results by relevance, and they provide a signal for filtering out weak matches.

#### Building the Augmented Prompt

The retrieved documents become part of the LLM prompt:

```python
docs_str = ''
for doc, meta, score in documents_with_scores:
    docs_str += f"Similarity Score: {score:.3f}\nDocument:\n{doc}\n\n"

prompt = f"""
Given the following documents, answer the question:

{docs_str}

Question:
{query}
"""
```

This prompt structure is the essence of RAG. Instead of asking the LLM to answer from its training data alone, we provide specific documents that should contain the answer. The LLM's job shifts from recall to comprehension: it reads the provided documents and synthesizes an answer.

Including the similarity score in the prompt is optional but can help the LLM weight its confidence. A document with score 0.95 is a strong match; one with score 0.60 might be tangentially relevant.

#### Generating the Answer

The augmented prompt goes to the LLM:

```python
from agentic_patterns.core.agents import get_agent, run_agent

agent = get_agent()
answer, nodes = await run_agent(agent, prompt=prompt, verbose=True)
```

The LLM now has access to relevant passages from the corpus. If the question asks about a character from a book, and the retrieved documents contain paragraphs describing that character, the LLM can answer accurately even if that information wasn't in its training data.

### Why This Pattern Works

The RAG pattern succeeds because it separates concerns. Embeddings capture semantic similarity without requiring exact keyword matches. Vector search scales to large corpora with sub-linear query time. LLMs excel at reading comprehension and synthesis but struggle with precise recall. By combining these components, RAG gets the best of each: broad semantic matching, efficient retrieval, and fluent answer generation.

The simple paragraph-based chunking in this example works well for narrative text where paragraphs correspond to coherent units of meaning. For technical documentation, code, or structured data, more sophisticated chunking strategies (covered in later examples) may be needed.

### Limitations of Simple RAG

This basic implementation has several limitations that motivate the advanced techniques covered in subsequent examples.

The paragraph chunking is naive. It doesn't consider semantic boundaries, so a topic that spans two paragraphs gets split into separate chunks. A query might retrieve only half of the relevant context.

The retrieval uses a single query. If the user's question could be phrased multiple ways, the system might miss relevant documents that match an alternate phrasing. Query expansion addresses this.

There's no re-ranking. The initial similarity scores from the vector database are approximate. A dedicated re-ranker that jointly considers query-document pairs can improve precision, especially at the top of the ranking.

There's no metadata filtering. In a production system, you might want to restrict retrieval to documents from a specific time period, author, or category. The metadata is captured during ingestion but not used during retrieval in this basic example.

These limitations don't diminish the value of the simple approach. For many use cases, paragraph chunking and direct retrieval work well. The advanced techniques add complexity that should be justified by measured improvements in retrieval quality for your specific domain.

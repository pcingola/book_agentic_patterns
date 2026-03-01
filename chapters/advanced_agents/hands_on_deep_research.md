## Hands-On: Deep Research Agent

This exercise (`example_deep_research.ipynb`) builds a deep research agent that decomposes a broad question into sub-queries, retrieves evidence from multiple sources across iterations, detects conflicts, and synthesises a structured report with references.

### Setup

Set your Perplexity API key in `config.yaml` before running:

```yaml
search:
  perplexity:
    api_key: your-perplexity-api-key
    model: sonar
    api_url: https://api.perplexity.ai
```

### Running the agent

`DeepResearchAgent` loads Perplexity from `config.yaml` automatically. Set `max_iterations` to control how many gap-filling rounds it performs before synthesis:

```python
from agentic_patterns.agents.research import DeepResearchAgent

agent = DeepResearchAgent(max_iterations=2)

report = await agent.run(
    "What are the current best practices for LLM evaluation in production systems?"
)
```

The agent runs six steps internally: decompose the question into sub-questions, search all sources in parallel for each, assess evidence gaps and re-query (up to `max_iterations` times), detect conflicts across results, then synthesise a final report.

### Displaying the report

`report.content` is a markdown string with inline citation markers (`[1]`, `[2]`, etc.):

```python
from IPython.display import Markdown, display

display(Markdown(report.content))
```

### Structured references

`report.references` is a list of `Reference` objects. Each has `title`, `url`, `snippet`, and `source_type` (`"web"` or `"vectordb"`):

```python
for i, ref in enumerate(report.references, 1):
    print(f"[{i}] ({ref.source_type}) {ref.title}")
    if ref.url:
        print(f"    {ref.url}")
    print(f"    {ref.snippet[:120]}..." if len(ref.snippet) > 120 else f"    {ref.snippet}")
```

### Multi-source research (web + VectorDB)

Pass explicit sources to combine Perplexity with a local vector database:

```python
from agentic_patterns.core.vectordb.vectordb import get_vector_db
from agentic_patterns.agents.research import SearchSourcePerplexity, SearchSourceVectorDB

vdb_source = SearchSourceVectorDB(get_vector_db("my_collection"))

agent_multi = DeepResearchAgent(sources=[SearchSourcePerplexity.from_config(), vdb_source])
report_multi = await agent_multi.run("How does our internal API handle rate limiting?")
display(Markdown(report_multi.content))
```

Sources are queried in parallel for each sub-question; results from all sources are merged before gap assessment and synthesis.

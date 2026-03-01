# Deep Research Agent

An iterative research agent that decomposes questions, searches multiple sources in parallel, detects gaps and conflicts, and synthesizes a markdown report with inline citations and structured references.

Uses `get_agent()` directly (not `OrchestratorAgent`) since the research loop is a fixed protocol. Same pattern as `RedTeamAgent` and `DebateOrchestrator`.

Prompts live in `prompts/research/`.


## Search Sources

The agent queries pluggable search sources via a `SearchSource` protocol. Two implementations are provided.

`SearchSourcePerplexity` calls the Perplexity Sonar API (OpenAI-compatible endpoint) for web search. Configuration goes in `config.yaml` under `search.perplexity` with `api_key`, `model` (default: `sonar`), and `api_url`.

`SearchSourceVectorDB` wraps an existing `VectorDB` instance for local/private search. It calls `vdb.retrieve()` and maps `RetrievedDocument` objects to `SearchResult`.

```python
from agentic_patterns.agents.research import (
    SearchSourcePerplexity,
    SearchSourceVectorDB,
)
from agentic_patterns.core.vectordb.vectordb import get_vector_db

web = SearchSourcePerplexity(api_key="...", model="sonar")
vdb = SearchSourceVectorDB(get_vector_db("my_collection"))
```


## Research Loop

The `DeepResearchAgent.run(question)` method executes:

1. **Decompose** -- LLM breaks the question into 3-7 sub-questions.
2. **Search** -- For each sub-question, query all sources in parallel. Accumulate evidence.
3. **Assess gaps** -- LLM identifies sub-questions with insufficient evidence.
4. **Re-query** -- For each gap, reformulate and search again. Repeats up to `max_iterations`.
5. **Detect conflicts** -- LLM finds contradictions across accumulated evidence.
6. **Synthesize** -- LLM produces a markdown report with `[N]` citation markers and a structured reference list.

```python
from agentic_patterns.agents.research import DeepResearchAgent

agent = DeepResearchAgent(sources=[web, vdb], max_iterations=2)
report = await agent.run("What are the best practices for LLM evaluation?")
print(report.content)
for ref in report.references:
    print(f"[{ref.source_type}] {ref.title}: {ref.url}")
```


## Output

`ResearchReport` contains `content` (markdown with `[N]` citation markers) and `references: list[Reference]`. Each `Reference` has `url`, `title`, `snippet`, and `source_type` ("web" or "vectordb").


## API Reference

### `agentic_patterns.agents.research.source`

| Name | Kind | Description |
|---|---|---|
| `SearchResult` | Pydantic model | content, url, title, source_type |
| `SearchSource` | Protocol | `async search(query) -> list[SearchResult]` |
| `SearchSourcePerplexity(api_key, model, api_url)` | Class | Perplexity Sonar web search |
| `SearchSourceVectorDB(vdb)` | Class | Local VectorDB search |

### `agentic_patterns.agents.research.models`

| Name | Kind | Description |
|---|---|---|
| `Reference` | Pydantic model | url, title, snippet, source_type |
| `ResearchReport` | Pydantic model | content (markdown), references: list[Reference] |

### `agentic_patterns.agents.research.agent`

| Name | Kind | Description |
|---|---|---|
| `DeepResearchAgent(sources, config_name, max_iterations)` | Class | Iterative deep research agent |
| `DeepResearchAgent.run(question)` | Method | Returns ResearchReport |


## Examples

See `agentic_patterns/examples/advanced_agents/example_deep_research.ipynb` for a hands-on walkthrough covering single-source (Perplexity) research and multi-source (web + VectorDB) research.

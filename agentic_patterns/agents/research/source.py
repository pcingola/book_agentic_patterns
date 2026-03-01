"""Search source protocol and implementations for the deep research agent."""

import logging
import ssl
from typing import Protocol, runtime_checkable

import httpx
import yaml
from pydantic import BaseModel

from agentic_patterns.core.config.config import MAIN_PROJECT_DIR

logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    """A single result returned by a search source."""

    content: str
    url: str
    title: str
    source_type: str  # "web" or "vectordb"

    def __str__(self) -> str:
        return f"SearchResult({self.title!r}, {self.source_type})"


@runtime_checkable
class SearchSource(Protocol):
    async def search(self, query: str) -> list[SearchResult]: ...


class SearchSourcePerplexity:
    """Calls Perplexity Sonar API (OpenAI-compatible) for web search."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "sonar",
        api_url: str = "https://api.perplexity.ai",
    ):
        self._api_key = api_key
        self._model = model
        self._api_url = api_url.rstrip("/")

    async def search(self, query: str) -> list[SearchResult]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": query}],
        }
        async with httpx.AsyncClient(
            timeout=60, verify=ssl.create_default_context()
        ) as client:
            resp = await client.post(
                f"{self._api_url}/chat/completions", headers=headers, json=payload
            )
            if resp.status_code == 401:
                raise PermissionError(
                    "Perplexity API key is missing or invalid. Check 'search.perplexity.api_key' in config.yaml."
                )
            resp.raise_for_status()
            data = resp.json()

        answer = data["choices"][0]["message"]["content"]
        citations: list[str] = data.get("citations", [])

        if not citations:
            return [
                SearchResult(
                    content=answer, url="", title="Perplexity answer", source_type="web"
                )
            ]

        results = []
        for i, url in enumerate(citations):
            results.append(
                SearchResult(
                    content=answer, url=url, title=f"Source {i + 1}", source_type="web"
                )
            )
        return results

    @classmethod
    def from_config(cls) -> "SearchSourcePerplexity":
        """Load configuration from config.yaml (section search.perplexity)."""
        with open(MAIN_PROJECT_DIR / "config.yaml") as f:
            cfg = yaml.safe_load(f)
        p = cfg["search"]["perplexity"]
        return cls(
            api_key=p["api_key"],
            model=p.get("model", "sonar"),
            api_url=p.get("api_url", "https://api.perplexity.ai"),
        )

    def __str__(self) -> str:
        return f"SearchSourcePerplexity(model={self._model!r})"


class SearchSourceVectorDB:
    """Wraps an existing VectorDB for local/private search."""

    def __init__(self, vdb: "VectorDB"):  # noqa: F821
        self._vdb = vdb

    async def search(self, query: str) -> list[SearchResult]:
        docs = self._vdb.retrieve(query, max_results=5)
        results = []
        for doc in docs:
            url = doc.metadata.get("url", doc.metadata.get("source", ""))
            title = doc.metadata.get("title", doc.doc_id)
            results.append(
                SearchResult(
                    content=doc.text, url=url, title=title, source_type="vectordb"
                )
            )
        return results

    def __str__(self) -> str:
        return f"SearchSourceVectorDB({self._vdb})"

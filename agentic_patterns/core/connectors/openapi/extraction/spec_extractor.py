"""API specification extraction orchestrator."""

import json
from pathlib import Path
from typing import Any

import requests
import yaml

from agentic_patterns.core.connectors.openapi.extraction.spec_parser import ApiSpecParser
from agentic_patterns.core.connectors.openapi.models import ApiInfo


class ApiSpecExtractor:
    """Extracts API specifications from URLs or files."""

    def __init__(self, api_id: str, base_url: str | None = None):
        self.api_id = api_id
        self.base_url = base_url
        self.spec_dict: dict[str, Any] | None = None
        self.parser: ApiSpecParser | None = None

    def connect(self, spec_source: str) -> "ApiSpecExtractor":
        """Fetch spec from URL or file and create parser.

        If base_url was provided to constructor (from config), it will be used
        for API requests instead of the spec's servers section.
        """
        # Determine if source is URL or file
        if spec_source.startswith(("http://", "https://")):
            self.spec_dict = self._fetch_from_url(spec_source)
        else:
            self.spec_dict = self._load_from_file(Path(spec_source))

        # Create parser based on spec format
        from agentic_patterns.core.connectors.openapi.factories import create_spec_parser
        self.parser = create_spec_parser(self.spec_dict, self.api_id, self.base_url)

        return self

    def api_info(self, cache: bool = True) -> ApiInfo:
        """Extract ApiInfo from spec."""
        if self.parser is None:
            raise RuntimeError("Must call connect() before api_info()")

        api_info = self.parser.parse()

        if cache:
            api_info.save()

        return api_info

    def _fetch_from_url(self, url: str) -> dict:
        """Fetch OpenAPI spec from URL."""
        from agentic_patterns.core.connectors.openapi.config import MAX_RETRIES, REQUEST_TIMEOUT

        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()

                # Detect format from content type or URL
                content_type = response.headers.get("content-type", "")
                if "json" in content_type or url.endswith(".json"):
                    return response.json()
                elif "yaml" in content_type or url.endswith((".yaml", ".yml")):
                    return yaml.safe_load(response.text)
                else:
                    # Try JSON first, then YAML
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        return yaml.safe_load(response.text)

            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise RuntimeError(f"Failed to fetch spec from {url}: {e}")

        raise RuntimeError(f"Failed to fetch spec from {url} after {MAX_RETRIES} attempts")

    def _load_from_file(self, path: Path) -> dict:
        """Load OpenAPI spec from file."""
        if not path.exists():
            raise FileNotFoundError(f"Spec file not found: {path}")

        content = path.read_text()

        # Detect format from extension
        if path.suffix == ".json":
            return json.loads(content)
        elif path.suffix in [".yaml", ".yml"]:
            return yaml.safe_load(content)
        else:
            # Try JSON first, then YAML
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return yaml.safe_load(content)

    def __enter__(self) -> "ApiSpecExtractor":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

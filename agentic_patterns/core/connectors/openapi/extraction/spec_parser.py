"""Abstract base class for OpenAPI specification parsers."""

from abc import ABC, abstractmethod

from agentic_patterns.core.connectors.openapi.models import ApiInfo


class ApiSpecParser(ABC):
    """Base class for parsing API specifications into ApiInfo objects."""

    def __init__(self, spec_dict: dict, api_id: str, base_url: str | None = None):
        self.spec_dict = spec_dict
        self.api_id = api_id
        self.base_url = base_url

    @abstractmethod
    def parse(self) -> ApiInfo:
        """Parse the specification and return ApiInfo."""
        pass

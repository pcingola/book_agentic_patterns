"""Abstract base class for HTTP clients."""

from abc import ABC, abstractmethod


class ApiHttpClient(ABC):
    """Base class for making HTTP requests to APIs."""

    def __init__(self, api_id: str, base_url: str):
        self.api_id = api_id
        self.base_url = base_url.rstrip("/")

    @abstractmethod
    def request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        headers: dict | None = None,
        json: dict | None = None,
        data: str | None = None,
    ) -> dict:
        """
        Make an HTTP request.

        Returns a dict with:
            - status_code: int
            - headers: dict
            - body: dict | str | None
        """
        pass

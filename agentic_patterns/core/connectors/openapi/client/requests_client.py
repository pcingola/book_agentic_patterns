"""HTTP client implementation using requests library."""

import asyncio
import json as json_module
from functools import partial

import requests

from agentic_patterns.core.connectors.openapi.client.http_client import ApiHttpClient
from agentic_patterns.core.connectors.openapi.config import MAX_RETRIES, REQUEST_TIMEOUT


class RequestsApiClient(ApiHttpClient):
    """HTTP client using requests library (sync with async wrapper)."""

    def request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        headers: dict | None = None,
        json: dict | None = None,
        data: str | None = None,
    ) -> dict:
        """Make an HTTP request with retry logic."""
        url = (
            f"{self.base_url}{path}"
            if path.startswith("/")
            else f"{self.base_url}/{path}"
        )

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    headers=headers,
                    json=json,
                    data=data,
                    timeout=REQUEST_TIMEOUT,
                )

                # Parse response body
                body = None
                content_type = response.headers.get("content-type", "")
                if response.content:
                    if "application/json" in content_type:
                        try:
                            body = response.json()
                        except json_module.JSONDecodeError:
                            body = response.text
                    else:
                        body = response.text

                return {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": body,
                }

            except Exception as e:
                last_error = e
                if attempt == MAX_RETRIES - 1:
                    return {
                        "status_code": 0,
                        "headers": {},
                        "body": f"Request failed after {MAX_RETRIES} attempts: {e}",
                    }

        # Fallback (should not reach here)
        return {
            "status_code": 0,
            "headers": {},
            "body": f"Request failed: {last_error}",
        }

    async def request_async(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        headers: dict | None = None,
        json: dict | None = None,
        data: str | None = None,
    ) -> dict:
        """Async wrapper around synchronous request method."""
        loop = asyncio.get_event_loop()
        func = partial(self.request, method, path, params, headers, json, data)
        return await loop.run_in_executor(None, func)

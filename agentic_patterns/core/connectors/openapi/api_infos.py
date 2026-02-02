"""API metadata and client registry."""

from agentic_patterns.core.connectors.openapi.api_connection_config import ApiConnectionConfigs
from agentic_patterns.core.connectors.openapi.client.http_client import ApiHttpClient
from agentic_patterns.core.connectors.openapi.config import API_CACHE_DIR, API_INFO_EXT
from agentic_patterns.core.connectors.openapi.factories import create_http_client
from agentic_patterns.core.connectors.openapi.models import ApiInfo


class ApiInfos:
    """Registry for all API connections and metadata. Singleton."""

    _instance: "ApiInfos | None" = None

    def __init__(self) -> None:
        self._api_info: dict[str, ApiInfo] = {}
        self._clients: dict[str, ApiHttpClient] = {}
        self._initialized = False

    @classmethod
    def get(cls) -> "ApiInfos":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        if self._initialized:
            return
        api_configs = ApiConnectionConfigs.get()
        for api_id in api_configs.list_api_ids():
            api_info_path = API_CACHE_DIR / api_id / f"{api_id}{API_INFO_EXT}"
            if api_info_path.exists():
                self._api_info[api_id] = ApiInfo.load(api_id, api_info_path)
        self._initialized = True

    def add(self, api_info: ApiInfo) -> None:
        self._api_info[api_info.api_id] = api_info

    def get_api_info(self, api_id: str) -> ApiInfo:
        if api_id not in self._api_info:
            raise ValueError(f"API '{api_id}' not found. Available: {list(self._api_info.keys())}")
        return self._api_info[api_id]

    def get_client(self, api_id: str) -> ApiHttpClient:
        if api_id not in self._api_info:
            raise ValueError(f"API '{api_id}' not found. Available: {list(self._api_info.keys())}")
        if api_id not in self._clients:
            api_info = self._api_info[api_id]
            self._clients[api_id] = create_http_client(api_id, api_info.base_url)
        return self._clients[api_id]

    def list_api_ids(self) -> list[str]:
        return sorted(list(self._api_info.keys()))

    def __len__(self) -> int:
        return len(self._api_info)

    def __str__(self) -> str:
        return f"ApiInfos({len(self._api_info)} APIs: {self.list_api_ids()})"

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

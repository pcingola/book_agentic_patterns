"""API connection configuration model."""

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel


class ApiConnectionConfig(BaseModel):
    """Configuration for a single API connection."""

    api_id: str
    spec_source: str  # URL or file path
    base_url: str

    def __str__(self) -> str:
        return f"ApiConnectionConfig(api_id={self.api_id!r}, spec_source={self.spec_source!r}, base_url={self.base_url!r})"


class ApiConnectionConfigs:
    """Registry for all API connection configurations. Singleton."""

    _instance: "ApiConnectionConfigs | None" = None

    def __init__(self) -> None:
        self._configs: dict[str, ApiConnectionConfig] = {}

    @classmethod
    def get(cls) -> "ApiConnectionConfigs":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._auto_load()
        return cls._instance

    def _auto_load(self) -> None:
        """Auto-load from apis.yaml if available."""
        from agentic_patterns.core.connectors.openapi.config import APIS_YAML_PATH
        if APIS_YAML_PATH.exists():
            self.load_from_yaml(APIS_YAML_PATH)

    def add(self, config: ApiConnectionConfig) -> None:
        self._configs[config.api_id] = config

    def get_config(self, api_id: str) -> ApiConnectionConfig:
        if api_id not in self._configs:
            raise ValueError(f"API '{api_id}' not found. Available: {list(self._configs.keys())}")
        return self._configs[api_id]

    def list_api_ids(self) -> list[str]:
        return list(self._configs.keys())

    def load_from_yaml(self, yaml_path: Path) -> None:
        """Load API configurations from a YAML file with environment variable expansion."""
        if not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")
        data = yaml.safe_load(yaml_path.read_text())
        if not data or "apis" not in data:
            raise ValueError("Invalid apis.yaml format: missing 'apis' key")

        for api_id, api_data in data["apis"].items():
            spec_source = self._expand_env_vars(api_data["spec_source"])
            base_url = self._expand_env_vars(api_data["base_url"])

            # Resolve relative file paths
            if not spec_source.startswith(("http://", "https://")) and not Path(spec_source).is_absolute():
                spec_source = str(yaml_path.parent / spec_source)

            self._configs[api_id] = ApiConnectionConfig(
                api_id=api_id,
                spec_source=spec_source,
                base_url=base_url,
            )

    def _expand_env_vars(self, value: str) -> str:
        """Expand ${VAR} environment variables in string."""
        def replacer(match: re.Match) -> str:
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))
        return re.sub(r"\$\{([^}]+)\}", replacer, value)

    def __len__(self) -> int:
        return len(self._configs)

    def __str__(self) -> str:
        return f"ApiConnectionConfigs({len(self._configs)} APIs: {list(self._configs.keys())})"

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

"""OpenAPI connector configuration."""

from pathlib import Path

import yaml
from pydantic import BaseModel

from agentic_patterns.core.config.config import DATA_DIR, MAIN_PROJECT_DIR


class OpenApiConfig(BaseModel):
    """OpenAPI connector configuration."""

    apis_yaml: str = "apis.yaml"
    cache_dir: str = "data/api"
    info_ext: str = ".api_info.json"
    request_timeout: int = 30
    max_retries: int = 3
    categorization_batch_size: int = 10


_config_cache: OpenApiConfig | None = None


def load_openapi_config(config_path: Path | None = None) -> OpenApiConfig:
    """Load OpenAPI configuration from config.yaml or use defaults."""
    global _config_cache

    if _config_cache is not None and config_path is None:
        return _config_cache

    if config_path is None:
        config_path = MAIN_PROJECT_DIR / "config.yaml"

    if config_path.exists():
        with open(config_path) as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config and "openapi" in yaml_config:
                config = OpenApiConfig.model_validate(yaml_config["openapi"])
                if config_path is None:
                    _config_cache = config
                return config

    config = OpenApiConfig()
    if config_path is None:
        _config_cache = config
    return config


# Derived values for backward compatibility
def _get_config() -> OpenApiConfig:
    return load_openapi_config()


APIS_YAML_PATH = MAIN_PROJECT_DIR / _get_config().apis_yaml
API_CACHE_DIR = DATA_DIR / "api"
API_INFO_EXT = _get_config().info_ext
REQUEST_TIMEOUT = _get_config().request_timeout
MAX_RETRIES = _get_config().max_retries
CATEGORIZATION_BATCH_SIZE = _get_config().categorization_batch_size

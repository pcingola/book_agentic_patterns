"""OpenAPI connector configuration."""

import os

from agentic_patterns.core.config.config import DATA_DIR, MAIN_PROJECT_DIR


APIS_YAML_PATH = MAIN_PROJECT_DIR / os.getenv("APIS_YAML", "apis.yaml")
API_CACHE_DIR = DATA_DIR / "api"
API_INFO_EXT = ".api_info.json"

REQUEST_TIMEOUT = int(os.getenv("API_REQUEST_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))

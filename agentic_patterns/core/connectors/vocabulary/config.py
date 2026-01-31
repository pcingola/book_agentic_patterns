"""Configuration for the vocabulary connector."""

import os
from pathlib import Path

from agentic_patterns.core.config.config import MAIN_PROJECT_DIR

VOCABULARIES_YAML_PATH = MAIN_PROJECT_DIR / os.getenv("VOCABULARIES_YAML", "vocabularies.yaml")
VOCABULARY_CACHE_DIR = MAIN_PROJECT_DIR / "data" / "vocabularies"

"""Context management configuration.

Loads configuration from config.yaml for file processing limits, truncation settings, and history compaction.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel

from agentic_patterns.core.config.config import MAIN_PROJECT_DIR


class TruncationConfig(BaseModel):
    """Configuration for @context_result decorator."""
    threshold: int = 5000
    max_preview_tokens: int = 500
    rows_head: int = 20
    rows_tail: int = 10
    lines_head: int = 50
    lines_tail: int = 20
    json_array_head: int = 10
    json_array_tail: int = 5
    json_max_keys: int = 20


class ContextConfig(BaseModel):
    """Complete context management configuration."""
    # File processing
    max_tokens_per_file: int = 5000
    max_total_output: int = 50000
    max_lines: int = 200
    max_line_length: int = 1000

    # Structured data
    max_nesting_depth: int = 5
    max_array_items: int = 50
    max_object_keys: int = 50
    max_string_value_length: int = 500
    max_object_string_length: int = 2000

    # Tabular data
    max_columns: int = 50
    max_cell_length: int = 500
    rows_head: int = 20
    rows_tail: int = 10

    # Image
    max_image_size_bytes: int = 2 * 1024 * 1024

    # History compaction
    history_max_tokens: int = 120_000
    history_target_tokens: int = 40_000
    summarizer_max_tokens: int = 180_000

    # Truncation configs for decorators
    truncation: dict[str, TruncationConfig] = {
        "default": TruncationConfig(),
        "sql_query": TruncationConfig(threshold=2000, max_preview_tokens=1000, rows_head=30, rows_tail=10),
        "log_search": TruncationConfig(threshold=10000, max_preview_tokens=300, lines_head=50, lines_tail=20),
    }


# Image MIME types that can be attached to model context
IMAGE_ATTACHMENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"}

# Document types that can be extracted
EXTRACTABLE_DOCUMENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/pdf",
}


_config_cache: ContextConfig | None = None


def load_context_config(config_path: Path | None = None) -> ContextConfig:
    """Load context configuration from config.yaml or use defaults."""
    global _config_cache

    if _config_cache is not None and config_path is None:
        return _config_cache

    if config_path is None:
        config_path = MAIN_PROJECT_DIR / "config.yaml"

    if config_path.exists():
        with open(config_path) as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config and "context" in yaml_config:
                config = ContextConfig.model_validate(yaml_config["context"])
                if config_path is None:
                    _config_cache = config
                return config

    config = ContextConfig()
    if config_path is None:
        _config_cache = config
    return config


def get_truncation_config(name: str = "default") -> TruncationConfig:
    """Get truncation configuration by name."""
    config = load_context_config()
    return config.truncation.get(name, config.truncation["default"])

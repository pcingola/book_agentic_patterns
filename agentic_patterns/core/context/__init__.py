"""Context management for agents.

Provides file processing, history compaction, and workspace storage
to manage agent context window limits.
"""

from agentic_patterns.core.context.config import (
    ContextConfig,
    TruncationConfig,
    get_truncation_config,
    load_context_config,
)
from agentic_patterns.core.context.decorators import context_result
from agentic_patterns.core.context.history import (
    CompactionConfig,
    CompactionResult,
    HistoryCompactor,
)
from agentic_patterns.core.context.models import (
    BinaryContent,
    FileExtractionResult,
    FileMetadata,
    FileType,
    TruncationInfo,
)
from agentic_patterns.core.context.reader import read_file, read_file_as_string

__all__ = [
    "BinaryContent",
    "CompactionConfig",
    "CompactionResult",
    "ContextConfig",
    "FileExtractionResult",
    "FileMetadata",
    "FileType",
    "HistoryCompactor",
    "TruncationConfig",
    "TruncationInfo",
    "context_result",
    "get_truncation_config",
    "load_context_config",
    "read_file",
    "read_file_as_string",
]

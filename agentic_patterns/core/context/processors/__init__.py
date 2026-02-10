"""File processors for context management."""

from agentic_patterns.core.context.processors.common import count_lines as count_lines
from agentic_patterns.core.context.processors.json_processor import (
    process_json as process_json,
)
from agentic_patterns.core.context.processors.text import (
    detect_encoding as detect_encoding,
    read_line_range as read_line_range,
)

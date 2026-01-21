"""Decorators for context management in tool functions.

Provides @context_result decorator for tools that may return large results.
When result exceeds threshold, saves full content to workspace and returns truncated preview.
"""

import asyncio
import re
from functools import wraps
from typing import Any
from uuid import uuid4

from agentic_patterns.core.context.config import TruncationConfig, get_truncation_config
from agentic_patterns.core.context.models import FileType


def _detect_content_type(content: str) -> FileType:
    """Auto-detect content type from string content."""
    content_start = content[:1000].strip()

    # JSON
    if content_start.startswith("{") or content_start.startswith("["):
        return FileType.JSON

    # CSV (simple heuristic: comma-separated with consistent columns)
    lines = content_start.split("\n")[:5]
    if len(lines) >= 2:
        comma_counts = [line.count(",") for line in lines if line.strip()]
        if comma_counts and all(c == comma_counts[0] and c > 0 for c in comma_counts):
            return FileType.CSV

    # SQL results (table format)
    if re.search(r"^\s*\|.*\|", content_start, re.MULTILINE):
        return FileType.TEXT

    # Log files
    if re.search(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", content_start):
        return FileType.TEXT

    return FileType.TEXT


def _get_extension_for_type(content_type: FileType) -> str:
    """Get file extension for content type."""
    extensions = {
        FileType.JSON: ".json",
        FileType.CSV: ".csv",
        FileType.TEXT: ".txt",
        FileType.MARKDOWN: ".md",
        FileType.XML: ".xml",
        FileType.YAML: ".yaml",
    }
    return extensions.get(content_type, ".txt")


def _truncate_by_type(content: str, content_type: FileType, config: TruncationConfig) -> str:
    """Truncate content based on detected type."""
    if content_type == FileType.CSV:
        lines = content.split("\n")
        if len(lines) > config.rows_head + config.rows_tail + 1:
            header = lines[0]
            head = lines[1:config.rows_head + 1]
            tail = lines[-config.rows_tail:] if config.rows_tail > 0 else []
            truncated_lines = [header] + head + ["..."] + tail
            return "\n".join(truncated_lines)
        return content

    if content_type in (FileType.TEXT, FileType.MARKDOWN):
        lines = content.split("\n")
        if len(lines) > config.lines_head + config.lines_tail:
            head = lines[:config.lines_head]
            tail = lines[-config.lines_tail:] if config.lines_tail > 0 else []
            truncated_lines = head + ["..."] + tail
            return "\n".join(truncated_lines)
        return content

    # Default: character-based truncation
    max_chars = config.max_preview_tokens * 4
    if len(content) > max_chars:
        return content[:max_chars] + "..."
    return content


def context_result(config_name: str = "default"):
    """Decorator for tools that may return large results.

    If result exceeds threshold:
    1. Auto-detect content type
    2. Save full content to workspace
    3. Truncate according to content type
    4. Return path + truncated preview

    Args:
        config_name: Name of truncation config from config.yaml

    Usage:
        @context_result()
        def some_tool() -> str:
            ...

        @context_result("sql_query")
        def run_sql_query(sql: str) -> str:
            ...
    """
    def decorator(func):
        def _process_result(result: str, ctx: Any) -> str:
            config = get_truncation_config(config_name)

            if not isinstance(result, str) or len(result) <= config.threshold:
                return result

            content_type = _detect_content_type(result)
            ext = _get_extension_for_type(content_type)
            filename = f"result_{uuid4().hex[:8]}{ext}"
            path = f"/workspace/results/{filename}"

            from agentic_patterns.core.workspace import write_to_workspace
            write_to_workspace(path, result, ctx)

            preview = _truncate_by_type(result, content_type, config)
            return f"Results saved to {path} ({len(result)} chars)\n\nPreview:\n{preview}"

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            ctx = kwargs.get("ctx")
            result = await func(*args, **kwargs)
            return _process_result(result, ctx)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            ctx = kwargs.get("ctx")
            result = func(*args, **kwargs)
            return _process_result(result, ctx)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator

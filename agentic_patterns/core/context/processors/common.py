"""Common utilities for file processors."""

import io
import math
from datetime import datetime
from pathlib import Path

from agentic_patterns.core.context.models import (
    FileExtractionResult,
    FileMetadata,
    FileType,
    TruncationInfo,
)


def check_and_apply_output_limit(
    content: str, max_output: int, truncation_info: TruncationInfo
) -> str:
    """Check if content exceeds max output and truncate if needed."""
    suffix = "\n..."
    if len(content) > max_output:
        truncation_info.total_output_limit_reached = True
        return content[: max_output - len(suffix)] + suffix
    return content


def count_lines(file_path: Path, encoding: str = "utf-8") -> int:
    """Count total lines in file."""
    with open(file_path, "r", encoding=encoding, errors="replace") as f:
        return sum(1 for _ in f)


def create_error_result(
    error: Exception,
    file_type: FileType,
    file_path: Path | None = None,
    context: str = "",
) -> FileExtractionResult:
    """Create standardized error result."""
    context_str = f" {context}" if context else ""
    error_message = f"Failed to process{context_str}: {str(error)}"

    size_bytes = 0
    if file_path and file_path.exists():
        try:
            size_bytes = file_path.stat().st_size
        except Exception:
            pass

    return FileExtractionResult(
        content=None,
        success=False,
        error_message=error_message,
        file_type=file_type,
        metadata=FileMetadata(size_bytes=size_bytes),
    )


def create_file_metadata(
    file_path: Path, mime_type: str | None = None, encoding: str | None = None
) -> FileMetadata:
    """Create file metadata from file path."""
    file_stat = file_path.stat()
    return FileMetadata(
        size_bytes=file_stat.st_size,
        modified_time=datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
        mime_type=mime_type,
        encoding=encoding,
    )


def format_section_header(
    title: str, index: int | None = None, total: int | None = None
) -> str:
    """Format section header (e.g., for sheets, chapters)."""
    if index is not None and total is not None:
        return f"\n## {title} {index + 1} of {total}\n\n"
    return f"\n## {title}\n\n"


def format_truncation_summary(
    truncation_info: TruncationInfo, extra_stats: dict | None = None
) -> str:
    """Format truncation summary if any truncation occurred."""
    if not any(
        [
            truncation_info.lines_shown,
            truncation_info.columns_shown,
            truncation_info.rows_shown,
            truncation_info.cells_truncated,
            truncation_info.total_output_limit_reached,
            extra_stats,
        ]
    ):
        return ""

    output = io.StringIO()
    parts = []

    if truncation_info.lines_shown:
        parts.append(f"lines {truncation_info.lines_shown}")

    if truncation_info.columns_shown:
        parts.append(f"columns: {truncation_info.columns_shown}")

    if truncation_info.rows_shown:
        parts.append(f"rows: {truncation_info.rows_shown}")

    if truncation_info.cells_truncated and truncation_info.cells_truncated > 0:
        parts.append(f"{truncation_info.cells_truncated} cells")

    if extra_stats:
        for key, value in extra_stats.items():
            if value and value > 0:
                parts.append(f"{value} {key}")

    if parts:
        output.write(f"Truncated: {', '.join(parts)}\n")

    if truncation_info.total_output_limit_reached:
        output.write("Total output limit reached\n")

    return output.getvalue()


def human_readable_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0B"

    units = ["B", "KB", "MB", "GB", "TB"]
    index = min(int(math.log(size_bytes, 1024)), len(units) - 1)
    size = size_bytes / (1024**index)

    return f"{size:.1f}{units[index]}"


def truncate_string(
    value: str | None, max_length: int, suffix: str = "..."
) -> tuple[str, bool]:
    """Truncate string if it exceeds max_length. Returns (truncated_string, was_truncated)."""
    if value is None:
        return "", False

    value_str = str(value) if not isinstance(value, str) else value

    if len(value_str) <= max_length:
        return value_str, False

    return value_str[:max_length] + suffix, True

"""Text and code file processor with line-based truncation."""

import io
from collections.abc import Callable
from pathlib import Path

from agentic_patterns.core.context.config import ContextConfig, load_context_config
from agentic_patterns.core.context.models import FileExtractionResult, FileType, TruncationInfo
from agentic_patterns.core.context.processors.common import check_and_apply_output_limit, count_lines, create_error_result, create_file_metadata, truncate_string


def detect_encoding(file_path: Path) -> str:
    """Detect file encoding with fallback strategy."""
    encodings = ["utf-8", "latin-1"]

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                f.read(1024)
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue

    return "latin-1"


def read_line_range(file_path: Path, encoding: str, start: int, end: int) -> tuple[list[str], bool, bool]:
    """Read lines from start to end index without loading entire file.

    Returns (selected_lines, ended_at_eof, file_ends_with_newline).
    """
    selected_lines = []
    ended_at_eof = True
    last_line_had_newline = False

    with open(file_path, "r", encoding=encoding, errors="replace") as f:
        for i, line in enumerate(f):
            if i >= start and i < end:
                selected_lines.append(line.rstrip("\n\r"))
                last_line_had_newline = line.endswith(("\n", "\r"))
            if i >= end:
                ended_at_eof = False
                break

    return selected_lines, ended_at_eof, last_line_had_newline


def process_text(
    file_path: Path,
    start_line: int | None = None,
    end_line: int | None = None,
    config: ContextConfig | None = None,
    tokenizer: Callable[[str], int] | None = None,
    file_type: FileType = FileType.TEXT,
) -> FileExtractionResult:
    """Process text files with line range selection and truncation."""
    if config is None:
        config = load_context_config()

    try:
        encoding = detect_encoding(file_path)
        metadata = create_file_metadata(file_path, encoding=encoding)

        actual_start = start_line if start_line is not None else 0
        actual_end = end_line if end_line is not None else actual_start + config.max_lines

        total_lines = count_lines(file_path, encoding)

        if total_lines == 0:
            return FileExtractionResult(
                content="", success=True, file_type=file_type, truncation_info=TruncationInfo(), metadata=metadata
            )

        selected_lines, ended_at_eof, file_ends_with_newline = read_line_range(file_path, encoding, actual_start, actual_end)
        lines_shown = len(selected_lines)

        output = io.StringIO()
        lines_truncated = 0

        for i, line in enumerate(selected_lines):
            truncated_line, was_truncated = truncate_string(line, config.max_line_length)
            if was_truncated:
                lines_truncated += 1

            if i > 0:
                output.write("\n")
            output.write(truncated_line)

            if output.tell() > config.max_total_output:
                output.write("\n...")
                break

        if ended_at_eof and selected_lines and file_ends_with_newline:
            output.write("\n")

        truncation_info = TruncationInfo(
            lines_shown=f"{lines_shown} of {total_lines}" if lines_shown < total_lines else None,
            total_output_limit_reached=output.tell() > config.max_total_output,
        )

        if tokenizer:
            content_str = output.getvalue()
            truncation_info.tokens_shown = tokenizer(content_str)

        result_content = check_and_apply_output_limit(output.getvalue(), config.max_total_output, truncation_info)

        return FileExtractionResult(
            content=result_content, success=True, file_type=file_type, truncation_info=truncation_info, metadata=metadata
        )

    except Exception as e:
        return create_error_result(e, FileType.TEXT, file_path, "text file")


def process_code(
    file_path: Path,
    start_line: int | None = None,
    end_line: int | None = None,
    config: ContextConfig | None = None,
    tokenizer: Callable[[str], int] | None = None,
) -> FileExtractionResult:
    """Process code files with line range selection and truncation."""
    result = process_text(file_path=file_path, start_line=start_line, end_line=end_line, config=config, tokenizer=tokenizer)
    if result.success:
        result.file_type = FileType.CODE
    return result

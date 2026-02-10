"""CSV/TSV file processor with row sampling and truncation."""

import csv
import io
from collections.abc import Callable
from pathlib import Path

from agentic_patterns.core.context.config import ContextConfig, load_context_config
from agentic_patterns.core.context.models import (
    FileExtractionResult,
    FileType,
    TruncationInfo,
)
from agentic_patterns.core.context.processors.common import (
    check_and_apply_output_limit,
    create_error_result,
    create_file_metadata,
    format_truncation_summary,
    truncate_string,
)


def _detect_delimiter(file_path: Path) -> str:
    """Detect delimiter (comma or tab) from file using a small fixed sample."""
    try:
        sample_size = 8192
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            sample = f.read(sample_size)
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample)
            return dialect.delimiter
    except Exception:
        if file_path.suffix.lower() == ".tsv":
            return "\t"
        return ","


def _read_header_and_count(
    file_path: Path, delimiter: str, count_rows: bool = True
) -> tuple[list[str], int | None]:
    """Read CSV header and optionally count total rows."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f, delimiter=delimiter)
        try:
            header = next(reader)
        except StopIteration:
            return [], 0

        if not count_rows:
            return header, None

        total_rows = sum(1 for _ in reader)
    return header, total_rows


def _read_row_range(
    file_path: Path, delimiter: str, start: int, end: int, max_row_bytes: int = 100000
) -> list[list[str]]:
    """Read rows from start to end index without loading entire file."""
    selected_rows = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        header_line = f.readline()
        header_reader = csv.reader(io.StringIO(header_line), delimiter=delimiter)
        try:
            next(header_reader)
        except StopIteration:
            pass

        for i in range(end):
            line = f.readline()
            if not line:
                break

            if len(line) > max_row_bytes:
                line = line[:max_row_bytes] + "\n"

            if i >= start:
                row_reader = csv.reader(io.StringIO(line), delimiter=delimiter)
                try:
                    row = next(row_reader)
                    selected_rows.append(row)
                except (StopIteration, csv.Error):
                    selected_rows.append(
                        [f"[Row {i + 1} parsing error after truncation]"]
                    )

    return selected_rows


def _truncate_row(
    row: list[str], max_columns: int, max_cell_length: int
) -> tuple[list[str], int]:
    """Truncate row to max columns and truncate each cell."""
    row_truncated = row[:max_columns]
    cells_truncated = 0

    truncated_row = []
    for cell in row_truncated:
        truncated_cell, was_truncated = truncate_string(cell, max_cell_length)
        truncated_row.append(truncated_cell)
        if was_truncated:
            cells_truncated += 1

    return truncated_row, cells_truncated


def _write_row_as_line(row: list[str], delimiter: str, max_line_length: int) -> str:
    """Convert row to CSV line and truncate if needed."""
    row_str = io.StringIO()
    temp_writer = csv.writer(row_str, delimiter=delimiter, lineterminator="")
    temp_writer.writerow(row)
    line = row_str.getvalue()

    if len(line) > max_line_length:
        line = line[:max_line_length] + "..."

    return line


def process_csv(
    file_path: Path,
    start_row: int | None = None,
    end_row: int | None = None,
    config: ContextConfig | None = None,
    tokenizer: Callable[[str], int] | None = None,
) -> FileExtractionResult:
    """Process CSV/TSV files with row range selection and truncation."""
    if config is None:
        config = load_context_config()

    try:
        metadata = create_file_metadata(file_path, encoding="utf-8")
        delimiter = _detect_delimiter(file_path)
        file_type = FileType.CSV

        needs_row_count = start_row is not None and start_row < 0
        header, total_rows = _read_header_and_count(
            file_path, delimiter, count_rows=needs_row_count
        )

        if start_row is not None and start_row < 0:
            if total_rows is None:
                header, total_rows = _read_header_and_count(
                    file_path, delimiter, count_rows=True
                )
            actual_start = max(0, total_rows + start_row)
        else:
            actual_start = start_row if start_row is not None else 0

        actual_end = end_row if end_row is not None else actual_start + 10

        if not header:
            return FileExtractionResult(
                content="",
                success=True,
                file_type=file_type,
                truncation_info=TruncationInfo(),
                metadata=metadata,
            )

        total_columns = len(header)
        columns_to_show = min(total_columns, config.max_columns)
        header_truncated = header[:columns_to_show]

        selected_rows = _read_row_range(file_path, delimiter, actual_start, actual_end)
        rows_shown = len(selected_rows)

        output = io.StringIO()
        csv_writer = csv.writer(output, delimiter=delimiter, lineterminator="\n")
        cells_truncated = 0

        truncated_header, header_cells_truncated = _truncate_row(
            header_truncated, columns_to_show, config.max_cell_length
        )
        cells_truncated += header_cells_truncated
        csv_writer.writerow(truncated_header)

        for row in selected_rows:
            truncated_row, row_cells_truncated = _truncate_row(
                row, columns_to_show, config.max_cell_length
            )
            cells_truncated += row_cells_truncated

            line = _write_row_as_line(truncated_row, delimiter, config.max_line_length)
            output.write(line + "\n")

            if output.tell() > config.max_total_output:
                output.write("\n...\n")
                break

        if total_rows is None:
            rows_info = f"first {rows_shown} rows" if rows_shown > 0 else None
        else:
            rows_info = (
                f"{rows_shown} of {total_rows}" if rows_shown < total_rows else None
            )

        truncation_info = TruncationInfo(
            columns_shown=f"{columns_to_show} of {total_columns}"
            if total_columns > columns_to_show
            else None,
            rows_shown=rows_info,
            cells_truncated=cells_truncated,
            total_output_limit_reached=output.tell() > config.max_total_output,
        )

        if tokenizer:
            content_str = output.getvalue()
            truncation_info.tokens_shown = tokenizer(content_str)

        summary = format_truncation_summary(truncation_info)
        if summary:
            output.write(summary)

        result_content = check_and_apply_output_limit(
            output.getvalue(), config.max_total_output, truncation_info
        )

        return FileExtractionResult(
            content=result_content,
            success=True,
            file_type=file_type,
            truncation_info=truncation_info,
            metadata=metadata,
        )

    except Exception as e:
        return create_error_result(e, FileType.CSV, file_path, "tabular file")

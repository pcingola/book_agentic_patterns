"""CSV connector for reading and writing CSV files in the workspace sandbox.

All read operations use the CSV processor for automatic column/cell truncation to
handle wide files (e.g., genomics data with 20,000+ columns).
"""

import csv
import io
from pathlib import Path, PurePosixPath
from typing import Any

from agentic_patterns.core.context.processors.csv_processor import _detect_delimiter, process_csv
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.core.workspace import WorkspaceError, container_to_host_path


def _translate_path(path: str, ctx: Any) -> Path | str:
    """Translate sandbox path to host path, returning error string on failure."""
    try:
        return container_to_host_path(PurePosixPath(path), ctx)
    except WorkspaceError as e:
        return f"[Error] {e}"


class CsvConnector:
    """Agent-facing CSV operations with workspace sandbox isolation.

    All methods are static because there is no instance state yet. When we add
    backend adapters or per-connector config, switch to __init__ + instance methods.
    """

    @staticmethod
    @tool_permission(ToolPermission.WRITE)
    def append(path: str, values: dict[str, str] | list[str], ctx: Any = None) -> str:
        """Append a new row to the end of the CSV."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        try:
            delimiter = _detect_delimiter(host_path)

            with open(host_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f, delimiter=delimiter)
                try:
                    header = next(reader)
                except StopIteration:
                    return "[Error] Empty CSV file"

                row_count = sum(1 for _ in reader)

            if isinstance(values, dict):
                new_row = []
                for col_name in header:
                    if col_name not in values:
                        return f"[Error] Missing value for column '{col_name}'"
                    new_row.append(values[col_name])
            else:
                if len(values) != len(header):
                    return f"[Error] Value count mismatch: expected {len(header)}, got {len(values)}"
                new_row = values

            with open(host_path, "a", encoding="utf-8") as f:
                csv_writer = csv.writer(f, delimiter=delimiter, lineterminator="\n")
                csv_writer.writerow(new_row)

            return f"Appended 1 row to {path} (now {row_count + 1} rows)"

        except Exception as e:
            return f"[Error] {e}"

    @staticmethod
    @tool_permission(ToolPermission.WRITE)
    def delete(path: str, column: str | int, value: str, ctx: Any = None) -> str:
        """Delete rows matching a condition."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        try:
            delimiter = _detect_delimiter(host_path)

            with open(host_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f, delimiter=delimiter)
                try:
                    header = next(reader)
                except StopIteration:
                    return "[Error] Empty CSV file"

                col_idx: int
                if isinstance(column, int):
                    col_idx = column
                    if col_idx < 0 or col_idx >= len(header):
                        return f"[Error] Column index {col_idx} out of range (0-{len(header) - 1})"
                else:
                    try:
                        col_idx = header.index(column)
                    except ValueError:
                        return f"[Error] Column '{column}' not found. Available columns: {', '.join(header)}"

                rows = list(reader)

            original_count = len(rows)
            filtered_rows = [row for row in rows if not (len(row) > col_idx and row[col_idx] == value)]
            deleted_count = original_count - len(filtered_rows)

            if deleted_count == 0:
                col_name = header[col_idx] if isinstance(column, int) else column
                return f"[No rows found where {col_name}='{value}']"

            output = io.StringIO()
            csv_writer = csv.writer(output, delimiter=delimiter, lineterminator="\n")
            csv_writer.writerow(header)
            csv_writer.writerows(filtered_rows)

            host_path.write_text(output.getvalue())

            col_name = header[col_idx] if isinstance(column, int) else column
            return f"Deleted {deleted_count} row(s) where {col_name}='{value}' from {path}"

        except Exception as e:
            return f"[Error] {e}"

    @staticmethod
    @tool_permission(ToolPermission.READ)
    def find(path: str, column: str | int, value: str, limit: int = 10, ctx: Any = None) -> str:
        """Find rows where a column matches a value with automatic truncation."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        if limit <= 0:
            return "[Error] Limit must be positive"

        try:
            delimiter = _detect_delimiter(host_path)

            with open(host_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f, delimiter=delimiter)
                try:
                    header = next(reader)
                except StopIteration:
                    return "[Error] Empty CSV file"

                col_idx: int
                if isinstance(column, int):
                    col_idx = column
                    if col_idx < 0 or col_idx >= len(header):
                        return f"[Error] Column index {col_idx} out of range (0-{len(header) - 1})"
                else:
                    try:
                        col_idx = header.index(column)
                    except ValueError:
                        return f"[Error] Column '{column}' not found. Available columns: {', '.join(header)}"

                matching_rows = []
                for row_num, row in enumerate(reader, start=1):
                    if len(row) > col_idx and row[col_idx] == value:
                        matching_rows.append((row_num, row))
                        if len(matching_rows) >= limit:
                            break

            if not matching_rows:
                return f"[No rows found where column '{header[col_idx]}' = '{value}']"

            output = io.StringIO()
            csv_writer = csv.writer(output, delimiter=delimiter, lineterminator="\n")
            csv_writer.writerow(header)

            row_numbers = []
            for row_num, row in matching_rows:
                csv_writer.writerow(row)
                row_numbers.append(str(row_num))

            temp_file = host_path.parent / f".{host_path.name}.search_results.tmp"
            try:
                temp_file.write_text(output.getvalue())
                result = process_csv(temp_file, start_row=0, end_row=len(matching_rows))
                if not result.success:
                    return f"[Error] Failed to process results: {result.content}"

                rows_info = f"[Found {len(matching_rows)} row(s): {', '.join(row_numbers)}]\n"
                return rows_info + result.content
            finally:
                if temp_file.exists():
                    temp_file.unlink()

        except Exception as e:
            return f"[Error] {e}"

    @staticmethod
    @tool_permission(ToolPermission.READ)
    def head(path: str, n: int = 10, ctx: Any = None) -> str:
        """Read first N rows with automatic column/cell truncation."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        if n <= 0:
            return "[Error] Row count must be positive"

        result = process_csv(host_path, start_row=0, end_row=n)
        if not result.success:
            return f"[Error] Failed to read CSV: {result.content}"

        return result.content

    @staticmethod
    @tool_permission(ToolPermission.READ)
    def headers(path: str, ctx: Any = None) -> str:
        """Get CSV column headers with automatic truncation for wide tables."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        result = process_csv(host_path, start_row=0, end_row=0)
        if not result.success:
            return f"[Error] Failed to read CSV: {result.content}"

        try:
            delimiter = _detect_delimiter(host_path)
            lines = result.content.strip().split('\n')
            if not lines:
                return "[Error] Empty CSV file"

            reader = csv.reader(io.StringIO(lines[0]), delimiter=delimiter)
            header = next(reader)

            total_cols = len(header)
            if result.truncation_info and result.truncation_info.columns_shown:
                shown_info = result.truncation_info.columns_shown
                return f"Columns ({shown_info}): {', '.join(header)}"

            return f"Columns ({total_cols} total): {', '.join(header)}"
        except Exception as e:
            return f"[Error] {e}"

    @staticmethod
    @tool_permission(ToolPermission.READ)
    def read_row(path: str, row_number: int, ctx: Any = None) -> str:
        """Read a specific row by 1-indexed row number with automatic column truncation."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        if row_number < 1:
            return "[Error] Row number must be >= 1"

        result = process_csv(host_path, start_row=row_number - 1, end_row=row_number)
        if not result.success:
            return f"[Error] Failed to read CSV: {result.content}"

        if not result.content.strip() or result.content.count('\n') < 2:
            return f"[Error] Row {row_number} not found"

        return f"[Row {row_number}]\n{result.content}"

    @staticmethod
    @tool_permission(ToolPermission.READ)
    def tail(path: str, n: int = 10, ctx: Any = None) -> str:
        """Read last N rows with automatic column/cell truncation."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        if n <= 0:
            return "[Error] Row count must be positive"

        try:
            delimiter = _detect_delimiter(host_path)

            with open(host_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f, delimiter=delimiter)
                try:
                    header = next(reader)
                except StopIteration:
                    return "[Error] Empty CSV file"

                all_rows = list(reader)

            total_rows = len(all_rows)
            if total_rows == 0:
                return "[Error] No data rows"

            start = max(0, total_rows - n)
            tail_rows = all_rows[start:]

            output = io.StringIO()
            csv_writer = csv.writer(output, delimiter=delimiter, lineterminator="\n")
            csv_writer.writerow(header)
            csv_writer.writerows(tail_rows)

            temp_file = host_path.parent / f".{host_path.name}.tail.tmp"
            try:
                temp_file.write_text(output.getvalue())
                result = process_csv(temp_file, start_row=0, end_row=len(tail_rows))
                if not result.success:
                    return f"[Error] Failed to read CSV: {result.content}"

                if start > 0:
                    return f"[Rows {start + 1}-{total_rows} of {total_rows}]\n{result.content}"
                return result.content
            finally:
                if temp_file.exists():
                    temp_file.unlink()

        except Exception as e:
            return f"[Error] {e}"

    @staticmethod
    @tool_permission(ToolPermission.WRITE)
    def update_cell(path: str, row_number: int, column: str | int, value: str, ctx: Any = None) -> str:
        """Update a single cell value."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        if row_number < 1:
            return "[Error] Row number must be >= 1"

        try:
            delimiter = _detect_delimiter(host_path)

            with open(host_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f, delimiter=delimiter)
                try:
                    header = next(reader)
                except StopIteration:
                    return "[Error] Empty CSV file"

                if len(header) > 1000:
                    return f"[Warning] File has {len(header)} columns. For extremely wide files, consider using specialized tools."

                col_idx: int
                if isinstance(column, int):
                    col_idx = column
                    if col_idx < 0 or col_idx >= len(header):
                        return f"[Error] Column index {col_idx} out of range (0-{len(header) - 1})"
                else:
                    try:
                        col_idx = header.index(column)
                    except ValueError:
                        return f"[Error] Column '{column}' not found. Available columns: {', '.join(header)}"

                rows = list(reader)

            if row_number > len(rows):
                return f"[Error] Row {row_number} not found (file has {len(rows)} data rows)"

            rows[row_number - 1][col_idx] = value

            output = io.StringIO()
            csv_writer = csv.writer(output, delimiter=delimiter, lineterminator="\n")
            csv_writer.writerow(header)
            csv_writer.writerows(rows)

            host_path.write_text(output.getvalue())

            col_name = header[col_idx] if isinstance(column, int) else column
            return f"Updated row {row_number}, column '{col_name}' to '{value}' in {path}"

        except Exception as e:
            return f"[Error] {e}"

    @staticmethod
    @tool_permission(ToolPermission.WRITE)
    def update_row(path: str, key_column: str | int, key_value: str, updates: dict[str, str], ctx: Any = None) -> str:
        """Update an entire row by matching a key column."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        if not updates:
            return "[Error] No updates provided"

        try:
            delimiter = _detect_delimiter(host_path)

            with open(host_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f, delimiter=delimiter)
                try:
                    header = next(reader)
                except StopIteration:
                    return "[Error] Empty CSV file"

                key_col_idx: int
                if isinstance(key_column, int):
                    key_col_idx = key_column
                    if key_col_idx < 0 or key_col_idx >= len(header):
                        return f"[Error] Key column index {key_col_idx} out of range (0-{len(header) - 1})"
                else:
                    try:
                        key_col_idx = header.index(key_column)
                    except ValueError:
                        return f"[Error] Key column '{key_column}' not found. Available columns: {', '.join(header)}"

                update_indices = {}
                for col_name, _ in updates.items():
                    try:
                        update_indices[col_name] = header.index(col_name)
                    except ValueError:
                        return f"[Error] Column '{col_name}' not found in updates. Available columns: {', '.join(header)}"

                rows = list(reader)

            updated_count = 0
            for row in rows:
                if len(row) > key_col_idx and row[key_col_idx] == key_value:
                    for col_name, new_value in updates.items():
                        row[update_indices[col_name]] = new_value
                    updated_count += 1

            if updated_count == 0:
                key_col_name = header[key_col_idx] if isinstance(key_column, int) else key_column
                return f"[No rows found where {key_col_name}='{key_value}']"

            output = io.StringIO()
            csv_writer = csv.writer(output, delimiter=delimiter, lineterminator="\n")
            csv_writer.writerow(header)
            csv_writer.writerows(rows)

            host_path.write_text(output.getvalue())

            key_col_name = header[key_col_idx] if isinstance(key_column, int) else key_column
            return f"Updated {updated_count} row(s) where {key_col_name}='{key_value}' in {path}"

        except Exception as e:
            return f"[Error] {e}"

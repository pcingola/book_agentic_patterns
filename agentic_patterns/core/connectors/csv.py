"""CSV connector for reading and writing CSV files in the workspace sandbox.

Inherits generic file operations from FileConnector and overrides/adds
CSV-aware methods. Read operations use the CSV processor for automatic
column/cell truncation to handle wide files.
"""

import csv
import io

from pydantic_ai import ModelRetry

from agentic_patterns.core.connectors.file import FileConnector
from agentic_patterns.core.workspace import WorkspaceError
from agentic_patterns.core.context.decorators import context_result
from agentic_patterns.core.context.processors.csv_processor import (
    _detect_delimiter,
    process_csv,
)
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission


class CsvConnector(FileConnector):
    """CSV operations with workspace sandbox isolation.

    Inherited from FileConnector: delete, edit, find, list, read, write.
    Overridden: append, head, tail.
    Added: delete_rows, find_rows, headers, read_row, update_cell, update_row.
    """

    @tool_permission(ToolPermission.WRITE)
    def append(self, path: str, values: dict[str, str] | list[str]) -> str:
        """Append a new row to the end of the CSV."""
        try:
            host_path = self._translate_path(path)
            if not host_path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            delimiter = _detect_delimiter(host_path)
            with open(host_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f, delimiter=delimiter)
                try:
                    header = next(reader)
                except StopIteration:
                    raise ValueError("Empty CSV file") from None
                row_count = sum(1 for _ in reader)

            if isinstance(values, dict):
                new_row = []
                for col_name in header:
                    if col_name not in values:
                        raise ValueError(f"Missing value for column '{col_name}'")
                    new_row.append(values[col_name])
            else:
                if len(values) != len(header):
                    raise ValueError(
                        f"Value count mismatch: expected {len(header)}, got {len(values)}"
                    )
                new_row = values

            with open(host_path, "a", encoding="utf-8") as f:
                csv_writer = csv.writer(f, delimiter=delimiter, lineterminator="\n")
                csv_writer.writerow(new_row)

            return f"Appended 1 row to {path} (now {row_count + 1} rows)"
        except (FileNotFoundError, ValueError, IndexError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.WRITE)
    def delete_rows(self, path: str, column: str | int, value: str) -> str:
        """Delete rows matching a condition."""
        try:
            host_path = self._translate_path(path)
            if not host_path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            delimiter = _detect_delimiter(host_path)
            with open(host_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f, delimiter=delimiter)
                try:
                    header = next(reader)
                except StopIteration:
                    raise ValueError("Empty CSV file") from None
                col_idx = self._resolve_column(header, column)
                rows = list(reader)

            original_count = len(rows)
            filtered_rows = [
                row
                for row in rows
                if not (len(row) > col_idx and row[col_idx] == value)
            ]
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
            return (
                f"Deleted {deleted_count} row(s) where {col_name}='{value}' from {path}"
            )
        except (FileNotFoundError, ValueError, IndexError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    @context_result()
    def find_rows(
        self, path: str, column: str | int, value: str, limit: int = 10
    ) -> str:
        """Find rows where a column matches a value with automatic truncation."""
        try:
            host_path = self._translate_path(path)
            if not host_path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            if limit <= 0:
                raise ValueError("Limit must be positive")

            delimiter = _detect_delimiter(host_path)
            with open(host_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f, delimiter=delimiter)
                try:
                    header = next(reader)
                except StopIteration:
                    raise ValueError("Empty CSV file") from None
                col_idx = self._resolve_column(header, column)

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
                    raise ValueError(f"Failed to process results: {result.content}")

                rows_info = (
                    f"[Found {len(matching_rows)} row(s): {', '.join(row_numbers)}]\n"
                )
                return rows_info + result.content
            finally:
                if temp_file.exists():
                    temp_file.unlink()
        except (FileNotFoundError, ValueError, IndexError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    @context_result()
    def head(self, path: str, n: int = 10) -> str:
        """Read first N rows with automatic column/cell truncation."""
        try:
            host_path = self._translate_path(path)
            if not host_path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            if n <= 0:
                raise ValueError("Row count must be positive")

            result = process_csv(host_path, start_row=0, end_row=n)
            if not result.success:
                raise ValueError(f"Failed to read CSV: {result.content}")
            return result.content
        except (FileNotFoundError, ValueError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    def headers(self, path: str) -> str:
        """Get CSV column headers with automatic truncation for wide tables."""
        try:
            host_path = self._translate_path(path)
            if not host_path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            result = process_csv(host_path, start_row=0, end_row=0)
            if not result.success:
                raise ValueError(f"Failed to read CSV: {result.content}")

            delimiter = _detect_delimiter(host_path)
            lines = result.content.strip().split("\n")
            if not lines:
                raise ValueError("Empty CSV file")

            reader = csv.reader(io.StringIO(lines[0]), delimiter=delimiter)
            header = next(reader)

            total_cols = len(header)
            if result.truncation_info and result.truncation_info.columns_shown:
                shown_info = result.truncation_info.columns_shown
                return f"Columns ({shown_info}): {', '.join(header)}"

            return f"Columns ({total_cols} total): {', '.join(header)}"
        except (FileNotFoundError, ValueError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    def read_row(self, path: str, row_number: int) -> str:
        """Read a specific row by 1-indexed row number with automatic column truncation."""
        try:
            host_path = self._translate_path(path)
            if not host_path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            if row_number < 1:
                raise ValueError("Row number must be >= 1")

            result = process_csv(
                host_path, start_row=row_number - 1, end_row=row_number
            )
            if not result.success:
                raise ValueError(f"Failed to read CSV: {result.content}")

            if not result.content.strip() or result.content.count("\n") < 2:
                raise IndexError(f"Row {row_number} not found")

            return f"[Row {row_number}]\n{result.content}"
        except (FileNotFoundError, ValueError, IndexError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    @context_result()
    def tail(self, path: str, n: int = 10) -> str:
        """Read last N rows with automatic column/cell truncation."""
        try:
            host_path = self._translate_path(path)
            if not host_path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            if n <= 0:
                raise ValueError("Row count must be positive")

            delimiter = _detect_delimiter(host_path)
            with open(host_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f, delimiter=delimiter)
                try:
                    header = next(reader)
                except StopIteration:
                    raise ValueError("Empty CSV file") from None
                all_rows = list(reader)

            total_rows = len(all_rows)
            if total_rows == 0:
                raise ValueError("No data rows")

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
                    raise ValueError(f"Failed to read CSV: {result.content}")

                if start > 0:
                    return f"[Rows {start + 1}-{total_rows} of {total_rows}]\n{result.content}"
                return result.content
            finally:
                if temp_file.exists():
                    temp_file.unlink()
        except (FileNotFoundError, ValueError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.WRITE)
    def update_cell(
        self, path: str, row_number: int, column: str | int, value: str
    ) -> str:
        """Update a single cell value."""
        try:
            host_path = self._translate_path(path)
            if not host_path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            if row_number < 1:
                raise ValueError("Row number must be >= 1")

            delimiter = _detect_delimiter(host_path)
            with open(host_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f, delimiter=delimiter)
                try:
                    header = next(reader)
                except StopIteration:
                    raise ValueError("Empty CSV file") from None
                col_idx = self._resolve_column(header, column)
                rows = list(reader)

            if row_number > len(rows):
                raise IndexError(
                    f"Row {row_number} not found (file has {len(rows)} data rows)"
                )

            rows[row_number - 1][col_idx] = value

            output = io.StringIO()
            csv_writer = csv.writer(output, delimiter=delimiter, lineterminator="\n")
            csv_writer.writerow(header)
            csv_writer.writerows(rows)
            host_path.write_text(output.getvalue())

            col_name = header[col_idx] if isinstance(column, int) else column
            return (
                f"Updated row {row_number}, column '{col_name}' to '{value}' in {path}"
            )
        except (FileNotFoundError, ValueError, IndexError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.WRITE)
    def update_row(
        self, path: str, key_column: str | int, key_value: str, updates: dict[str, str]
    ) -> str:
        """Update an entire row by matching a key column."""
        try:
            host_path = self._translate_path(path)
            if not host_path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            if not updates:
                raise ValueError("No updates provided")

            delimiter = _detect_delimiter(host_path)
            with open(host_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f, delimiter=delimiter)
                try:
                    header = next(reader)
                except StopIteration:
                    raise ValueError("Empty CSV file") from None
                key_col_idx = self._resolve_column(header, key_column)

                update_indices = {}
                for col_name in updates:
                    try:
                        update_indices[col_name] = header.index(col_name)
                    except ValueError:
                        raise ValueError(
                            f"Column '{col_name}' not found. Available columns: {', '.join(header)}"
                        ) from None

                rows = list(reader)

            updated_count = 0
            for row in rows:
                if len(row) > key_col_idx and row[key_col_idx] == key_value:
                    for col_name, new_value in updates.items():
                        row[update_indices[col_name]] = new_value
                    updated_count += 1

            if updated_count == 0:
                key_col_name = (
                    header[key_col_idx] if isinstance(key_column, int) else key_column
                )
                return f"[No rows found where {key_col_name}='{key_value}']"

            output = io.StringIO()
            csv_writer = csv.writer(output, delimiter=delimiter, lineterminator="\n")
            csv_writer.writerow(header)
            csv_writer.writerows(rows)
            host_path.write_text(output.getvalue())

            key_col_name = (
                header[key_col_idx] if isinstance(key_column, int) else key_column
            )
            return f"Updated {updated_count} row(s) where {key_col_name}='{key_value}' in {path}"
        except (FileNotFoundError, ValueError, IndexError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    @staticmethod
    def _resolve_column(header: list[str], column: str | int) -> int:
        """Resolve column name or index to index."""
        if isinstance(column, int):
            if column < 0 or column >= len(header):
                raise ValueError(
                    f"Column index {column} out of range (0-{len(header) - 1})"
                )
            return column
        try:
            return header.index(column)
        except ValueError:
            raise ValueError(
                f"Column '{column}' not found. Available columns: {', '.join(header)}"
            ) from None

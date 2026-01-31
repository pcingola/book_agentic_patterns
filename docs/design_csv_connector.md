# CSV File Connector Design

## Overview

Design for a CSV file connector that provides CSV-specific primitives for agents to interact with CSV files in the workspace sandbox. This connector builds on top of the existing generic file connector and integrates with the context processor infrastructure for automatic truncation of large results.

## Requirements

1. **Agent-facing**: Operations designed for direct agent use, not programmer APIs
2. **Workspace sandboxing**: All file operations constrained to `/workspace/...` paths
3. **Context management**: **ALWAYS** use CSV processor for ALL read operations (genomics files can have 20,000+ columns per row)
4. **Format detection**: Auto-detect delimiters (comma, tab)
5. **Safe operations**: Validate inputs, handle errors gracefully
6. **Permission-aware**: Use existing `@tool_permission` decorator

## Critical Design Constraint

**NEVER read CSV data directly without the processor.** Even a single row can have thousands of columns (e.g., genomics data with 20,000 columns). Every read operation must route through `process_csv()` to ensure proper column and cell truncation.

**Write operations on wide files**: While write operations cannot use the processor (they need to preserve all columns), they should:
1. Check column count before attempting updates
2. Warn agent if file has >1000 columns
3. Process line-by-line to avoid loading entire wide rows into memory
4. Consider suggesting agent use specialized tools for genomics data instead

## Operations

### Read Operations (ToolPermission.READ)

#### 1. `preview_csv(path, rows=20, ctx=None) -> str`
Preview first N rows with automatic column/cell truncation.

**Input:**
- `path`: Sandbox path (e.g., `/workspace/data/customers.csv`)
- `rows`: Number of rows to preview (default 20)
- `ctx`: Request context for user/session isolation

**Output:**
- Formatted CSV string with truncation summary
- Uses CSV processor for intelligent truncation
- Returns `[Error] ...` on failure

**Implementation:**
- Translate sandbox path to host path
- Use `process_csv()` with `start_row=0, end_row=rows`
- Format result with truncation info

#### 2. `read_csv_row(path, row_number, ctx=None) -> str`
Read a specific row by 1-indexed row number with automatic column truncation.

**Input:**
- `path`: Sandbox path
- `row_number`: Row to read (1 = first data row after header)
- `ctx`: Request context

**Output:**
- Formatted CSV string with header + requested row
- Includes truncation info if columns/cells were truncated
- Returns `[Error] ...` on failure

**Implementation:**
- Use `process_csv()` with `start_row=row_number-1, end_row=row_number`
- CSV processor handles column/cell truncation automatically
- Format result with row number annotation
- Handle missing rows gracefully

#### 3. `find_csv_rows(path, column, value, limit=10, ctx=None) -> str`
Find rows where a column matches a value with automatic truncation.

**Input:**
- `path`: Sandbox path
- `column`: Column name or index (0-based)
- `value`: Value to match (string comparison)
- `limit`: Max rows to return (default 10)
- `ctx`: Request context

**Output:**
- Formatted CSV string with header + matching rows
- Includes row numbers and truncation info
- Returns `[Error] ...` on failure

**Implementation:**
- First pass: Stream through file to find matching row numbers
- Use `process_csv()` on collected row ranges
- CSV processor handles column/cell truncation automatically
- Alternatively: Write matching rows to temp file, process with `process_csv()`
- Include original row numbers in output

#### 4. `get_csv_headers(path, ctx=None) -> str`
Get CSV column headers with automatic truncation for wide tables.

**Input:**
- `path`: Sandbox path
- `ctx`: Request context

**Output:**
- Formatted string showing headers (truncated if >50 columns)
- Example: `"Columns (showing 50 of 20000): col1, col2, ..., col50"`
- Returns `[Error] ...` on failure

**Implementation:**
- Use `process_csv()` with `start_row=0, end_row=0` (header only)
- CSV processor handles column truncation automatically
- Extract header info from result
- Format compactly for agent consumption

### Write Operations (ToolPermission.WRITE)

#### 5. `update_csv_cell(path, row_number, column, value, ctx=None) -> str`
Update a single cell value.

**Input:**
- `path`: Sandbox path
- `row_number`: Row to update (1-indexed, 1 = first data row)
- `column`: Column name or 0-based index
- `value`: New value (string)
- `ctx`: Request context

**Output:**
- Success: `"Updated row 5, column 'status' to 'active' in /workspace/data/file.csv"`
- Returns `[Error] ...` on failure

**Implementation:**
- Read entire file line-by-line (required for CSV rewrite)
- Parse only the specific row that needs updating
- Update specific cell
- Write back to file
- Validate row/column exist
- **Warning**: For extremely wide files (20,000+ columns), this may be slow; consider warning agent if column count > 1000

#### 6. `update_csv_row(path, key_column, key_value, updates, ctx=None) -> str`
Update an entire row by matching a key column.

**Input:**
- `path`: Sandbox path
- `key_column`: Column to use as key
- `key_value`: Value to match
- `updates`: Dict of column->value updates (e.g., `{"status": "inactive", "date": "2026-01-15"}`)
- `ctx`: Request context

**Output:**
- Success: `"Updated 1 row(s) where customer_id='C-1932' in /workspace/data/file.csv"`
- Returns `[Error] ...` on failure

**Implementation:**
- Read entire file
- Find row(s) matching key
- Apply updates
- Write back
- Return count of updated rows

#### 7. `append_csv_row(path, values, ctx=None) -> str`
Append a new row to the end of the CSV.

**Input:**
- `path`: Sandbox path
- `values`: Dict or list of values (e.g., `{"name": "Alice", "age": "30"}` or `["Alice", "30"]`)
- `ctx`: Request context

**Output:**
- Success: `"Appended 1 row to /workspace/data/file.csv (now 156 rows)"`
- Returns `[Error] ...` on failure

**Implementation:**
- Read header to validate columns
- Format new row with correct delimiter
- Append to file (efficient, no full rewrite)
- Validate value count matches header

#### 8. `delete_csv_rows(path, column, value, ctx=None) -> str`
Delete rows matching a condition.

**Input:**
- `path`: Sandbox path
- `column`: Column name or index
- `value`: Value to match
- `ctx`: Request context

**Output:**
- Success: `"Deleted 3 row(s) where status='inactive' from /workspace/data/file.csv"`
- Returns `[Error] ...` on failure

**Implementation:**
- Read entire file
- Filter out matching rows
- Write back
- Return count of deleted rows

## Technical Details

### File Structure

```
agentic_patterns/core/connectors/
├── __init__.py          # Export all connector functions
├── file.py              # Existing generic file connector
└── csv.py               # New CSV connector (this design)
```

### Dependencies

- `agentic_patterns.core.workspace`: Path translation, sandboxing
- `agentic_patterns.core.context.processors.csv_processor`: CSV reading with truncation
- `agentic_patterns.core.tools.permissions`: `@tool_permission` decorator
- `csv` module: Reading/writing CSV data
- `pathlib`: Path handling

### Key Patterns

1. **Path Translation**: Always use `_translate_path(path, ctx)` to convert sandbox paths to host paths
2. **Error Handling**: Return formatted error strings `"[Error] ..."` instead of raising exceptions
3. **Format Detection**: Auto-detect delimiter using `_detect_delimiter()` from CSV processor
4. **CRITICAL - Truncation**: **ALL read operations MUST use `process_csv()`** - never read CSV data directly (genomics files can have 20,000+ columns per row)
5. **Read-Modify-Write**: For updates, read entire file, modify in memory, write back (CSV format limitation - but validate column count before writing)

### Example Agent Interactions

```python
# Agent previews a CSV file
preview_csv("/workspace/data/customers.csv", rows=20)
# Returns: Formatted CSV with first 20 rows, column truncation if needed

# Agent previews a wide genomics file (20,000 columns)
preview_csv("/workspace/genomics/variants.csv", rows=10)
# Returns: Formatted CSV with header + 10 rows
#   [Truncation info: showing 50 of 20000 columns, 145 cells truncated]

# Agent checks headers (normal file)
get_csv_headers("/workspace/data/customers.csv")
# Returns: "Columns (5 total): customer_id, name, email, status, created_at"

# Agent checks headers (wide file)
get_csv_headers("/workspace/genomics/variants.csv")
# Returns: "Columns (showing 50 of 20000): chr, pos, ref, alt, sample_001, ..., sample_047"

# Agent searches for specific records
find_csv_rows("/workspace/data/customers.csv", column="status", value="active", limit=10)
# Returns: Formatted CSV with header + matching rows (with row numbers)
#   [Row 5, Row 12, Row 23 shown, columns truncated if needed]

# Agent updates a cell
update_csv_cell("/workspace/data/customers.csv", row_number=12, column="status", value="active")
# Returns: "Updated row 12, column 'status' to 'active' in /workspace/data/customers.csv"

# Agent updates a row by key
update_csv_row(
    "/workspace/data/customers.csv",
    key_column="customer_id",
    key_value="C-1932",
    updates={"status": "inactive", "churned_at": "2026-01-15"}
)
# Returns: "Updated 1 row(s) where customer_id='C-1932' in /workspace/data/customers.csv"

# Agent appends a new record
append_csv_row(
    "/workspace/data/customers.csv",
    values={"customer_id": "C-2041", "name": "Alice", "email": "alice@example.com", "status": "active"}
)
# Returns: "Appended 1 row to /workspace/data/customers.csv (now 156 rows)"
```

## Performance Considerations

1. **Wide Files (Many Columns)**: CSV processor automatically truncates to max_columns (default 50) - critical for genomics data with 20,000+ columns
2. **Tall Files (Many Rows)**: Read operations use streaming and row limits; safe for millions of rows
3. **Write Operations**: Require full file read/write (CSV format limitation) - validate column count before processing
4. **Search Operations**: Stream through file; stop at limit to avoid loading everything
5. **Delimiter Detection**: Uses small sample (8KB) for fast detection
6. **Cell Truncation**: Individual cells truncated to max_cell_length (default 500 chars) to prevent context overflow

## Future Enhancements

Not in scope for initial implementation:

- Batch updates (multiple rows/cells in one call)
- Schema validation (type checking)
- Column addition/removal
- CSV-to-JSON conversion
- Aggregations (sum, count, etc.)

## Testing Strategy

Test coverage should include:

1. **Unit tests** for each operation
2. **Delimiter detection** (comma, tab)
3. **Wide files** (1000+ columns) - verify column truncation works
4. **Tall files** (10,000+ rows) - verify row limits work
5. **Genomics-scale files** (20,000 columns, long cell values) - verify no context overflow
6. **Error cases** (missing files, invalid rows, malformed CSV)
7. **Workspace sandboxing** (path traversal attempts)
8. **Edge cases** (empty files, single row, no header, single column)

## References

From book chapter "Connectors" (chapters/connectors/connectors.md):

> For CSV, the agent usually wants either a preview table or a cell/row update without manually counting commas. A connector can offer a minimal table abstraction while still being backend-agnostic:
>
> ```python
> preview = csv.preview("data/customers.csv", rows=20)
> csv.update_cell("data/customers.csv", row=12, column="status", value="active")
> csv.update_row("data/customers.csv", key={"customer_id": "C-1932"},
>                values={"status": "inactive", "churned_at": "2026-01-15"})
> ```

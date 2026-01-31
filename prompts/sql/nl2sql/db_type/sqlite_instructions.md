# SQLite-specific SQL syntax guidelines

- Use double quotes for identifiers, single quotes for string literals
- Avoid using reserved words for table aliases (e.g. don't use 'do', 'user', 'table', etc.)
- No `ILIKE`, use `LIKE` with `LOWER()` for case-insensitive matching
- Use `LIMIT` and `OFFSET` for pagination
- Date/time functions: `date()`, `time()`, `datetime()`, `strftime()`
- String concatenation: use `||` operator
- No regular expression support by default
- Boolean values stored as 0 (false) and 1 (true)
- No native array or JSON types (stored as text)
- Use `RANDOM()` for random ordering

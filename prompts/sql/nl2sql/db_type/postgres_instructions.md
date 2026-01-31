# PostgreSQL-specific SQL syntax guidelines

- Use double quotes for identifiers that contain special characters or are case-sensitive
- Avoid using reserved words for table aliases (e.g. don't use 'do', 'user', 'table', etc.)
- Use `ILIKE` for case-insensitive pattern matching
- Use `LIMIT` and `OFFSET` for pagination
- Array syntax: `ARRAY[1,2,3]` or `'{1,2,3}'::int[]`
- JSON operations: use `->` for JSON object field access, `->>` for text extraction
- String concatenation: use `||` operator or `concat()` function
- Date functions: `CURRENT_DATE`, `CURRENT_TIMESTAMP`, `age()`, `date_trunc()`
- Regular expressions: use `~` for pattern matching, `~*` for case-insensitive

## Guidelines and methods

- When executing SQL statements, use `ILIKE` with wildcards for case insensitive text searches.
- There is no need to use `LIMIT` in your SQL queries, as the tool will limit the number of shown rows and the full output is saved to a file.
- Be careful not to use reserved words in table aliases, e.g. `do` is a reserved word in PostgreSQL

## Database schema

{schema}

## Examples

{example_queries_md}

# SQL Query Example

Generate a SQL query example for this database that demonstrates its usage patterns.

## Database Information

Database Description:
{db_description}

Database Schema:

{schema}

## Requirements

- Create a query that covers complexity level (simple select, join, or aggregation)
- The query MUST be a valid SQL query that can be executed without errors
- The query should demonstrate meaningful insights from the data
- Use realistic filtering conditions based on the schema
- This is query {idx} of {total}, try to vary complexity and tables used{retry_note}

## Output Format

Return a single dictionary with:
- description: Brief description of what the query does (one line, no special characters)
- query: The SQL query (must be valid SQL)

Example format:
{{"description": "Get all active users", "query": "SELECT * FROM users WHERE status = 'active';"}}

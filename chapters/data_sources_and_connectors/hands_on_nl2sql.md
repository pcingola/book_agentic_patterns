## Hands-On: NL2SQL with CSV Post-Processing

This hands-on walks through `example_nl2sql.ipynb`, where two agents collaborate in sequence. The first agent translates a natural language question into SQL, executes it against the bookstore database, and saves the results as a CSV file. The second agent then picks up that CSV file and operates on it using the CsvConnector. This demonstrates how connectors chain together: one produces data, another refines it.

### Database Configuration

Before any NL2SQL agent can run, the system needs to know which databases exist and how to connect to them. Configuration is loaded from `dbs.yaml`, which declares database identifiers, connection details, and paths. The two singleton registries -- `DbConnectionConfigs` and `DbInfos` -- are reset and reloaded to ensure a clean state:

```python
DbConnectionConfigs.reset()
DbInfos.reset()
DbConnectionConfigs.get().load_from_yaml(DBS_YAML_PATH)
```

`DbConnectionConfigs` holds connection parameters (driver, path, credentials). `DbInfos` holds the extracted and annotated schema metadata that the agent uses as context. The `reset()` calls are relevant in notebook environments where cells may be re-executed.

### Creating the NL2SQL Agent

The `create_agent()` factory (in `agents/nl2sql`) does several things in a single call. It looks up the schema metadata for the given database identifier, loads the system prompt and instructions (which embed the full annotated schema), collects the NL2SQL tools, and returns a configured PydanticAI agent:

```python
nl2sql_agent = create_agent(db_id="bookstore")
```

The agent receives two tools. `db_execute_sql_tool` generates SQL from the user's question, validates it (SELECT-only, single statement), executes it, and writes results to a CSV file in the workspace. `db_get_row_by_id_tool` fetches a single row by primary key for detailed inspection. Both tools are created using the closure pattern: inner functions that capture the `db_id` from the enclosing scope, so the model never sees or manages database identifiers directly.

The schema embedded in the instructions is the annotated version produced by the offline annotation pipeline. It includes table descriptions, column explanations, enum values, and sample data. This rich context is what allows the model to generate accurate SQL without querying the database catalog at runtime.

### Running a Natural Language Query

The prompt asks the agent to join books with authors and reviews, compute average ratings, sort by rating, and save the output:

```python
query = "List all books with their author name and average review rating, sorted by rating descending. Save results to /workspace/books_ratings.csv"
result, nodes = await run_agent(nl2sql_agent, query, verbose=True)
```

Behind the scenes, the agent reasons about the schema, generates a SQL query with the appropriate JOINs and GROUP BY clause, calls `db_execute_sql_tool`, and receives a truncated preview of the results. The full result set is written to the CSV file at the workspace path specified in the prompt. The `verbose=True` flag prints each reasoning step and tool call so you can see the generated SQL.

This illustrates the core NL2SQL pipeline described in the chapter: natural language in, validated SQL generated, results bounded and persisted, only a preview returned to the agent context.

### Handing Off to the CSV Agent

The SQL agent produced `/workspace/books_ratings.csv`. Now a second agent takes over, equipped with CsvConnector tools instead of SQL tools:

```python
csv_connector = CsvConnector()

csv_tools = [
    csv_connector.head,
    csv_connector.find_rows,
    csv_connector.headers,
    csv_connector.delete_rows,
    csv_connector.read_row,
]

csv_agent = get_agent(tools=csv_tools)
```

The CsvConnector operates on CSV files through workspace paths, just like the FileConnector operates on text files. Its methods -- `head`, `find_rows`, `headers`, `delete_rows`, `read_row` -- are already tool-compatible bound methods decorated with `@tool_permission()`. Like the FileConnector, these methods can be bound directly as tools without any wrapper functions.

Note that this example focuses on read operations. The CsvConnector also provides write operations (`update_cell`, `update_row`, `append`) for modifying CSV data in place, which would be useful in workflows where the agent needs to transform or correct data before passing it downstream.

The CSV agent prompt asks it to inspect the file that the SQL agent created:

```python
csv_prompt = """Using the CSV file at /workspace/books_ratings.csv:
1. Show me the column headers.
2. Show me the first 5 rows.
3. Read row 1 in detail."""
```

The agent calls `headers`, `head`, and `read_row` in sequence. Each tool reads from the same CSV file on disk, returning structured text that the agent can summarize for the user.

### Connector Chaining

The key architectural point here is that neither agent knows about the other. The SQL agent writes a CSV file as a side effect of query execution. The CSV agent reads that file as input. The workspace filesystem is the integration layer -- it decouples the two agents completely. You could replace the SQL agent with any other data source that produces CSV, and the CSV agent would work unchanged.

This pattern scales naturally. A third agent could read the same CSV and produce a chart. A fourth could filter rows and write a new file. Each agent operates through its own connector, and the workspace provides shared, persistent storage.

### Verifying on Disk

The final cell confirms that the CSV file exists on the host filesystem, outside the agent conversation:

```python
host_path = workspace_to_host_path(PurePosixPath("/workspace/books_ratings.csv"))
print(host_path.read_text().splitlines()[:6])
```

This round-trip verification -- agent writes through the sandbox, human reads from the host -- confirms that the data produced by the NL2SQL pipeline is a real, persistent artifact available for any downstream use.

### Key Takeaways

The NL2SQL agent translates natural language into validated SQL using an annotated schema as its primary grounding context. Results are persisted as CSV files in the workspace rather than injected into the agent context, keeping prompts small and data reusable. The CsvConnector provides a second agent with structured access to that data without any knowledge of SQL. The workspace filesystem acts as the integration layer between agents, enabling connector chaining where each agent operates independently through its own tools.

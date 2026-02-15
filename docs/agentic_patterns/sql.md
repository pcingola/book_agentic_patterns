# SQL Connector

`SqlConnector` provides SQL database access with schema discovery, validated query execution, and result persistence. Configuration is loaded from `dbs.yaml` which declares database identifiers, connection details, and sensitivity levels.

## Configuration

Database connections are declared in `dbs.yaml` at the project root:

```yaml
databases:
  bookstore:
    type: sqlite
    dbname: data/db/bookstore.db

  inventory:
    type: sqlite
    dbname: data/db/inventory.db
    sensitivity: confidential
```

Each entry defines a `type` (`sqlite`; `postgres` reserved for future use), connection parameters (`host`, `port`, `dbname`, `user`, `password`, `schema`), and an optional `sensitivity` level (`public`, `internal`, `confidential`, `restricted`). Relative `dbname` paths are resolved relative to `dbs.yaml`'s directory.

`DbConnectionConfigs` is a singleton registry that auto-loads `dbs.yaml` on first access. `DbInfos` is the companion registry for extracted and annotated schema metadata. Both support `reset()` for notebook re-execution.

```python
from agentic_patterns.core.connectors.sql.db_connection_config import DbConnectionConfigs
from agentic_patterns.core.connectors.sql.db_infos import DbInfos

configs = DbConnectionConfigs.get()      # auto-loads dbs.yaml
configs.list_db_ids()                    # ["bookstore", "inventory"]
```

## Data Models

`DbInfo` -- database-level metadata: `db_id`, `description`, `tables: list[TableInfo]`, `example_queries`. Provides `schema_sql()` for formatted schema output.

`TableInfo` -- table metadata: `name`, `columns: list[ColumnInfo]`, `foreign_keys`, `indexes`, `description`, `sample_data_csv`.

`ColumnInfo` -- column metadata: `name`, `data_type`, `is_nullable`, `description`, `is_primary_key`, `is_enum`, `enum_values`.

## Operations

`list_databases()` -- list available databases with descriptions and table counts.

`list_tables(db_id)` -- list tables with descriptions.

`show_schema(db_id)` -- full annotated schema SQL with descriptions and example queries.

`show_table_details(db_id, table_name)` -- detailed schema for a single table.

`execute_sql(db_id, query, output_file=None, nl_query=None)` -- execute a validated SELECT query. Rejects non-SELECT and multi-statement queries. Writes results to a CSV file and returns a bounded preview. If the database has a non-PUBLIC sensitivity level, tags the session via `PrivateData`.

`get_row_by_id(db_id, table_name, row_id, fetch_related=False)` -- fetch a single row by primary key, optionally expanding foreign key references.

## Query Validation

`validate_query()` ensures that only single SELECT statements reach the database. It rejects empty queries, multi-statement queries, and non-SELECT statements. Used internally by `execute_sql()`, but available as a standalone utility:

```python
from agentic_patterns.core.connectors.sql.query_validation import validate_query, QueryValidationError

validate_query("SELECT * FROM books")  # OK
validate_query("DROP TABLE books")     # raises QueryValidationError
```

## Configuration Constants

Tunable via environment variables (`agentic_patterns.core.connectors.sql.config`):

| Constant | Env var | Default | Description |
|---|---|---|---|
| `DBS_YAML_PATH` | `DBS_YAML` | `dbs.yaml` | Path to database config file |
| `MAX_SAMPLE_ROWS` | `MAX_SAMPLE_ROWS` | 10 | Sample rows collected during annotation |
| `MAX_ENUM_VALUES` | `MAX_ENUM_VALUES` | 50 | Maximum distinct values for enum detection |
| `NUMBER_OF_EXAMPLE_QUERIES` | `NUMBER_OF_EXAMPLE_QUERIES` | 5 | Example queries generated per database |
| `PREVIEW_ROWS` | `PREVIEW_ROWS` | 10 | Rows shown in query result preview |
| `PREVIEW_COLUMNS` | `PREVIEW_COLUMNS` | 200 | Column character limit in preview |
| `MAX_CSV_VIEW_ROWS` | `MAX_CSV_VIEW_ROWS` | 1000 | Maximum rows in CSV view |

## Schema Annotation Pipeline

Schema preparation is an offline step. The annotation pipeline (`DbSchemaAnnotator`) extracts raw schema from the database, then uses an LLM to generate descriptions for the database, each table, and each column. It also collects sample data, detects enum-like columns, and generates example queries. Results are cached as `.db_info.json` files. At runtime, the agent relies entirely on this cached metadata.

Run the annotation pipeline via CLI:

```bash
scripts/annotate_schema.sh
```

## Database-Specific Components

The SQL connector uses a factory pattern (`agentic_patterns.core.connectors.sql.factories`) to create database-specific implementations. Three factory functions dispatch on `DatabaseType`:

`create_connection(db_id)` -- returns a `DbConnection` (currently `DbConnectionSqlite`).

`create_schema_inspector(db_id, connection)` -- returns a `DbSchemaInspector` (currently `DbSchemaInspectorSqlite`).

`create_db_operations(db_id)` -- returns a `DbOperations` (currently `DbOperationsSqlite`).

To add a new database engine, create implementations of `DbConnection`, `DbSchemaInspector`, and `DbOperations` in a subdirectory (e.g., `postgres/`), add a new `DatabaseType` value, and extend each factory's `match` block.

## NL2SQL Agent

The NL2SQL agent combines the SQL connector with a domain-specific agent that translates natural language to validated SQL:

```python
from agentic_patterns.agents.nl2sql import create_agent

agent = create_agent(db_id="bookstore")
result, nodes = await run_agent(agent, "List all books with author name and average review rating")
```

`create_agent(db_id)` loads the annotated schema, builds a system prompt embedding the full schema, and binds two closure-based tools (`db_execute_sql_tool` and `db_get_row_by_id_tool`) that capture the database identifier. The agent never sees raw database identifiers or connection details.

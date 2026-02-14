# SQL Connector

`SqlConnector` provides SQL database access with schema discovery, validated query execution, and result persistence. Configuration is loaded from `dbs.yaml` which declares database identifiers, connection details, and sensitivity levels.

## Configuration

```python
from agentic_patterns.core.connectors.sql.db_connection_configs import DbConnectionConfigs
from agentic_patterns.core.connectors.sql.db_infos import DbInfos

DbConnectionConfigs.get().load_from_yaml(dbs_yaml_path)
```

`DbConnectionConfigs` is a singleton registry of connection parameters (driver, path, credentials, sensitivity level). `DbInfos` is a singleton registry of extracted and annotated schema metadata. Both support `reset()` for notebook re-execution.

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

## Schema Annotation Pipeline

Schema preparation is an offline step. The annotation pipeline (`DbSchemaAnnotator`) extracts raw schema from the database, then uses an LLM to generate descriptions for the database, each table, and each column. It also collects sample data, detects enum-like columns, and generates example queries. Results are cached as `.db_info.json` files. At runtime, the agent relies entirely on this cached metadata.

Run the annotation pipeline via CLI:

```bash
scripts/annotate_schema.sh
```

## NL2SQL Agent

The NL2SQL agent combines the SQL connector with a domain-specific agent that translates natural language to validated SQL:

```python
from agentic_patterns.agents.nl2sql import create_agent

agent = create_agent(db_id="bookstore")
result, nodes = await run_agent(agent, "List all books with author name and average review rating")
```

`create_agent(db_id)` loads the annotated schema, builds a system prompt embedding the full schema, and binds two closure-based tools (`db_execute_sql_tool` and `db_get_row_by_id_tool`) that capture the database identifier. The agent never sees raw database identifiers or connection details.

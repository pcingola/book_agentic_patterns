# Plan: SQL Connector and NL2SQL

Reference implementation: `~/aixplore/mcp-template-sql/` (mcp_sql module).

## Code Reuse from mcp-template-sql

Most of the code we need already exists in `~/aixplore/mcp-template-sql/mcp_sql/`. The approach is to copy and adapt rather than write from scratch. Key sources:

- **Data models**: `mcp_sql/data_models/` -- DatabaseType, DbConnectionConfig, DbConnection, ColumnInfo, ForeignKeyInfo, IndexInfo, TableInfo, DbInfo. Adapt from dataclasses to Pydantic where needed, adjust imports to point to `agentic_patterns.core`.
- **Schema inspection**: `mcp_sql/db_inspection/` -- DbSchemaInspector (abstract + SQLite/Postgres), DbSchemaExtractor, enum detectors, sample data collectors. Copy directly, update imports.
- **Operations**: `mcp_sql/tools/operations.py` (the `_op` layer) and `mcp_sql/tools/sqlite/operations.py` (DbOperationsSqlite). Copy and adapt, removing MCP Context dependencies where not needed.
- **Query validation**: Already in `mcp_sql/tools/operations.py`. Extract into its own file.
- **NL2SQL agent**: `mcp_sql/agents/nl2sql/` -- agent.py, tools.py, prompts.py. Copy and rewire to use `agentic_patterns.core.agents.get_agent()`.
- **DB catalog agent**: `mcp_sql/agents/db_catalog/`. Copy as-is.
- **Prompt templates**: `mcp-template-sql/prompts/` -- all markdown files for NL2SQL, enum detection, schema annotation. Copy into `prompts/sql/`.
- **Factories**: `mcp_sql/data_models/factories.py`, `mcp_sql/tools/factory.py`, `mcp_sql/db_inspection/factory.py`. Merge into fewer factory files.
- **Test helpers**: `mcp-template-sql/tests/` -- bookstore DB creation, test setup patterns. Copy and adapt.
- **Scripts**: `mcp-template-sql/scripts/` -- schema annotation script (`annotate.sh` or equivalent), secrets management (`secrets.sh`). Copy and adapt to use this project's `scripts/config.sh` pattern.
- **Bookstore test database**: `mcp-template-sql/data/db/bookstore.db` and its creation SQL/helpers. Copy the DB file into `tests/data/` and reuse the programmatic creation code in test helpers. Also copy the cached schema JSON from `mcp-template-sql/data/database/bookstore/` into `data/database/bookstore/` so the annotation pipeline does not need to run before tests or examples work.
- **dbs.yaml**: `mcp-template-sql/dbs.yaml` -- copy and trim to just the bookstore SQLite entry.

The main adaptation work is: updating import paths, replacing MCP-specific Context parameters with optional arguments, and converting dataclasses to Pydantic models where the project conventions require it. The logic, SQL queries, prompt templates, and overall architecture should be preserved as-is.

## Goal

Implement a SQL connector in `agentic_patterns/core/connectors/` and NL2SQL capabilities in `agentic_patterns/core/` that can later be exposed as MCP tools and A2A agent endpoints. Start with SQLite support; the architecture should allow adding Postgres/Starburst later via match/case dispatch in factory functions.

## Part 1: Data Models

Location: `agentic_patterns/core/connectors/sql/`

**database_type.py** -- `DatabaseType(str, Enum)` with SQLITE, POSTGRES values.

**db_connection_config.py** -- `DbConnectionConfig` (Pydantic model) with db_id, type, host, port, dbname, user, password, schema. Load from a `dbs.yaml` file in the project data directory. Password field supports `ENC:` prefix for encrypted values (defer encryption implementation; just document the convention).

**connection.py** -- Abstract `DbConnection` base class with `connect()`, `close()`, `cursor()` methods. SQLite subclass `DbConnectionSqlite` in `sqlite/connection.py`.

**column_info.py** -- `ColumnInfo` (Pydantic): name, data_type, nullable, description, is_enum, enum_values, is_primary_key.

**foreign_key_info.py** -- `ForeignKeyInfo` (Pydantic): name, columns, referenced_table, referenced_columns.

**index_info.py** -- `IndexInfo` (Pydantic): name, columns, is_unique, is_primary.

**table_info.py** -- `TableInfo` (Pydantic): name, columns, foreign_keys, indexes, description, sample_data_csv. Methods: `get_column()`, `get_primary_key_column()`.

**db_info.py** -- `DbInfo` (Pydantic): db_id, description, tables, example_queries. Methods: `get_table()`, `schema_sql()`, `save(path)`, `load(path)`. JSON serialization for caching.

**factories.py** -- `create_connection(db_id)` and `create_db_operations(db_id)` using match/case on DatabaseType.

## Part 2: Schema Inspection

Location: `agentic_patterns/core/connectors/sql/inspection/`

**schema_inspector.py** -- Abstract `DbSchemaInspector` with methods: `get_tables()`, `get_columns()`, `get_primary_keys()`, `get_foreign_keys()`, `get_indexes()`. Each returns `list[dict]` with standardized keys.

**sqlite/schema_inspector.py** -- SQLite implementation using `sqlite_master` and `PRAGMA` commands.

**schema_extractor.py** -- `DbSchemaExtractor` that orchestrates inspector calls to build `DbInfo` with all `TableInfo` objects. Handles caching: extract once, save as JSON to `data/database/{db_id}/{db_id}.db_info.json`.

**schema_formatter.py** -- `format_schema_sql(db_info) -> str` producing annotated CREATE TABLE statements with enum values in comments and sample data.

## Part 3: SQL Connector (Tools Layer)

Location: `agentic_patterns/core/connectors/sql/`

**db_operations.py** -- Abstract `DbOperations` with: `execute_select_query(query, limit) -> pd.DataFrame`, `fetch_row_by_id(table, row_id) -> dict | None`, `fetch_related_row(table, column, value) -> dict | None`.

**sqlite/operations.py** -- `DbOperationsqlite` implementing the above.

**operations.py** -- Database-agnostic business logic functions (the `_op` layer):
- `db_list_op()` -- list configured databases
- `db_list_tables_op(db_id)` -- list tables from cached schema
- `db_show_schema_op(db_id)` -- return full annotated schema SQL
- `db_show_table_details_op(db_id, table)` -- single table details
- `db_execute_sql_op(db_id, query, output_file, nl_query)` -- validate query (SELECT only, single statement), execute, save CSV + metadata JSON, return truncated preview
- `db_get_row_by_id_op(db_id, table, row_id)` -- fetch row with optional FK traversal

**query_validation.py** -- `validate_query(query: str)` enforcing SELECT-only, single-statement rules.

**query_result.py** -- `QueryResultMetadata` (Pydantic) for the companion .metadata.json files. Utility to save DataFrame to CSV and return truncated preview.

## Part 4: Schema Annotation (Offline Pipeline)

Location: `agentic_patterns/core/connectors/sql/annotation/`

**annotator.py** -- `DbSchemaAnnotator` orchestrating: schema extraction, AI-generated descriptions (database, tables, columns), enum detection, sample data collection, example query generation with validation. Each step is a method so the pipeline is extensible.

**enum_detector.py** -- Two-phase enum detection: quick screening (skip PKs, high cardinality, numeric/date types) then AI classification of candidates. Results cached in DbInfo.

**example_queries.py** -- Generate example SQL queries via AI, validate each by executing it, retry on failure up to N attempts.

Prompts for annotation stored in `prompts/sql/` as markdown templates: `enum_detection.md`, `schema_db_description.md`, `schema_table_description.md`, `schema_columns_description.md`, `example_query_generation.md`.

## Part 5: NL2SQL Agent

Location: `agentic_patterns/core/connectors/sql/nl2sql/`

**agent.py** -- `create_nl2sql_agent(db_id) -> Agent` and `run_nl2sql_query(db_id, query) -> tuple`. Uses `get_agent()` from core. Loads system prompt, composes instructions from cached schema + example queries + db-type-specific instructions.

**tools.py** -- Agent tool wrappers (`_tool` suffix) delegating to the `_op` functions: `db_execute_sql_tool`, `db_get_row_by_id_tool`, `csv_head_tool`, `csv_tail_tool`, `saved_queries_list_tool`.

**prompts.py** -- `get_system_prompt()`, `get_instructions(db_info)`. Composes base instructions + optional db-type and db-specific overrides.

Prompt templates in `prompts/sql/nl2sql/`: `nl2sql_system_prompt.md`, `nl2sql_instructions.md`, `db_type/sqlite_instructions.md`, `db_type/postgres_instructions.md`.

## Part 6: DB Catalog Agent (Optional)

Location: `agentic_patterns/core/connectors/sql/db_catalog/`

**agent.py** -- Pure classification agent (no tools) that selects the appropriate database for a natural-language question based on database descriptions and table summaries.

## Part 7: Configuration

**dbs.yaml** at project root or `data/` -- database connection definitions. Format:

```yaml
databases:
  bookstore:
    type: sqlite
    dbname: data/db/bookstore.db
  analytics:
    type: postgres
    host: localhost
    port: 5432
    dbname: analytics
    user: readonly
    password: ENC:...
    schema: public
```

**config.py** additions -- `DBS_YAML_PATH`, `DATABASE_CACHE_DIR` pointing to `data/database/`.

## Part 8: Examples

Location: `agentic_patterns/examples/connectors/`

**sql_connector_example.py** or `.ipynb` -- demonstrate schema discovery, query execution, row lookup with FK traversal using the bookstore SQLite test database.

**nl2sql_example.py** or `.ipynb` -- demonstrate NL2SQL agent answering natural-language questions against the bookstore database.

## Part 9: Tests

**tests/data/bookstore.db** -- SQLite database with books, authors, customers, orders tables and sample data, created programmatically by a test helper.

**tests/unit/connectors/sql/** -- test files covering:
- Schema inspection (tables, columns, FKs, indexes extraction)
- Schema extraction and caching (JSON round-trip)
- Query validation (SELECT-only, single statement)
- Operations (execute query, row by id, FK traversal)
- DbInfo/TableInfo model serialization

## Implementation Order

1. Data models (Part 1)
2. Schema inspection -- SQLite (Part 2)
3. SQL connector operations -- SQLite (Part 3)
4. Configuration and dbs.yaml loading (Part 7)
5. Schema annotation pipeline (Part 4)
6. NL2SQL agent and prompts (Part 5)
7. Examples (Part 8)
8. Tests (Part 9)
9. DB catalog agent (Part 6, if needed)

## File Count Estimate

Approximately 25-30 Python files and 8-10 prompt markdown files. Each file stays under the 500-line limit per project conventions.

## Notes

- Only SQLite is implemented initially. Postgres support means adding `postgres/` subdirectories with connection, inspector, extractor, and operations implementations, plus updating factory match/case branches.
- The MCP and A2A integration are out of scope for this plan; they will wrap the connector and NL2SQL agent created here.
- No mocking in tests; use a real SQLite bookstore database.

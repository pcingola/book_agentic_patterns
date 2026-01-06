# MCP SQL Design Document

Design patterns, architecture, and key learnings from the Natural Language to SQL MCP system.

## Core Principles

**Separation of Concerns through Layered Architecture**
The system separates interface, business logic, and database-specific implementations into distinct layers. Each layer has a clear responsibility and communicates through well-defined interfaces.

**Database Agnosticism**
All database-specific code is isolated behind abstract interfaces. Adding a new database type requires implementing a few interfaces and updating factory functions - no changes to business logic.

**Schema as First-Class Data**
Database schemas are extracted, annotated with AI-generated descriptions, and cached as JSON. This metadata becomes the foundation for natural language understanding and query generation.

**Minimal Server Initialization**
The MCP server is intentionally simple - just 10 lines initializing FastMCP and registering tools/resources. All complexity lives in separate modules.

## System Architecture

### Three-Component Design

**Schema Preparation (Offline)**
Extract schema structure, generate AI descriptions for databases/tables/columns, detect enum columns, collect sample data, and validate example queries. Cache everything as JSON for fast runtime access.

**MCP Server (Runtime)**
FastMCP-based server exposing tools for SQL execution and resources for schema access. Stateless design - all state lives in cached metadata and query result files.

**Standalone Agents**
Independent pydantic-ai agents that can work with or without the MCP server. Database catalog agent selects appropriate database, NL2SQL agent converts queries to SQL.

### Five-Layer Architecture

**Layer 1: Server (server.py)**
Minimal FastMCP initialization. Just creates the MCP instance and calls registration functions.

```python
mcp = FastMCP("SQL Database")
register_tools(mcp)
register_resources(mcp)
```

**Layer 2: MCP Interface (tools.py, resources.py)**
Tool decorators and resource generators. Pure MCP concerns - parameter validation, decorators, context passing. Delegates all logic to Layer 3.

**Layer 3: Business Logic (operations.py)**
Database-agnostic operations with `_op` suffix. Handles workflow, validation, file I/O, and result formatting. Uses Layer 4 interfaces for database access.

**Layer 4: Database Abstraction (db_operations.py)**
Abstract interface defining database operations. Three methods: execute_select_query, fetch_row_by_id, fetch_related_row. All return standard Python types (DataFrame, dict).

```python
class DbOperations(ABC):
    def __init__(self, connection: DbConnection):
        self.connection = connection

    @abstractmethod
    async def execute_select_query(query: str, ctx: Context) -> pd.DataFrame:
        pass

    @abstractmethod
    async def fetch_row_by_id(table: TableInfo, row_id: str, ctx: Context) -> dict | None:
        pass

    @abstractmethod
    async def fetch_related_row(table: TableInfo, column_name: str, value: str, ctx: Context) -> dict | None:
        pass
```

**Layer 5: Database Implementations (postgres/, sqlite/, starburst/)**
Concrete implementations using database-specific libraries. Handles connection management, query construction, parameterization, and error handling.

### Consistent Naming Convention

All layers use the same naming pattern with layer-specific suffixes:

- MCP tools: `db_list`, `db_show_schema` (no suffix - public API)
- Operations: `db_list_op`, `db_show_schema_op` (`_op` suffix)
- Agent tools: `db_list_tool`, `db_show_schema_tool` (`_tool` suffix)

This provides clear layer distinction, easier debugging (stack traces show which layer), and predictable API patterns.

## Design Patterns

### Factory Pattern with Match/Case

Database-specific components are created through factory functions using Python's match/case for type routing.

```python
def create_connection(db_id: str) -> DbConnection:
    configs = DbConnectionConfigs.get()
    db_config = configs.get_config(db_id)

    match db_config.type:
        case DatabaseType.POSTGRES:
            return DbConnectionPostgres(config=db_config)
        case DatabaseType.SQLITE:
            return DbConnectionSqlite(config=db_config)
        case DatabaseType.STARBURST:
            return DbConnectionStarburst(config=db_config)
        case _:
            raise ValueError(f"Unsupported database type: {db_config.type}")
```

Three factory files handle different concerns:
- data_models/factories.py: Database connections
- tools/factory.py: Database operations
- db_inspection/factory.py: Schema inspectors, extractors, enum detectors, sample data collectors

### Singleton Registries

Global registries provide centralized access to configurations and cached metadata.

**DbConnectionConfigs** - Registry for dbs.yaml configurations. Loads once on first access, provides lookup by db_id.

**DbInfos** - Registry for database metadata. Lazy loads DbInfo from JSON cache, provides connections and operations instances.

```python
db_infos = DbInfos.get()
db_info = db_infos.get_db_info(db_id)
db_ops = db_infos.get_operations(db_id)
```

### Schema Caching Strategy

Database schemas are extracted once and cached as JSON at `data/database/{db_id}/{db_id}.db_info.json`. Cache includes structure, descriptions, enums, sample data, and example queries.

Runtime operations never query information_schema. All metadata comes from the cache, enabling fast startup and offline operation.

Cache invalidation is manual - run annotation script to regenerate when schema changes.

### Query Result Management

Large query results are saved to CSV with companion JSON metadata files. Tools return truncated previews with file references.

```python
# Save query result
df.to_csv(csv_path)
metadata = QueryResultMetadata(
    sql_query=query,
    timestamp=datetime.now().isoformat(),
    row_count=len(df),
    db_id=db_id,
    natural_language_query=nl_query
)
metadata.save(csv_path.with_suffix(".metadata.json"))

# Return truncated preview
return truncate_df_to_csv(df, max_rows=10, max_cell_chars=80)
```

Separate tools (csv_head, csv_tail) provide access to full results. This keeps context size manageable while preserving complete data.

### Foreign Key Traversal

The get_row_by_id operation optionally follows foreign keys to fetch related data. Only follows outbound relationships (table references other tables), not inbound (other tables reference this table).

```python
async def fetch_related_data(db_info, db_ops, table, base_data, ctx):
    related_data = {}
    for fk in table.foreign_keys:
        fk_value = base_data.get(fk.columns[0])
        if fk_value is None:
            continue
        related_table = db_info.get_table(fk.referenced_table)
        related_row = await db_ops.fetch_related_row(
            related_table,
            fk.referenced_columns[0],
            fk_value,
            ctx
        )
        if related_row:
            related_data[fk.referenced_table] = related_row
    return related_data
```

### Markdown-Based Prompts

All agent prompts are stored as markdown files, not hardcoded strings. Template variables use curly brace syntax for runtime substitution.

Prompts are organized by purpose:
- nl2sql/nl2sql_system_prompt.md: Agent role definition
- nl2sql/nl2sql_instructions.md: Task instructions with {schema} and {example_queries_md} placeholders
- nl2sql/db_type/*.md: Database-specific SQL syntax guidance
- nl2sql/db_specific/*.md: Database-specific conventions

Agent loads prompts at initialization:

```python
system_prompt = get_system_prompt()
instructions = get_instructions(db_info)  # Substitutes variables
tools = get_all_tools(db_id)
agent = get_agent(system_prompt=system_prompt, instructions=instructions, tools=tools)
```

### AI-Powered Enum Detection

Columns are analyzed to determine if they represent enums. Two-stage process with quick screening followed by AI classification.

**Quick Screening**
Skip obvious non-enums: primary keys, columns with many unique values, numeric types, date types. Check distinct count and uniqueness ratio.

```python
distinct_count = await sql_helper.distinct_count(table_name, column_name)
if distinct_count > MAX_ENUM_VALUES:
    return False

total_rows = await sql_helper.table_row_count(table_name)
uniqueness_ratio = distinct_count / total_rows
if uniqueness_ratio > 0.5:
    return False
```

**AI Classification**
For candidates, fetch distinct values with counts and send to AI with table context. AI returns structured response with is_enum boolean and reasoning.

```python
distinct_values = await sql_helper.distinct_values(table_name, column_name)
prompt = enum_detection_template.format(
    db_description=db_info.description,
    table_schema=table_schema,
    column_name=column_name,
    column_data_type=column.data_type,
    row_count=total_rows,
    distinct_count=distinct_count,
    distinct_by_count=distinct_values
)
result = await ai_model.classify(prompt)
```

Results are cached in DbInfo JSON. Enum values are embedded in schema SQL as comments.

### Example Query Generation with Validation

Generate example SQL queries demonstrating database usage. Each query must:
- Be valid SQL that actually executes
- Return results (not empty)
- Cover diverse query patterns (filtering, aggregation, joins)

Generation process:
1. AI generates query with natural language description
2. System validates syntax (SELECT only, no multiple statements)
3. System executes query to verify it runs
4. System checks query returns results
5. On failure, retry with error feedback up to MAX_QUERY_GENERATION_RETRIES

```python
for attempt in range(MAX_QUERY_GENERATION_RETRIES):
    examples = await generate_queries(db_info, num_examples)
    for example in examples:
        try:
            df = execute_query(example.query)
            if len(df) > 0:
                validated_examples.append(example)
            else:
                feedback = "Query returned no results"
        except Exception as e:
            feedback = f"Query failed: {e}"
```

Only validated queries are saved to db_info.example_queries.

## Data Models

### Core Schema Models

**ColumnInfo**
Column metadata with data type, nullability, description, is_enum flag, enum_values list, is_primary_key, is_unique. Supports composite primary keys.

**ForeignKeyInfo**
Foreign key constraint with name, list of columns (supports composite keys), referenced table, list of referenced columns, on_delete action, on_update action.

**IndexInfo**
Index metadata with name, list of columns, is_unique flag, is_primary flag, index_type (btree, hash, etc).

**TableInfo**
Table metadata with name, list of columns, list of foreign_keys, list of indexes, description, sample_data_csv. Methods: get_column, get_primary_key_column, get_column_names.

**DbInfo**
Database metadata with db_id, description, list of tables, list of example_queries. Methods: get_table, get_table_names, schema_sql, save, load.

### Parent-Child References

DbInfo has list of TableInfo. Each TableInfo has reference back to parent DbInfo. Enables navigation in both directions.

```python
@dataclass
class TableInfo:
    name: str
    columns: list[ColumnInfo]
    db: DbInfo | None = None  # Parent reference

db_info = DbInfo(db_id="bookstore", tables=[])
table = TableInfo(name="books", columns=[])
db_info.add_table(table)  # Sets table.db = db_info
```

Serialization to JSON excludes parent references to avoid cycles. Deserialization reconstructs references.

### Configuration Models

**DatabaseType**
Enum with POSTGRES, SQLITE, STARBURST values. Used for match/case routing in factories.

**DbConnectionConfig**
Connection parameters with db_id, type, host, port, dbname, user, password, schema. Password supports ENC:... format for encrypted values.

**DbConnection (Abstract)**
Base class for database connections. Subclasses implement connect, close, cursor methods with database-specific libraries.

### Query Result Models

**QueryResultMetadata**
Metadata for saved queries with sql_query, timestamp, row_count, column_count, csv_filename, db_id, natural_language_query. Saved alongside CSV files as .metadata.json.

## Schema Inspection Architecture

### Abstract Inspector Interface

DbSchemaInspector defines standard interface for querying database catalog. Methods return lists of dictionaries with standardized keys.

```python
class DbSchemaInspector(ABC):
    @abstractmethod
    def get_tables(schema: str) -> list[dict]:
        pass

    @abstractmethod
    def get_columns(schema: str, table: str) -> list[dict]:
        pass

    @abstractmethod
    def get_primary_keys(schema: str, table: str) -> list[dict]:
        pass

    @abstractmethod
    def get_foreign_keys(schema: str, table: str) -> list[dict]:
        pass

    @abstractmethod
    def get_indexes(schema: str, table: str) -> list[dict]:
        pass
```

### Database-Specific Implementations

**Postgres**: Uses information_schema views and pg_catalog tables. Queries pg_constraint for full FK metadata including ON DELETE/UPDATE actions. Queries pg_index for index details.

**SQLite**: Uses sqlite_master table and PRAGMA commands. PRAGMA table_info for columns, PRAGMA foreign_key_list for FKs, PRAGMA index_list and index_info for indexes.

**Starburst/Trino**: Uses information_schema views. Limited support for constraints - no traditional indexes, minimal PK/FK support depending on connector.

### Schema Extractor Pattern

DbSchemaExtractor orchestrates inspector calls to build complete TableInfo objects. Handles caching, parent references, and aggregation of constraint information.

```python
class DbSchemaExtractor(ABC):
    def __init__(self, db_id: str, connection: DbConnection):
        self.db_id = db_id
        self.connection = connection
        self.inspector = create_schema_inspector(db_id, connection)

    def db_info(self, cache: bool = True) -> DbInfo:
        if cache and cache_exists:
            return DbInfo.load(db_id)

        db_info = DbInfo(db_id=db_id, description="", tables=[])
        table_names = self.inspector.get_tables(schema)

        for table_name in table_names:
            columns = self._extract_columns(table_name)
            foreign_keys = self._extract_foreign_keys(table_name)
            indexes = self._extract_indexes(table_name)

            table = TableInfo(
                name=table_name,
                columns=columns,
                foreign_keys=foreign_keys,
                indexes=indexes
            )
            db_info.add_table(table)

        return db_info
```

### Schema Formatting

DbFormatter generates annotated SQL schema with CREATE TABLE statements. Includes enum annotations, foreign key constraints, and index definitions as comments.

```sql
-- Database: bookstore
-- Online bookstore database tracking books, authors, customers, and orders

CREATE TABLE books (
    book_id INTEGER PRIMARY KEY,  -- Unique identifier for each book
    title VARCHAR(500) NOT NULL,  -- Book title
    genre VARCHAR(50),  -- Book genre [fiction, non-fiction, mystery, science-fiction, fantasy]
    price DECIMAL(10,2),  -- Book price in USD

    FOREIGN KEY (author_id) REFERENCES authors(author_id) ON DELETE SET NULL
);

-- Indexes:
-- idx_books_genre (genre)
```

## Agent Architecture

### Agent Tool Wrappers

Agents use pydantic-ai tools, not MCP tools. Agent tools wrap operations layer with `_tool` suffix. This allows agents to work standalone without MCP server.

```python
async def db_execute_sql_tool(db_id: str, query: str, output_file: str, nl_query: str | None = None) -> str:
    return await db_execute_sql_op(db_id, query, output_file, nl_query, ctx=None)

async def db_list_tool() -> str:
    return await db_list_op(ctx=None)
```

Agent initialization:

```python
tools = [
    db_execute_sql_tool,
    db_get_row_by_id_tool,
    saved_queries_list_tool,
    saved_query_get_details_tool,
    csv_head_tool,
    csv_tail_tool
]
agent = get_agent(system_prompt=system_prompt, instructions=instructions, tools=tools)
```

### Database Catalog Agent

Selects appropriate database for natural language query. Receives catalog of all databases with descriptions and table summaries.

```python
databases_info = format_catalog()  # "bookstore: Online bookstore with books, authors, customers..."
instructions = db_catalog_instructions_template.format(databases_info=databases_info)
agent = get_agent(system_prompt=system_prompt, instructions=instructions)

result = await agent.run(user_query)
# Returns: database name, reasoning
```

No tools needed - pure classification based on descriptions.

### NL2SQL Agent

Converts natural language to SQL and executes queries. Agent has access to full schema, example queries, and database-specific SQL syntax instructions.

Prompt assembly:

```python
system_prompt = load_markdown("nl2sql_system_prompt.md")
base_instructions = load_markdown("nl2sql_instructions.md")
db_type_instructions = load_markdown(f"db_type/{db_type}_instructions.md")
db_specific_instructions = load_markdown(f"db_specific/{db_id}_instructions.md")

instructions = base_instructions.format(
    schema=db_info.schema_sql(),
    example_queries_md=format_examples(db_info.example_queries)
)
instructions += db_type_instructions + db_specific_instructions

agent = get_agent(system_prompt=system_prompt, instructions=instructions, tools=tools)
```

Agent workflow:
1. Examine schema and example queries
2. Generate SQL query
3. Execute using db_execute_sql_tool
4. Return results or fetch additional data if needed
5. Summarize findings

## Security Patterns

### Read-Only Enforcement

Only SELECT queries allowed. Multiple validation layers:

```python
query_stripped = query.strip()
if query_stripped.rstrip(";").count(";") > 0:
    raise AixToolError("Multiple SQL statements not allowed")

query_upper = query_stripped.upper()
if not query_upper.startswith("SELECT"):
    raise AixToolError("Only SELECT queries allowed")
```

Database connections can be configured with read-only users for additional protection.

### Password Encryption

Passwords in dbs.yaml support encrypted format using Fernet encryption.

```yaml
databases:
  prod_db:
    password: ENC:gAAAAABh2k3j...
```

SecretsManager stores encryption keys in user home directory with 0600 permissions. CLI tool for encryption management:

```bash
./scripts/secrets.sh set-key
./scripts/secrets.sh set-db-password prod_db
./scripts/secrets.sh decrypt "ENC:..."
```

### Workspace Isolation

All file operations are scoped to /workspace directory. Path validation prevents directory traversal:

```python
csv_path = container_to_host_path(PurePosixPath(output_file), ctx=ctx)
if csv_path is None:
    raise AixToolError("Invalid file path")
```

Agent prompts explicitly state file paths are relative to /workspace.

## Testing Strategy

### Unit Testing with Real Databases

Tests use Python's unittest framework. Test database is SQLite with bookstore schema created programmatically.

```python
def create_test_bookstore_db() -> Path:
    db_path = Path("tests/data/bookstore.db")
    conn = sqlite3.connect(db_path)

    # Execute schema SQL
    conn.executescript(bookstore_schema_sql)

    # Insert test data
    conn.executescript(bookstore_data_sql)

    return db_path
```

Test helper provides reusable database setup:

```python
class TestOperations(unittest.TestCase):
    def setUp(self):
        self.db_path = create_test_bookstore_db()
        self.db_info = create_test_db_info(self.db_path)
```

### Test Coverage Areas

**Operations Tests**: MCP operations layer including db_list_op, db_execute_sql_op, db_get_row_by_id_op with foreign key traversal.

**Schema Tests**: Schema extraction, caching, DbInfo serialization, parent reference reconstruction.

**Inspector Tests**: Low-level catalog queries for tables, columns, constraints. Verify correct metadata extraction.

**Enum Detection Tests**: Quick screening filters (PKs, high cardinality, unique values), distinct value queries, sample uniqueness ratios, AI classification, caching.

**Foreign Key Tests**: FK detection including composite keys, ON DELETE/UPDATE actions, metadata completeness.

**Index Tests**: Index detection including types, uniqueness flags, primary key indexes.

### Async Test Patterns

Tests use asyncio for async operations:

```python
class TestOperations(unittest.TestCase):
    def test_execute_query(self):
        async def run_test():
            result = await db_execute_sql_op(
                db_id="bookstore",
                query="SELECT * FROM books WHERE genre = 'fiction'",
                output_file="results.csv"
            )
            self.assertIn("fiction", result)

        asyncio.run(run_test())
```

## Extension Points

### Adding New Database Types

Implement four components:

**DbConnection**: Connection management with connect, close, cursor methods using database-specific driver.

**DbSchemaInspector**: Catalog queries returning standardized dictionaries. Map database-specific catalog schema to standard format.

**DbSchemaExtractor**: Orchestrate inspector calls to build TableInfo objects. Handle database-specific quirks.

**DbOperations**: Query execution with execute_select_query, fetch_row_by_id, fetch_related_row. Use parameterized queries for security.

Update three factory functions with new match/case branch:

```python
# data_models/factories.py
case DatabaseType.SNOWFLAKE:
    return DbConnectionSnowflake(config=db_config)

# tools/factory.py
case DatabaseType.SNOWFLAKE:
    return DbOperationsSnowflake(connection)

# db_inspection/factory.py
case DatabaseType.SNOWFLAKE:
    return DbSchemaInspectorSnowflake(db_id, connection)
```

Create database-specific SQL instructions in prompts/nl2sql/db_type/snowflake_instructions.md.

No changes needed to server, tools, resources, business logic, or agents.

### Adding New Schema Annotators

Schema annotation pipeline is extensible. Current steps: database description, table descriptions, column descriptions, enum detection, sample data, example queries.

To add new annotation step:

```python
class DbSchemaAnnotator:
    async def annotate_relationships(self):
        """Detect implicit relationships not captured by FKs."""
        for table in self.db_info.tables:
            # Analyze column names and patterns
            # Update table metadata
            pass

    async def run(self):
        self.extract_schema()
        await self.annotate_db_description()
        await self.annotate_table_descriptions()
        await self.annotate_column_descriptions()
        await self.annotate_relationships()  # New step
        await self.detect_enums()
        self.add_sample_data()
        await self.generate_example_queries()
```

### Adding New MCP Tools

Register new tools in tools.py:

```python
@mcp.tool()
async def db_analyze_query_performance(db_id: str, query: str, ctx: Context) -> str:
    """Analyze query execution plan and provide optimization suggestions."""
    return await db_analyze_query_performance_op(db_id, query, ctx)
```

Implement operation in operations.py:

```python
async def db_analyze_query_performance_op(db_id: str, query: str, ctx: Context) -> str:
    db_ops = DbInfos.get().get_operations(db_id)
    plan = await db_ops.get_query_plan(query, ctx)
    # Analyze and return suggestions
    return format_performance_report(plan)
```

Add abstract method to DbOperations if needed:

```python
class DbOperations(ABC):
    @abstractmethod
    async def get_query_plan(query: str, ctx: Context) -> dict:
        pass
```

Implement in database-specific operations classes.

### Adding New MCP Resources

Register resources in resources.py:

```python
@mcp.resource("db://{db_id}/statistics")
async def db_statistics_resource(uri: str) -> str:
    db_id = extract_db_id_from_uri(uri)
    db_info = DbInfos.get().get_db_info(db_id)
    stats = compute_statistics(db_info)
    return format_statistics_markdown(stats)
```

Resources are read-only views of database metadata. Use cached DbInfo when possible to avoid database queries.

## Key Learnings

**Cache Metadata Aggressively**
Runtime performance depends on avoiding catalog queries. Extract schema once, annotate with AI, cache as JSON. Operations only touch the database for actual data queries.

**Standardize Early**
Database-specific code returns standardized dictionaries/types immediately. Conversion happens at the boundary, not throughout the codebase. Makes business logic database-agnostic.

**Layer Responsibilities Clearly**
Each layer has single responsibility: server (initialization), interface (MCP protocol), operations (workflow), abstraction (interface definition), implementations (database specifics). Prevents concerns from bleeding across boundaries.

**Use Match/Case for Type Routing**
Python's match/case is perfect for routing by database type. Exhaustive checking catches missing implementations. Clear and maintainable.

**Validate Queries Defensively**
Multiple validation layers for SQL queries: strip whitespace, check for multiple statements, verify SELECT only, use parameterized queries. Security cannot rely on AI not generating dangerous SQL.

**Save Large Results, Return Previews**
Query results go to CSV files with metadata. Tools return truncated previews with file references. Keeps context manageable while preserving complete data for later analysis.

**Make Agents Standalone**
Agent tools wrap operations layer, not MCP layer. Agents can run in notebooks, scripts, or other contexts without MCP server. Increases reusability.

**Markdown for Prompts**
Store prompts as markdown files with template variables. Easier to version, review, and modify than embedded strings. Enables database-specific instructions without code changes.

**AI for Tedious Classification**
Enum detection and description generation are perfect AI tasks. Humans can verify but shouldn't do manually. Quick screening filters out obvious cases before invoking AI.

**Test with Real Databases**
Tests use actual SQLite database, not mocks. Catches real-world issues with SQL syntax, data types, and constraint behavior. Test helpers make setup reasonable.

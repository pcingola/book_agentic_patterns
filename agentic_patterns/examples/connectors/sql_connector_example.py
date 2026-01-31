"""SQL connector example -- demonstrates schema discovery, query execution, and row lookup."""

import asyncio
from pathlib import Path

from agentic_patterns.core.connectors.sql.config import DATABASE_CACHE_DIR, DBS_YAML_PATH
from agentic_patterns.core.connectors.sql.db_connection_config import DbConnectionConfigs
from agentic_patterns.core.connectors.sql.db_infos import DbInfos
from agentic_patterns.core.connectors.sql.inspection.schema_extractor import DbSchemaExtractor
from agentic_patterns.core.connectors.sql.operations import (
    db_execute_sql_op,
    db_get_row_by_id_op,
    db_list_op,
    db_list_tables_op,
    db_show_schema_op,
)


DB_ID = "bookstore"


def setup():
    """Load database configurations and metadata."""
    DbConnectionConfigs.reset()
    DbInfos.reset()
    DbConnectionConfigs.get().load_from_yaml(DBS_YAML_PATH)


async def main():
    setup()

    # List databases
    print("=== Available Databases ===")
    print(await db_list_op())

    # List tables
    print("\n=== Tables ===")
    print(await db_list_tables_op(DB_ID))

    # Show schema
    print("\n=== Schema ===")
    print(await db_show_schema_op(DB_ID))

    # Execute a query
    print("\n=== Query: Top 5 books by price ===")
    result = await db_execute_sql_op(DB_ID, "SELECT title, price FROM books ORDER BY price DESC LIMIT 5")
    print(result)

    # Get row by ID with related data
    print("\n=== Book #1 with related author ===")
    row = await db_get_row_by_id_op(DB_ID, "books", "1", fetch_related=True)
    print(row)


if __name__ == "__main__":
    asyncio.run(main())

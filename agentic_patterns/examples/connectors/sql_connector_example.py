"""SQL connector example -- demonstrates schema discovery, query execution, and row lookup."""

import asyncio

from agentic_patterns.core.connectors.sql.config import DBS_YAML_PATH
from agentic_patterns.core.connectors.sql.connector import SqlConnector
from agentic_patterns.core.connectors.sql.db_connection_config import DbConnectionConfigs
from agentic_patterns.core.connectors.sql.db_infos import DbInfos


DB_ID = "bookstore"


def setup():
    """Load database configurations and metadata."""
    DbConnectionConfigs.reset()
    DbInfos.reset()
    DbConnectionConfigs.get().load_from_yaml(DBS_YAML_PATH)


async def main():
    setup()
    connector = SqlConnector()

    print("=== Available Databases ===")
    print(await connector.list_databases())

    print("\n=== Tables ===")
    print(await connector.list_tables(DB_ID))

    print("\n=== Schema ===")
    print(await connector.show_schema(DB_ID))

    print("\n=== Query: Top 5 books by price ===")
    result = await connector.execute_sql(DB_ID, "SELECT title, price FROM books ORDER BY price DESC LIMIT 5")
    print(result)

    print("\n=== Book #1 with related author ===")
    row = await connector.get_row_by_id(DB_ID, "books", "1", fetch_related=True)
    print(row)


if __name__ == "__main__":
    asyncio.run(main())

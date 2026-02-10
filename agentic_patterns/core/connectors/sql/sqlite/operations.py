"""SQLite-specific database operations."""

import sqlite3

import pandas as pd

from agentic_patterns.core.connectors.sql.db_operations import DbOperations
from agentic_patterns.core.connectors.sql.sqlite.connection import DbConnectionSqlite
from agentic_patterns.core.connectors.sql.table_info import TableInfo


class DbOperationsSqlite(DbOperations):
    """SQLite implementation of database operations."""

    def __init__(self, connection: DbConnectionSqlite) -> None:
        super().__init__(connection)

    async def execute_select_query(self, query: str) -> pd.DataFrame:
        try:
            df = pd.read_sql_query(query, self.connection.connect())
            return df
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error executing query: {e}") from e

    async def fetch_row_by_id(self, table: TableInfo, row_id: str) -> dict | None:
        pk_column = table.get_primary_key_column()
        if pk_column is None:
            raise RuntimeError(
                f"Table '{table.name}' does not have a primary key column"
            )
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                f'SELECT * FROM "{table.name}" WHERE "{pk_column}" = ?', (row_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error fetching row: {e}") from e

    async def fetch_related_row(
        self, table: TableInfo, column_name: str, value: str
    ) -> dict | None:
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                f'SELECT * FROM "{table.name}" WHERE "{column_name}" = ?', (value,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error fetching related row: {e}") from e

"""SQLite connection management."""

import sqlite3

from agentic_patterns.core.connectors.sql.connection import DbConnection
from agentic_patterns.core.connectors.sql.db_connection_config import DbConnectionConfig


class DbConnectionSqlite(DbConnection):
    """Manages SQLite database connection."""

    def __init__(self, config: DbConnectionConfig) -> None:
        super().__init__(config)

    def connect(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.config.dbname)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def cursor(self):
        if self._conn is None:
            self.connect()
        return self._conn.cursor()

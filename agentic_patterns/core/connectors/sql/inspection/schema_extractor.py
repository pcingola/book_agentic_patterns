"""Schema extractor -- orchestrates schema extraction and caching."""

import logging
from pathlib import Path

from agentic_patterns.core.connectors.sql.config import DATABASE_CACHE_DIR, DB_INFO_EXT
from agentic_patterns.core.connectors.sql.connection import DbConnection
from agentic_patterns.core.connectors.sql.db_info import DbInfo
from agentic_patterns.core.connectors.sql.inspection.schema_inspector import (
    DbSchemaInspector,
)
from agentic_patterns.core.connectors.sql.table_info import TableInfo


logger = logging.getLogger(__name__)


class DbSchemaExtractor:
    """Orchestrates schema extraction, caching, and file I/O."""

    def __init__(self, db_id: str) -> None:
        self.db_id = db_id
        self.connection: DbConnection | None = None
        self.inspector: DbSchemaInspector | None = None

    def connect(self) -> "DbSchemaExtractor":
        from agentic_patterns.core.connectors.sql.factories import (
            create_connection,
            create_schema_inspector,
        )

        self.connection = create_connection(self.db_id)
        self.connection.connect()
        self.inspector = create_schema_inspector(self.db_id, self.connection)
        return self

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None
            self.inspector = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def db_info(self, cache: bool = True, cache_path: Path | None = None) -> DbInfo:
        """Extract complete database schema information."""
        if cache_path is None:
            cache_path = DATABASE_CACHE_DIR / self.db_id / f"{self.db_id}{DB_INFO_EXT}"

        if cache and cache_path.exists():
            logger.info(f"Loading database info from cache: {cache_path}")
            return DbInfo.load(self.db_id, cache_path)

        db_info = DbInfo(
            db_id=self.db_id,
            description="",
            tables=[],
            cache_file_path=cache_path if cache else None,
        )

        assert self.inspector is not None, (
            "Inspector not initialized. Call connect() first."
        )
        table_names = self.inspector.get_tables()
        view_map = self.inspector.is_view_map()

        for table_name in table_names:
            table = self.table_info(table_name, is_view=view_map.get(table_name, False))
            db_info.add_table(table)

        if cache:
            logger.info(f"Saving database info to cache: {cache_path}")
            db_info.save(cache_path)

        return db_info

    def table_info(self, table_name: str, is_view: bool = False) -> TableInfo:
        """Extract schema information for a single table."""
        assert self.inspector is not None, (
            "Inspector not initialized. Call connect() first."
        )
        table = TableInfo(name=table_name, is_view=is_view, columns=[])
        columns = self.inspector.get_columns(table_name)
        for col in columns:
            table.add_column(col)
        table.foreign_keys = self.inspector.get_foreign_keys(table_name)
        table.indexes = self.inspector.get_indexes(table_name)
        return table

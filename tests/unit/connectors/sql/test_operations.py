"""Tests for SQLite database operations."""

import asyncio
import tempfile
import unittest
from pathlib import Path

from tests.data.sql.db_helper import create_test_bookstore_db

from agentic_patterns.core.connectors.sql.column_info import ColumnInfo
from agentic_patterns.core.connectors.sql.db_connection_config import DbConnectionConfig, DbConnectionConfigs
from agentic_patterns.core.connectors.sql.database_type import DatabaseType
from agentic_patterns.core.connectors.sql.db_info import DbInfo
from agentic_patterns.core.connectors.sql.db_infos import DbInfos
from agentic_patterns.core.connectors.sql.foreign_key_info import ForeignKeyInfo
from agentic_patterns.core.connectors.sql.operations import db_execute_sql_op, db_get_row_by_id_op
from agentic_patterns.core.connectors.sql.table_info import TableInfo


class TestOperationsSqlite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls._tmpdir.name) / "test_bookstore.db"
        create_test_bookstore_db(cls.db_path)

        # Reset singletons
        DbConnectionConfigs.reset()
        DbInfos.reset()

        # Register DB config
        config = DbConnectionConfig(db_id="test_bookstore", type=DatabaseType.SQLITE, dbname=str(cls.db_path))
        DbConnectionConfigs.get().add(config)

        # Create minimal DbInfo
        db_info = DbInfo(db_id="test_bookstore", description="Test bookstore", tables=[])
        authors = TableInfo(name="authors", columns=[])
        authors.add_column(ColumnInfo(name="id", data_type="INTEGER", is_nullable=False, is_primary_key=True))
        authors.add_column(ColumnInfo(name="name", data_type="TEXT", is_nullable=False))
        db_info.add_table(authors)

        books = TableInfo(name="books", columns=[], foreign_keys=[
            ForeignKeyInfo(columns=["author_id"], referenced_table="authors", referenced_columns=["id"]),
        ])
        books.add_column(ColumnInfo(name="id", data_type="INTEGER", is_nullable=False, is_primary_key=True))
        books.add_column(ColumnInfo(name="title", data_type="TEXT", is_nullable=False))
        books.add_column(ColumnInfo(name="author_id", data_type="INTEGER", is_nullable=False))
        db_info.add_table(books)

        DbInfos.get().add(db_info)

    @classmethod
    def tearDownClass(cls):
        DbInfos.reset()
        DbConnectionConfigs.reset()
        cls._tmpdir.cleanup()

    def test_execute_select(self):
        result = asyncio.run(db_execute_sql_op("test_bookstore", "SELECT COUNT(*) as cnt FROM books"))
        self.assertIn("Result:", result)

    def test_execute_select_multiple_rows(self):
        result = asyncio.run(db_execute_sql_op("test_bookstore", "SELECT id, title FROM books LIMIT 3"))
        self.assertIn("Rows:", result)

    def test_execute_select_with_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "results.csv"
            result = asyncio.run(db_execute_sql_op("test_bookstore", "SELECT * FROM books", str(out_path)))
            self.assertTrue(out_path.exists())

    def test_get_row_by_id(self):
        result = asyncio.run(db_get_row_by_id_op("test_bookstore", "books", "1"))
        self.assertIn("title", result)

    def test_get_row_not_found(self):
        result = asyncio.run(db_get_row_by_id_op("test_bookstore", "books", "99999"))
        self.assertIn("error", result)

    def test_get_row_with_related(self):
        result = asyncio.run(db_get_row_by_id_op("test_bookstore", "books", "1", fetch_related=True))
        self.assertIn("data", result)
        self.assertIn("related", result)
        self.assertIn("authors", result["related"])

    def test_table_not_found(self):
        result = asyncio.run(db_get_row_by_id_op("test_bookstore", "nonexistent", "1"))
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()

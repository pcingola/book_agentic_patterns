"""Tests for SQLite schema inspection."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from tests.data.sql.db_helper import create_test_bookstore_db

from agentic_patterns.core.connectors.sql.inspection.sqlite.schema_inspector import DbSchemaInspectorSqlite


class TestSchemaInspectionSqlite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls._tmpdir.name) / "test_bookstore.db"
        create_test_bookstore_db(cls.db_path)
        cls.conn = sqlite3.connect(str(cls.db_path))
        cls.inspector = DbSchemaInspectorSqlite(connection=cls.conn, schema="main")

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls._tmpdir.cleanup()

    def test_get_tables(self):
        tables = self.inspector.get_tables()
        self.assertIn("books", tables)
        self.assertIn("authors", tables)
        self.assertIn("customers", tables)
        self.assertIn("orders", tables)

    def test_get_columns(self):
        columns = self.inspector.get_columns("books")
        col_names = [c.name for c in columns]
        self.assertIn("id", col_names)
        self.assertIn("title", col_names)
        self.assertIn("price", col_names)

    def test_primary_keys(self):
        pks = self.inspector.get_primary_keys("books")
        self.assertIn("id", pks)

    def test_foreign_keys(self):
        fks = self.inspector.get_foreign_keys("books")
        ref_tables = [fk.referenced_table for fk in fks]
        self.assertIn("authors", ref_tables)
        self.assertIn("publishers", ref_tables)

    def test_indexes(self):
        indexes = self.inspector.get_indexes("books")
        index_names = [idx.name for idx in indexes]
        self.assertTrue(any("genre" in name for name in index_names))

    def test_is_view_map(self):
        view_map = self.inspector.is_view_map()
        self.assertFalse(view_map.get("books", True))

    def test_column_types(self):
        columns = self.inspector.get_columns("books")
        id_col = next(c for c in columns if c.name == "id")
        self.assertEqual(id_col.data_type, "INTEGER")
        price_col = next(c for c in columns if c.name == "price")
        self.assertEqual(price_col.data_type, "REAL")

    def test_column_nullable(self):
        columns = self.inspector.get_columns("books")
        title_col = next(c for c in columns if c.name == "title")
        self.assertFalse(title_col.is_nullable)
        genre_col = next(c for c in columns if c.name == "genre")
        self.assertTrue(genre_col.is_nullable)


if __name__ == "__main__":
    unittest.main()

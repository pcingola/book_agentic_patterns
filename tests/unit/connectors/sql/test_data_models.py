"""Tests for SQL connector data models."""

import json
import tempfile
import unittest
from pathlib import Path

from agentic_patterns.core.connectors.sql.column_info import ColumnInfo
from agentic_patterns.core.connectors.sql.database_type import DatabaseType
from agentic_patterns.core.connectors.sql.db_info import DbInfo
from agentic_patterns.core.connectors.sql.foreign_key_info import ForeignKeyInfo
from agentic_patterns.core.connectors.sql.index_info import IndexInfo
from agentic_patterns.core.connectors.sql.table_info import TableInfo


class TestDataModels(unittest.TestCase):

    def test_database_type_values(self):
        self.assertEqual(DatabaseType.SQLITE.value, "sqlite")
        self.assertEqual(DatabaseType.POSTGRES.value, "postgres")
        self.assertEqual(DatabaseType("sqlite"), DatabaseType.SQLITE)

    def test_column_info_roundtrip(self):
        col = ColumnInfo(name="id", data_type="INTEGER", is_nullable=False, is_primary_key=True)
        d = col.to_dict()
        col2 = ColumnInfo.from_dict(d)
        self.assertEqual(col2.name, "id")
        self.assertTrue(col2.is_primary_key)

    def test_column_info_enum(self):
        col = ColumnInfo(name="status", data_type="TEXT", is_nullable=True, is_enum=True, enum_values=["active", "closed"])
        self.assertIn("enum(2 values)", str(col))

    def test_foreign_key_info_roundtrip(self):
        fk = ForeignKeyInfo(name="fk_author", columns=["author_id"], referenced_table="authors", referenced_columns=["id"])
        d = fk.to_dict()
        fk2 = ForeignKeyInfo.from_dict(d)
        self.assertEqual(fk2.referenced_table, "authors")

    def test_index_info_roundtrip(self):
        idx = IndexInfo(name="idx_books_genre", columns=["genre"], is_unique=False)
        d = idx.to_dict()
        idx2 = IndexInfo.from_dict(d)
        self.assertEqual(idx2.name, "idx_books_genre")

    def test_table_info_roundtrip(self):
        col = ColumnInfo(name="id", data_type="INTEGER", is_nullable=False, is_primary_key=True)
        table = TableInfo(name="books", columns=[col], description="Books table")
        d = table.to_dict()
        table2 = TableInfo.from_dict(d)
        self.assertEqual(table2.name, "books")
        self.assertEqual(len(table2.columns), 1)
        self.assertEqual(table2.get_primary_key_column(), "id")

    def test_table_info_parent_reference(self):
        col = ColumnInfo(name="id", data_type="INTEGER", is_nullable=False, is_primary_key=True)
        table = TableInfo(name="test", columns=[])
        table.add_column(col)
        self.assertIs(col.table, table)

    def test_db_info_roundtrip(self):
        col = ColumnInfo(name="id", data_type="INTEGER", is_nullable=False, is_primary_key=True)
        table = TableInfo(name="books", columns=[col])
        db = DbInfo(db_id="test", description="Test DB", tables=[table], example_queries=[{"description": "Get all", "query": "SELECT * FROM books"}])
        d = db.to_dict()
        db2 = DbInfo.from_dict(d)
        self.assertEqual(db2.db_id, "test")
        self.assertEqual(len(db2.tables), 1)
        self.assertEqual(len(db2.example_queries), 1)

    def test_db_info_save_load(self):
        col = ColumnInfo(name="id", data_type="INTEGER", is_nullable=False, is_primary_key=True)
        table = TableInfo(name="books", columns=[col])
        db = DbInfo(db_id="test", description="Test", tables=[table])

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.db_info.json"
            db.save(path)
            self.assertTrue(path.exists())

            db2 = DbInfo.load(input_path=path)
            self.assertEqual(db2.db_id, "test")
            self.assertEqual(len(db2.tables), 1)

    def test_db_info_get_table(self):
        table = TableInfo(name="books", columns=[])
        db = DbInfo(db_id="test", description="", tables=[table])
        self.assertIsNotNone(db.get_table("books"))
        self.assertIsNone(db.get_table("nonexistent"))

    def test_db_info_get_table_names(self):
        t1 = TableInfo(name="books", columns=[])
        t2 = TableInfo(name="authors", columns=[])
        db = DbInfo(db_id="test", description="", tables=[t1, t2])
        self.assertEqual(db.get_table_names(), ["authors", "books"])


if __name__ == "__main__":
    unittest.main()

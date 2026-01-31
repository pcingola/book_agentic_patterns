"""Tests for SQL query validation."""

import unittest

from agentic_patterns.core.connectors.sql.query_validation import QueryValidationError, validate_query


class TestQueryValidation(unittest.TestCase):

    def test_valid_select(self):
        validate_query("SELECT * FROM books")

    def test_valid_select_with_semicolon(self):
        validate_query("SELECT * FROM books;")

    def test_empty_query(self):
        with self.assertRaises(QueryValidationError):
            validate_query("")

    def test_multiple_statements(self):
        with self.assertRaises(QueryValidationError):
            validate_query("SELECT 1; SELECT 2")

    def test_non_select(self):
        with self.assertRaises(QueryValidationError):
            validate_query("DELETE FROM books")

    def test_insert_rejected(self):
        with self.assertRaises(QueryValidationError):
            validate_query("INSERT INTO books VALUES (1)")

    def test_update_rejected(self):
        with self.assertRaises(QueryValidationError):
            validate_query("UPDATE books SET title = 'x'")

    def test_drop_rejected(self):
        with self.assertRaises(QueryValidationError):
            validate_query("DROP TABLE books")


if __name__ == "__main__":
    unittest.main()

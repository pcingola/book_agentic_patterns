"""Unit tests for CSV connector."""

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentic_patterns.core.connectors.csv import CsvConnector


class TestCsvConnector(unittest.TestCase):
    """Test CSV connector operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_dir = Path(self.temp_dir.name)
        self.patcher = patch(
            "agentic_patterns.core.workspace.WORKSPACE_DIR", self.workspace_dir
        )
        self.patcher.start()

        self.workspace_root = self.workspace_dir / "default_user" / "default_session"
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.connector = CsvConnector()

    def tearDown(self):
        """Clean up test fixtures."""
        self.patcher.stop()
        self.temp_dir.cleanup()

    def _create_csv(self, filename: str, rows: list[list[str]]) -> str:
        """Create a CSV file for testing and return sandbox path."""
        csv_path = self.workspace_root / filename
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        return f"/workspace/{filename}"

    def test_head_csv_basic(self):
        """Test basic CSV head."""
        sandbox_path = self._create_csv(
            "test.csv",
            [["name", "age", "city"], ["Alice", "30", "NYC"], ["Bob", "25", "LA"]],
        )

        result = self.connector.head(sandbox_path, n=10)
        self.assertIn("Alice", result)
        self.assertIn("Bob", result)
        self.assertIn("name", result)

    def test_head_csv_row_limit(self):
        """Test CSV head with row limit."""
        rows = [["id", "value"]] + [[str(i), f"val_{i}"] for i in range(100)]
        sandbox_path = self._create_csv("large.csv", rows)

        result = self.connector.head(sandbox_path, n=5)
        self.assertIn("id", result)
        self.assertIn("val_0", result)
        self.assertIn("val_4", result)
        self.assertNotIn("val_50", result)

    def test_head_csv_file_not_found(self):
        """Test head with non-existent file."""
        with self.assertRaises(FileNotFoundError):
            self.connector.head("/workspace/nonexistent.csv")

    def test_tail_csv_basic(self):
        """Test basic CSV tail."""
        rows = [["id", "value"]] + [[str(i), f"val_{i}"] for i in range(20)]
        sandbox_path = self._create_csv("test.csv", rows)

        result = self.connector.tail(sandbox_path, n=5)
        self.assertIn("val_19", result)
        self.assertIn("val_15", result)
        self.assertNotIn("val_0", result)

    def test_tail_csv_small_file(self):
        """Test tail on file with fewer rows than n."""
        sandbox_path = self._create_csv(
            "test.csv", [["name", "age"], ["Alice", "30"], ["Bob", "25"]]
        )

        result = self.connector.tail(sandbox_path, n=10)
        self.assertIn("Alice", result)
        self.assertIn("Bob", result)

    def test_read_csv_row(self):
        """Test reading specific row."""
        sandbox_path = self._create_csv(
            "test.csv",
            [["name", "age"], ["Alice", "30"], ["Bob", "25"], ["Charlie", "35"]],
        )

        result = self.connector.read_row(sandbox_path, row_number=2)
        self.assertIn("Bob", result)
        self.assertIn("25", result)
        self.assertIn("[Row 2]", result)

    def test_read_csv_row_out_of_range(self):
        """Test reading row beyond file length."""
        sandbox_path = self._create_csv("test.csv", [["name", "age"], ["Alice", "30"]])

        with self.assertRaises(IndexError):
            self.connector.read_row(sandbox_path, row_number=10)

    def test_get_csv_headers(self):
        """Test getting CSV headers."""
        sandbox_path = self._create_csv(
            "test.csv", [["name", "age", "city"], ["Alice", "30", "NYC"]]
        )

        result = self.connector.headers(sandbox_path)
        self.assertIn("name", result)
        self.assertIn("age", result)
        self.assertIn("city", result)
        self.assertIn("3 total", result)

    def test_find_csv_by_column_name(self):
        """Test finding rows by column name."""
        sandbox_path = self._create_csv(
            "test.csv",
            [
                ["name", "status"],
                ["Alice", "active"],
                ["Bob", "inactive"],
                ["Charlie", "active"],
            ],
        )

        result = self.connector.find_rows(
            sandbox_path, column="status", value="active", limit=10
        )
        self.assertIn("Alice", result)
        self.assertIn("Charlie", result)
        self.assertNotIn("Bob", result)

    def test_find_csv_by_column_index(self):
        """Test finding rows by column index."""
        sandbox_path = self._create_csv(
            "test.csv", [["name", "status"], ["Alice", "active"], ["Bob", "inactive"]]
        )

        result = self.connector.find_rows(
            sandbox_path, column=1, value="active", limit=10
        )
        self.assertIn("Alice", result)
        self.assertNotIn("Bob", result)

    def test_find_csv_no_matches(self):
        """Test finding rows with no matches."""
        sandbox_path = self._create_csv(
            "test.csv", [["name", "status"], ["Alice", "active"]]
        )

        result = self.connector.find_rows(
            sandbox_path, column="status", value="deleted", limit=10
        )
        self.assertIn("[No rows found", result)

    def test_update_csv_cell_by_column_name(self):
        """Test updating cell by column name."""
        sandbox_path = self._create_csv(
            "test.csv", [["name", "status"], ["Alice", "active"], ["Bob", "inactive"]]
        )

        result = self.connector.update_cell(
            sandbox_path, row_number=1, column="status", value="pending"
        )
        self.assertIn("Updated", result)
        self.assertIn("status", result)
        self.assertIn("pending", result)

        content = (self.workspace_root / "test.csv").read_text()
        self.assertIn("pending", content)

    def test_update_csv_cell_by_column_index(self):
        """Test updating cell by column index."""
        sandbox_path = self._create_csv(
            "test.csv", [["name", "status"], ["Alice", "active"]]
        )

        result = self.connector.update_cell(
            sandbox_path, row_number=1, column=1, value="inactive"
        )
        self.assertIn("Updated", result)

        content = (self.workspace_root / "test.csv").read_text()
        self.assertIn("inactive", content)

    def test_update_csv_row(self):
        """Test updating entire row by key."""
        sandbox_path = self._create_csv(
            "test.csv",
            [
                ["customer_id", "name", "status"],
                ["C-001", "Alice", "active"],
                ["C-002", "Bob", "inactive"],
            ],
        )

        result = self.connector.update_row(
            sandbox_path,
            key_column="customer_id",
            key_value="C-001",
            updates={"name": "Alicia", "status": "pending"},
        )
        self.assertIn("Updated 1 row", result)

        content = (self.workspace_root / "test.csv").read_text()
        self.assertIn("Alicia", content)
        self.assertIn("pending", content)

    def test_update_csv_row_no_match(self):
        """Test updating row with no matching key."""
        sandbox_path = self._create_csv(
            "test.csv", [["customer_id", "name"], ["C-001", "Alice"]]
        )

        result = self.connector.update_row(
            sandbox_path,
            key_column="customer_id",
            key_value="C-999",
            updates={"name": "Bob"},
        )
        self.assertIn("[No rows found", result)

    def test_append_csv_with_dict(self):
        """Test appending row using dict."""
        sandbox_path = self._create_csv("test.csv", [["name", "age"], ["Alice", "30"]])

        result = self.connector.append(
            sandbox_path, values={"name": "Bob", "age": "25"}
        )
        self.assertIn("Appended 1 row", result)
        self.assertIn("now 2 rows", result)

        content = (self.workspace_root / "test.csv").read_text()
        self.assertIn("Bob", content)
        self.assertIn("25", content)

    def test_append_csv_with_list(self):
        """Test appending row using list."""
        sandbox_path = self._create_csv("test.csv", [["name", "age"], ["Alice", "30"]])

        result = self.connector.append(sandbox_path, values=["Bob", "25"])
        self.assertIn("Appended 1 row", result)

        content = (self.workspace_root / "test.csv").read_text()
        self.assertIn("Bob", content)

    def test_append_csv_missing_column(self):
        """Test appending row with missing column value."""
        sandbox_path = self._create_csv("test.csv", [["name", "age"], ["Alice", "30"]])

        with self.assertRaises(ValueError):
            self.connector.append(sandbox_path, values={"name": "Bob"})

    def test_delete_csv(self):
        """Test deleting rows."""
        sandbox_path = self._create_csv(
            "test.csv",
            [
                ["name", "status"],
                ["Alice", "active"],
                ["Bob", "inactive"],
                ["Charlie", "active"],
            ],
        )

        result = self.connector.delete_rows(
            sandbox_path, column="status", value="active"
        )
        self.assertIn("Deleted 2 row", result)

        content = (self.workspace_root / "test.csv").read_text()
        self.assertNotIn("Alice", content)
        self.assertIn("Bob", content)
        self.assertNotIn("Charlie", content)

    def test_delete_csv_no_match(self):
        """Test deleting rows with no matches."""
        sandbox_path = self._create_csv(
            "test.csv", [["name", "status"], ["Alice", "active"]]
        )

        result = self.connector.delete_rows(
            sandbox_path, column="status", value="deleted"
        )
        self.assertIn("[No rows found", result)

    def test_tab_separated_values(self):
        """Test handling TSV files."""
        tsv_path = self.workspace_root / "test.tsv"
        with open(tsv_path, "w", encoding="utf-8") as f:
            f.write("name\tage\tcity\n")
            f.write("Alice\t30\tNYC\n")
            f.write("Bob\t25\tLA\n")

        sandbox_path = "/workspace/test.tsv"
        result = self.connector.head(sandbox_path, n=10)
        self.assertIn("Alice", result)
        self.assertIn("30", result)

    def test_wide_csv_with_truncation(self):
        """Test CSV with many columns gets truncated."""
        header = [f"col_{i}" for i in range(200)]
        data_row = [f"val_{i}" for i in range(200)]
        sandbox_path = self._create_csv("wide.csv", [header, data_row])

        result = self.connector.head(sandbox_path, n=5)
        self.assertIn("col_0", result)
        self.assertIn("col_1", result)

    def test_inherited_file_operations(self):
        """Test that inherited FileConnector operations work on CSV files."""
        sandbox_path = self._create_csv("test.csv", [["name", "age"], ["Alice", "30"]])

        result = self.connector.find(sandbox_path, "Alice")
        self.assertIn("Alice", result)

        result = self.connector.read(sandbox_path)
        self.assertIn("name", result)
        self.assertIn("Alice", result)


if __name__ == "__main__":
    unittest.main()

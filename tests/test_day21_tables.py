"""
Day 21 Unit Tests — Word Table Engine.
Verifies table creation, 2D matrix population, row insertions/deletions, and safety bounds (max 500x50).
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_office.word.word_errors import (
    WordInvalidRangeError,
    WordInvalidTableError,
    WordNoActiveDocumentError,
    WordTableSizeExceededError,
    WordValidationError,
)
from zye_office.word.word_table_engine import WordTableEngine


class TestDay21Tables(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_adapter = MagicMock()
        self.mock_adapter.worker.run.side_effect = lambda fn: fn()
        self.engine = WordTableEngine(adapter=self.mock_adapter)

    def test_create_table_success(self) -> None:
        """Verify table creation with valid dimensions."""
        mock_doc = MagicMock()
        mock_tables = MagicMock()
        mock_doc.Tables = mock_tables
        mock_tables.Count = 1
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.create_table(rows=3, columns=4, style="PROFESSIONAL_BLUE")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows"], 3)
        self.assertEqual(res["columns"], 4)
        mock_tables.Add.assert_called_once()

    def test_table_dimensions_safety_limits(self) -> None:
        """Verify tables exceeding 500 rows or 50 columns are blocked."""
        with self.assertRaises(WordTableSizeExceededError):
            self.engine.create_table(rows=501, columns=5)

        with self.assertRaises(WordTableSizeExceededError):
            self.engine.create_table(rows=10, columns=51)

    def test_populate_table_matrix(self) -> None:
        """Verify populating table cells with 2D array data."""
        mock_doc = MagicMock()
        mock_table = MagicMock()
        mock_table.Rows.Count = 10
        mock_table.Columns.Count = 10
        mock_cell = MagicMock()
        mock_table.Cell.return_value = mock_cell
        mock_doc.Tables.Count = 1
        mock_doc.Tables.return_value = mock_table
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        data = [
            ["ID", "Name", "Role"],
            ["1", "Alice", "Architect"],
            ["2", "Bob", "Engineer"],
        ]
        res = self.engine.populate_table(table_id=1, data=data)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["cells_written"], 9)

    def test_add_table_row(self) -> None:
        """Verify appending a row to an existing table."""
        mock_doc = MagicMock()
        mock_table = MagicMock()
        mock_table.Rows.Count = 5
        mock_doc.Tables.Count = 1
        mock_doc.Tables.return_value = mock_table
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.add_table_row(table_id=1)
        self.assertEqual(res["status"], "SUCCESS")
        mock_table.Rows.Add.assert_called_once()

    def test_delete_table_row(self) -> None:
        """Verify deleting a row index."""
        mock_doc = MagicMock()
        mock_table = MagicMock()
        mock_table.Rows.Count = 5
        mock_row = MagicMock()
        mock_table.Rows.return_value = mock_row
        mock_doc.Tables.Count = 1
        mock_doc.Tables.return_value = mock_table
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.delete_table_row(table_id=1, row_index=2)
        self.assertEqual(res["status"], "SUCCESS")
        mock_row.Delete.assert_called_once()


if __name__ == "__main__":
    unittest.main()

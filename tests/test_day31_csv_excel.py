"""
Tests for Day 31 CSV and Excel Ingestion, Multi-Sheet, and Read-Only Guarantees.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
import pandas as pd

import computer_intelligence_mcp
from zye_computer_intelligence.data_engine.dataset_loader import DatasetLoader
from zye_computer_intelligence.security.dataset_access import validate_dataset_file


class TestDay31CsvExcel(unittest.TestCase):
    """Verifies CSV and Excel ingestion, sheet selection, and file preservation."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="zye_test_csvexcel_"))
        self.csv_path = self.temp_dir / "sales_data.csv"
        self.excel_path = self.temp_dir / "multisheet_book.xlsx"

        # 1. Create CSV
        self.csv_content = (
            "order_id,customer_name,amount,status\n"
            "ORD-001,Alice,150.0,COMPLETED\n"
            "ORD-002,Bob,250.5,PENDING\n"
            "ORD-003,Charlie,300.0,COMPLETED\n"
            "ORD-004,David,50.0,REFUNDED\n"
        )
        self.csv_path.write_text(self.csv_content, encoding="utf-8")

        # 2. Create Multi-sheet Excel
        with pd.ExcelWriter(self.excel_path, engine="openpyxl") as writer:
            pd.DataFrame({"dept": ["Engineering", "Design"], "budget": [500000, 200000]}).to_excel(
                writer, sheet_name="Q1_Budget", index=False
            )
            pd.DataFrame({"project": ["Zye_AI", "OfficeMaster"], "priority": ["CRITICAL", "HIGH"]}).to_excel(
                writer, sheet_name="Projects", index=False
            )

    def tearDown(self):
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def test_01_csv_ingestion_and_metadata(self):
        """Verifies CSV metadata, size, format, and backend selection."""
        meta = DatasetLoader.load_and_inspect(self.csv_path)
        self.assertEqual(meta["status"], "SUCCESS")
        self.assertEqual(meta["format"], "CSV")
        self.assertEqual(meta["backend"], "DUCKDB")
        self.assertEqual(meta["schema"]["row_count"], 4)
        self.assertIn("amount", meta["schema"]["numeric_columns"])

    def test_02_excel_sheet_inspection_and_selection(self):
        """Verifies multi-sheet Excel inspection and sheet_name selection."""
        meta = DatasetLoader.load_and_inspect(self.excel_path, sheet_name="Projects")
        self.assertEqual(meta["status"], "SUCCESS")
        self.assertEqual(meta["format"], "EXCEL_OPENXML")
        self.assertEqual(meta["backend"], "PANDAS")
        schema = meta["schema"]
        self.assertEqual(schema["sheet_name"], "Projects")
        self.assertIn("Q1_Budget", schema["available_sheets"])
        self.assertIn("project", schema["column_names"])
        self.assertEqual(schema["row_count"], 2)

    def test_03_read_only_guarantee_preserves_disk_files(self):
        """Verifies that dataset analysis leaves files on disk completely unmodified."""
        initial_csv_stat = self.csv_path.stat()
        initial_csv_bytes = self.csv_path.read_bytes()

        # Run inspect, profile, and report tools
        computer_intelligence_mcp.inspect_dataset_schema(str(self.csv_path))
        computer_intelligence_mcp.profile_large_dataset(str(self.csv_path))
        computer_intelligence_mcp.get_dataset_analysis_report(str(self.csv_path))

        after_csv_stat = self.csv_path.stat()
        after_csv_bytes = self.csv_path.read_bytes()

        self.assertEqual(initial_csv_bytes, after_csv_bytes)
        self.assertEqual(initial_csv_stat.st_size, after_csv_stat.st_size)


if __name__ == "__main__":
    unittest.main()

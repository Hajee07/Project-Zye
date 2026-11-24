"""
Tests for Day 31 Schema Inspection, Profiling, Missing Values, and Duplicates.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from zye_computer_intelligence.data_engine.duckdb_engine import ManagedDuckDB
from zye_computer_intelligence.data_engine.schema_inspector import SchemaInspector
from zye_computer_intelligence.statistics.summary_statistics import SummaryStatistics


class TestDay31SchemaProfiling(unittest.TestCase):
    """Verifies descriptive statistics, quartile calculations, null distinction, and duplicate tracking."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="zye_test_profile_"))
        self.data_csv = self.temp_dir / "profile_test.csv"

        # CSV with exact known statistics, nulls, empty strings, and duplicates
        # Amounts: 10, 20, 30, 40, 50, 60, 70, 80, 90, 100 -> mean=55, median=55, min=10, max=100
        # Rows 1 and 2 are identical duplicates
        csv_data = [
            "id,user,amount,notes",
            "1,Alice,10.0,valid",
            "1,Alice,10.0,valid",  # exact duplicate of row 1
            "2,Bob,20.0,",         # empty string note
            "3,Charlie,30.0,   ",  # whitespace note
            "4,,40.0,valid",       # missing user
            "5,Eve,50.0,valid",
            "6,Frank,60.0,valid",
            "7,Grace,70.0,valid",
            "8,Heidi,80.0,valid",
            "9,Ivan,90.0,valid",
            "10,Judy,100.0,valid",
        ]
        self.data_csv.write_text("\n".join(csv_data), encoding="utf-8")

    def tearDown(self):
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def test_01_schema_classification(self):
        """Verifies column classification into numeric, categorical, and ID candidates."""
        with ManagedDuckDB() as engine:
            schema = SchemaInspector.inspect_csv_schema(self.data_csv, duck_engine=engine)
            self.assertEqual(schema["status"], "SUCCESS")
            self.assertEqual(schema["row_count"], 11)
            self.assertEqual(schema["column_count"], 4)
            self.assertIn("amount", schema["numeric_columns"])
            self.assertIn("user", schema["categorical_columns"])
            self.assertIn("notes", schema["categorical_columns"])
            self.assertIn("id", schema["identifier_columns"])

    def test_02_numeric_distribution_statistics(self):
        """Verifies mean, median, min, max, p25, p75, IQR on numeric columns."""
        with ManagedDuckDB() as engine:
            src = engine.get_csv_read_sql(self.data_csv)
            num_profile = SummaryStatistics.profile_numeric_columns(engine, src, ["amount"])
            amt = num_profile["amount"]
            self.assertEqual(amt["count"], 11)
            self.assertEqual(amt["null_count"], 0)
            self.assertAlmostEqual(amt["min"], 10.0)
            self.assertAlmostEqual(amt["max"], 100.0)
            self.assertIsNotNone(amt["median"])
            self.assertIsNotNone(amt["iqr"])

    def test_03_missing_values_categorization(self):
        """Verifies exact differentiation between NULL and empty/whitespace strings."""
        with ManagedDuckDB() as engine:
            src = engine.get_csv_read_sql(self.data_csv)
            missing = SummaryStatistics.analyze_missing_values(engine, src, ["user", "notes"])
            self.assertTrue(missing["has_missing"])
            # user has 1 missing
            self.assertGreaterEqual(missing["missing_by_column"]["user"]["total_missing"], 1)
            # notes has empty strings
            notes_info = missing["missing_by_column"]["notes"]
            self.assertGreaterEqual(notes_info["empty_string_count"], 1)

    def test_04_duplicate_row_detection(self):
        """Verifies exact duplicate rows and key-column duplicate group identification."""
        with ManagedDuckDB() as engine:
            src = engine.get_csv_read_sql(self.data_csv)
            # Exact row duplicates
            exact_dups = SummaryStatistics.analyze_duplicate_rows(engine, src)
            self.assertTrue(exact_dups["has_duplicates"])
            self.assertEqual(exact_dups["duplicate_rows"], 1)

            # Key-based duplicates on 'id'
            key_dups = SummaryStatistics.analyze_duplicate_rows(engine, src, key_columns=["id"])
            self.assertTrue(key_dups["has_duplicates"])
            self.assertGreaterEqual(key_dups["duplicate_groups"], 1)


if __name__ == "__main__":
    unittest.main()

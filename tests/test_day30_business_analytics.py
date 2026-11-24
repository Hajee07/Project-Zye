"""
Day 30 Test Suite: Business Data Analytics Engine
Tests CSV & Excel loading, data profiling, deterministic KPI calculation,
revenue trends, IQR anomaly detection, and data quality inspection.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from zye_personal_assistant.business_analytics import BusinessAnalyticsEngine


class TestDay30BusinessAnalytics(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="zye_test_analytics_"))
        self.engine = BusinessAnalyticsEngine()

        # 1. Create a standard sales CSV file
        self.csv_path = self.tmp_dir / "sales_data.csv"
        csv_content = """date,region,category,revenue,expenses
2026-01-10,North,Software,1500.0,800.0
2026-01-15,South,Hardware,3000.0,1800.0
2026-02-05,North,Software,2200.0,950.0
2026-02-18,East,Services,1800.0,1100.0
2026-03-01,West,Hardware,4500.0,2200.0
2026-03-20,South,Software,2800.0,1200.0
"""
        self.csv_path.write_text(csv_content, encoding="utf-8")

        # 2. Create an Excel workbook with 2 sheets
        self.xlsx_path = self.tmp_dir / "financial_report.xlsx"
        df_sheet1 = pd.DataFrame({
            "product": ["Widget A", "Widget B", "Widget C"],
            "sales": [5000.0, 7500.0, 3200.0],
            "cost": [2500.0, 3500.0, 1500.0],
        })
        df_sheet2 = pd.DataFrame({
            "department": ["R&D", "Marketing", "Operations"],
            "budget": [12000.0, 8000.0, 6000.0],
        })
        with pd.ExcelWriter(self.xlsx_path) as writer:
            df_sheet1.to_excel(writer, sheet_name="Q1_Sales", index=False)
            df_sheet2.to_excel(writer, sheet_name="Budget", index=False)

    def tearDown(self):
        shutil.rmtree(str(self.tmp_dir), ignore_errors=True)

    def test_01_valid_csv_analysis(self):
        """Analyzes CSV, computes deterministic revenue, expenses, net profit, and profit margin."""
        res = self.engine.analyze_dataset(
            file_path=str(self.csv_path),
            business_question="What is the total quarterly profit?",
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["data_quality"]["total_rows"], 6)
        self.assertEqual(res["data_quality"]["total_columns"], 5)

        kpis = res["business_kpis"]
        self.assertEqual(kpis["total_revenue"], 15800.0)
        self.assertEqual(kpis["total_expenses"], 8050.0)
        self.assertEqual(kpis["calculated_net_profit"], 7750.0)
        self.assertEqual(kpis["profit_margin_pct"], 49.1)
        self.assertGreater(len(res["trends"]), 0)
        self.assertIn("sales_data.csv", res["executive_analysis"])

    def test_02_valid_xlsx_analysis_and_sheet_selection(self):
        """Analyzes Excel workbook and allows selecting distinct sheets."""
        # Sheet 1
        res1 = self.engine.analyze_dataset(file_path=str(self.xlsx_path), sheet_name="Q1_Sales")
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertEqual(res1["selected_sheet"], "Q1_Sales")
        self.assertIn("Budget", res1["available_sheets"])
        self.assertEqual(res1["business_kpis"]["total_revenue"], 15700.0)

        # Sheet 2
        res2 = self.engine.analyze_dataset(file_path=str(self.xlsx_path), sheet_name="Budget")
        self.assertEqual(res2["status"], "SUCCESS")
        self.assertEqual(res2["selected_sheet"], "Budget")
        self.assertEqual(res2["data_quality"]["total_rows"], 3)

    def test_03_missing_file_error(self):
        """Non-existent file returns DATA_FILE_NOT_FOUND error."""
        res = self.engine.analyze_dataset(file_path="non_existent_file.csv")
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res.get("error_code"), "DATA_FILE_NOT_FOUND")

    def test_04_unsupported_format_error(self):
        """Unsupported file extensions return DATA_UNSUPPORTED_FORMAT."""
        bad_file = self.tmp_dir / "document.pdf"
        bad_file.write_text("Dummy content", encoding="utf-8")
        res = self.engine.analyze_dataset(file_path=str(bad_file))
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res.get("error_code"), "DATA_UNSUPPORTED_FORMAT")

    def test_05_empty_dataset_error(self):
        """Empty files are safely rejected."""
        empty_file = self.tmp_dir / "empty.csv"
        empty_file.write_text("", encoding="utf-8")
        res = self.engine.analyze_dataset(file_path=str(empty_file))
        self.assertEqual(res["status"], "ERROR")
        self.assertIn(res.get("error_code"), ("DATA_FILE_CORRUPTED", "DATA_SIZE_EXCEEDED"))

    def test_06_anomalies_and_iqr_detection(self):
        """Detects negative revenue and IQR statistical outliers with bounds."""
        anomaly_csv = self.tmp_dir / "anomalies.csv"
        # 10 data points with 1 negative revenue and 1 extreme outlier
        content = """revenue
100.0
105.0
98.0
102.0
110.0
-50.0
99.0
101.0
104.0
5000.0
"""
        anomaly_csv.write_text(content, encoding="utf-8")
        res = self.engine.analyze_dataset(file_path=str(anomaly_csv))
        self.assertEqual(res["status"], "SUCCESS")
        anomalies = res["detected_anomalies"]

        # Check negative revenue flagged
        self.assertTrue(any(a["type"] == "NEGATIVE_REVENUE" for a in anomalies))
        # Check statistical outlier flagged
        self.assertTrue(any(a["type"] == "STATISTICAL_OUTLIER" for a in anomalies))

    def test_07_zero_division_guard(self):
        """Zero revenue handles profit margin without zero division error."""
        zero_csv = self.tmp_dir / "zero_rev.csv"
        zero_csv.write_text("revenue,expense\n0.0,500.0\n0.0,200.0\n", encoding="utf-8")
        res = self.engine.analyze_dataset(file_path=str(zero_csv))
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["business_kpis"]["profit_margin_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()

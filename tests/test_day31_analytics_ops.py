"""
Tests for Day 31 Group Aggregations, Time Trends, Outlier Detection, and Full Reports.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import computer_intelligence_mcp


class TestDay31AnalyticsOps(unittest.TestCase):
    """Verifies group aggregations, trend evaluations, IQR outliers, and markdown formatting."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="zye_test_ops_"))
        self.csv_path = self.temp_dir / "business_ops.csv"

        # Multi-month, multi-category dataset with outliers and negatives
        csv_rows = [
            "date,category,revenue,units",
            "2026-01-10,Software,5000.0,5",
            "2026-01-15,Hardware,3000.0,3",
            "2026-02-10,Software,7000.0,7",
            "2026-02-20,Hardware,4000.0,4",
            "2026-03-05,Software,12000.0,12",
            "2026-03-15,Hardware,6000.0,6",
            "2026-03-25,Services,-500.0,1",    # Negative anomaly
            "2026-03-30,Software,95000.0,50",  # Extreme IQR outlier
        ]
        self.csv_path.write_text("\n".join(csv_rows), encoding="utf-8")

    def tearDown(self):
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def test_01_group_aggregation_tool(self):
        """Verifies aggregate_dataset_by_group calculates category sums and percentages."""
        res = computer_intelligence_mcp.aggregate_dataset_by_group(
            file_path=str(self.csv_path),
            group_by=["category"],
            metric="revenue",
            aggregation="SUM",
            sort_desc=True,
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertGreaterEqual(res["total_groups"], 3)
        # Software has highest revenue
        top = res["segments"][0]
        self.assertEqual(top["category"], "Software")
        self.assertGreater(top["value"], 100000.0)
        self.assertGreater(top["percentage_share"], 80.0)

    def test_02_time_trend_analysis_tool(self):
        """Verifies analyze_dataset_trends calculates monthly trajectories."""
        res = computer_intelligence_mcp.analyze_dataset_trends(
            file_path=str(self.csv_path),
            date_column="date",
            metric="revenue",
            aggregation="SUM",
            interval="MONTH",
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["total_periods"], 3)
        self.assertIn(res["trend_direction"], ("GROWING", "FLUCTUATING", "STABLE"))
        self.assertEqual(len(res["periods"]), 3)

    def test_03_outlier_detection_tool(self):
        """Verifies detect_dataset_outliers detects negative revenue and high IQR outlier."""
        res = computer_intelligence_mcp.detect_dataset_outliers(
            file_path=str(self.csv_path),
            columns=["revenue"],
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["has_anomalies"])
        rev_info = res["anomalies_by_column"]["revenue"]
        self.assertTrue(rev_info["has_negative_values"])
        self.assertEqual(rev_info["negative_count"], 1)
        self.assertGreaterEqual(rev_info["outlier_count"], 1)
        self.assertGreater(rev_info["upper_bound"], 10000.0)

    def test_04_full_report_generation(self):
        """Verifies get_dataset_analysis_report generates markdown tables and bilingual voice outputs."""
        report = computer_intelligence_mcp.get_dataset_analysis_report(str(self.csv_path), include_voice=True)
        self.assertEqual(report["status"], "SUCCESS")
        self.assertIn("markdown", report)
        self.assertIn("voice_tanglish", report)
        self.assertIn("voice_en", report)
        self.assertIn("# ZYE AI — Large Dataset Intelligence Report", report["markdown"])
        self.assertIn("Dataset analysis", report["voice_en"])


if __name__ == "__main__":
    unittest.main()

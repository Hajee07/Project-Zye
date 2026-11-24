"""
Unit tests for Day 14 Business Data Analytics Engine.
Verifies CSV/Excel statistical profiling, KPI calculations, anomaly detection, and dataset preservation.
"""

import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.business_analytics import BusinessAnalyticsEngine


class TestDay14Analytics(unittest.TestCase):
    def setUp(self):
        self.engine = BusinessAnalyticsEngine()
        self.test_dir = tempfile.mkdtemp(prefix="zye_ba_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_csv_loading_and_kpi_calculation(self):
        csv_path = Path(self.test_dir, "sales.csv")
        csv_path.write_text(
            "product,revenue,expenses\n"
            "Software A,10000,4000\n"
            "Software B,20000,8000\n"
            "Service C,5000,2000\n",
            encoding="utf-8",
        )

        res = self.engine.analyze_dataset(str(csv_path))
        self.assertEqual(res["status"], "SUCCESS")
        kpis = res["business_kpis"]
        self.assertEqual(kpis["total_revenue"], 35000.0)
        self.assertEqual(kpis["total_expenses"], 14000.0)
        self.assertEqual(kpis["calculated_net_profit"], 21000.0)
        self.assertEqual(kpis["profit_margin_pct"], 60.0)

    def test_02_anomaly_detection_negative_revenue_and_duplicates(self):
        csv_path = Path(self.test_dir, "anomalous_data.csv")
        csv_path.write_text(
            "tx_id,revenue\n"
            "1,100\n"
            "2,-50\n"  # Negative revenue anomaly
            "1,100\n",  # Duplicate row anomaly
            encoding="utf-8",
        )

        res = self.engine.analyze_dataset(str(csv_path))
        self.assertEqual(res["status"], "SUCCESS")
        anomalies = res.get("detected_anomalies", [])
        types = [a["type"] for a in anomalies]
        self.assertIn("NEGATIVE_REVENUE", types)
        self.assertIn("DUPLICATE_ROWS", types)

    def test_03_source_dataset_preservation(self):
        csv_path = Path(self.test_dir, "immutable.csv")
        original_content = "id,val\n1,10\n2,20\n"
        csv_path.write_text(original_content, encoding="utf-8")

        self.engine.analyze_dataset(str(csv_path))
        self.assertEqual(csv_path.read_text(encoding="utf-8"), original_content, "Source dataset must never be modified")


if __name__ == "__main__":
    unittest.main()

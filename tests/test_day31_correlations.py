"""
Statistical Correlation Engine Tests (Pearson & Spearman) — Mandatory Day 31 Milestone.
Verifies coefficient accuracy, noncausality explanations, rank correlation, and edge cases.
"""

from __future__ import annotations

import math
from pathlib import Path
import tempfile
import unittest
import numpy as np

import computer_intelligence_mcp
from zye_computer_intelligence.data_engine.duckdb_engine import ManagedDuckDB
from zye_computer_intelligence.statistics.correlation_engine import CorrelationEngine


class TestDay31Correlations(unittest.TestCase):
    """Verifies Pearson and Spearman correlation calculation, ranking, and edge cases."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="zye_test_corr_"))
        self.sample_csv = self.temp_dir / "correlation_benchmark.csv"

        # Generate deterministic synthetic data with known statistical properties
        np.random.seed(42)
        n = 500
        x = np.linspace(10, 100, n)
        # 1. Linear relationship with x (r ~ 0.99)
        y_lin = 2.5 * x + np.random.normal(0, 5, n)
        # 2. Perfect inverse with x (r = -1.0)
        y_inv = -3.0 * x + 500.0
        # 3. Monotonic non-linear with x (Spearman rho = 1.0, Pearson r < 1.0)
        y_mono = np.exp(x / 20.0)
        # 4. Constant column
        y_const = np.full(n, 42.0)
        # 5. Independent noise (r ~ 0.0)
        y_noise = np.random.normal(0, 10, n)

        lines = ["x,linear_pos,inverse_perf,monotonic_exp,constant_val,noise_rand"]
        for i in range(n):
            lines.append(f"{x[i]:.4f},{y_lin[i]:.4f},{y_inv[i]:.4f},{y_mono[i]:.4f},{y_const[i]:.4f},{y_noise[i]:.4f}")

        self.sample_csv.write_text("\n".join(lines), encoding="utf-8")

    def tearDown(self):
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def test_01_pearson_perfect_inverse_correlation(self):
        """Verifies perfect inverse linear correlation yields r = -1.000."""
        with ManagedDuckDB() as engine:
            src = engine.get_csv_read_sql(self.sample_csv)
            res = CorrelationEngine.calculate_pairwise_correlation(
                engine, src, "x", "inverse_perf", method="PEARSON"
            )
            self.assertIsNotNone(res["correlation"])
            self.assertAlmostEqual(res["correlation"], -1.0, places=3)
            self.assertEqual(res["interpretation"], "STRONG_NEGATIVE")
            self.assertEqual(res["valid_pairs"], 500)

    def test_02_pearson_strong_positive_correlation(self):
        """Verifies strong linear positive correlation (r > 0.95)."""
        with ManagedDuckDB() as engine:
            src = engine.get_csv_read_sql(self.sample_csv)
            res = CorrelationEngine.calculate_pairwise_correlation(
                engine, src, "x", "linear_pos", method="PEARSON"
            )
            self.assertIsNotNone(res["correlation"])
            self.assertGreater(res["correlation"], 0.95)
            self.assertEqual(res["interpretation"], "STRONG_POSITIVE")

    def test_03_spearman_rank_monotonic_correlation(self):
        """Verifies Spearman rank correlation captures monotonic non-linear relationships (rho = 1.000)."""
        with ManagedDuckDB() as engine:
            src = engine.get_csv_read_sql(self.sample_csv)
            res = CorrelationEngine.calculate_pairwise_correlation(
                engine, src, "x", "monotonic_exp", method="SPEARMAN"
            )
            self.assertIsNotNone(res["correlation"])
            self.assertAlmostEqual(res["correlation"], 1.0, places=2)
            self.assertEqual(res["interpretation"], "STRONG_POSITIVE")

    def test_04_constant_column_zero_variance_defense(self):
        """Verifies constant columns with zero variance do not crash and report warnings."""
        with ManagedDuckDB() as engine:
            src = engine.get_csv_read_sql(self.sample_csv)
            res = CorrelationEngine.calculate_pairwise_correlation(
                engine, src, "x", "constant_val", method="PEARSON"
            )
            self.assertIsNone(res["correlation"])
            self.assertEqual(res["interpretation"], "CONSTANT_COLUMN_ZERO_VARIANCE")
            self.assertTrue(any("zero variance" in w.lower() for w in res["warnings"]))

    def test_05_uncorrelated_noise_variable(self):
        """Verifies uncorrelated noise yields near-zero correlation (|r| < 0.15)."""
        with ManagedDuckDB() as engine:
            src = engine.get_csv_read_sql(self.sample_csv)
            res = CorrelationEngine.calculate_pairwise_correlation(
                engine, src, "x", "noise_rand", method="PEARSON"
            )
            self.assertIsNotNone(res["correlation"])
            self.assertLess(abs(res["correlation"]), 0.15)
            self.assertEqual(res["interpretation"], "NEAR_ZERO")

    def test_06_fastmcp_calculate_dataset_correlations_tool(self):
        """Verifies FastMCP calculate_dataset_correlations tool returns structured ranked matrix with noncausality statement."""
        res = computer_intelligence_mcp.calculate_dataset_correlations(
            str(self.sample_csv), method="PEARSON"
        )
        self.assertEqual(res["status"], "SUCCESS")
        corrs = res["correlations"]
        self.assertIn("ranked_relationships", corrs)
        self.assertGreater(len(corrs["ranked_relationships"]), 0)
        self.assertIn("noncausality_statement", corrs)
        self.assertIn("does not imply causation", corrs["noncausality_statement"])
        self.assertIn("markdown", res)
        self.assertIn("voice_tanglish", res)
        self.assertIn("voice_en", res)
        self.assertIn("causation", res["voice_tanglish"].lower())
        self.assertIn("causation", res["voice_en"].lower())


if __name__ == "__main__":
    unittest.main()

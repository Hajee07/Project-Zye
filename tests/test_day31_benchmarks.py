"""
Large-Scale Real-World Benchmarking Tests (Day 31 Milestone).
Measures execution time and throughput on 10,000 and 100,000 row synthetic datasets,
comparing DuckDB columnar performance against Pandas in-memory baselines.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
import time
import unittest
import numpy as np
import pandas as pd

from zye_computer_intelligence.data_engine.duckdb_engine import ManagedDuckDB
from zye_computer_intelligence.data_engine.schema_inspector import SchemaInspector
from zye_computer_intelligence.statistics.correlation_engine import CorrelationEngine
from zye_computer_intelligence.statistics.segment_analytics import SegmentAnalytics


class TestDay31Benchmarks(unittest.TestCase):
    """Benchmarks DuckDB execution speed and memory efficiency on large synthetic datasets."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="zye_benchmark_"))

        # 1. 10,000 rows dataset
        cls.csv_10k = cls.temp_dir / "bench_10k.csv"
        cls._generate_synthetic_csv(cls.csv_10k, n_rows=10_000)

        # 2. 100,000 rows dataset
        cls.csv_100k = cls.temp_dir / "bench_100k.csv"
        cls._generate_synthetic_csv(cls.csv_100k, n_rows=100_000)

    @classmethod
    def tearDownClass(cls):
        try:
            import shutil
            shutil.rmtree(cls.temp_dir, ignore_errors=True)
        except Exception:
            pass

    @staticmethod
    def _generate_synthetic_csv(path: Path, n_rows: int) -> None:
        """Generates a reproducible synthetic dataset with categories and numeric variables."""
        np.random.seed(42)
        categories = ["Electronics", "Fashion", "Home", "Sports", "Books"]
        cat_choices = np.random.choice(categories, size=n_rows)
        spend = np.random.uniform(10.0, 500.0, size=n_rows)
        revenue = spend * 3.2 + np.random.normal(0, 15.0, size=n_rows)
        units = np.random.randint(1, 25, size=n_rows)

        df = pd.DataFrame({
            "order_id": np.arange(1, n_rows + 1),
            "category": cat_choices,
            "ad_spend": np.round(spend, 2),
            "revenue": np.round(revenue, 2),
            "units": units,
        })
        df.to_csv(path, index=False)

    def test_01_benchmark_10k_schema_and_aggregation(self):
        """Measures 10k rows schema inspection, group-by, and Pearson correlation."""
        with ManagedDuckDB() as engine:
            t0 = time.perf_counter()
            schema = SchemaInspector.inspect_csv_schema(self.csv_10k, duck_engine=engine)
            t_schema = (time.perf_counter() - t0) * 1000

            self.assertEqual(schema["row_count"], 10_000)
            self.assertLess(t_schema, 500.0, "10k schema inspection must complete under 500ms")

            # Group aggregation
            t0 = time.perf_counter()
            src = schema["read_sql"]
            res = SegmentAnalytics.aggregate_by_group(engine, src, ["category"], "revenue")
            t_agg = (time.perf_counter() - t0) * 1000

            self.assertEqual(res["total_groups"], 5)
            self.assertLess(t_agg, 500.0, "10k group-by must complete under 500ms")

            # Pearson correlation
            t0 = time.perf_counter()
            corr = CorrelationEngine.calculate_pairwise_correlation(engine, src, "ad_spend", "revenue")
            t_corr = (time.perf_counter() - t0) * 1000

            self.assertGreater(corr["correlation"], 0.95)
            self.assertLess(t_corr, 500.0, "10k correlation must complete under 500ms")

    def test_02_benchmark_100k_duckdb_vs_pandas_performance(self):
        """Compares 100,000 rows aggregation and correlation: DuckDB vs Pandas."""
        # 1. DuckDB path
        with ManagedDuckDB() as engine:
            t0 = time.perf_counter()
            src = engine.get_csv_read_sql(self.csv_100k)
            corr_duck = CorrelationEngine.calculate_pairwise_correlation(engine, src, "ad_spend", "revenue")
            t_duck_corr = (time.perf_counter() - t0) * 1000

            t0 = time.perf_counter()
            agg_duck = SegmentAnalytics.aggregate_by_group(engine, src, ["category"], "revenue")
            t_duck_agg = (time.perf_counter() - t0) * 1000

        # 2. Pandas baseline path
        t0 = time.perf_counter()
        df_pd = pd.read_csv(self.csv_100k)
        corr_pd = df_pd["ad_spend"].corr(df_pd["revenue"])
        t_pd_corr = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        agg_pd = df_pd.groupby("category")["revenue"].sum()
        t_pd_agg = (time.perf_counter() - t0) * 1000

        # Verifications
        self.assertAlmostEqual(corr_duck["correlation"], corr_pd, places=2)
        self.assertEqual(len(agg_duck["segments"]), len(agg_pd))

        # Output benchmark metrics
        print(f"\n[100,000 Rows Benchmark Results]")
        print(f"  - DuckDB Correlation Time : {t_duck_corr:.2f} ms (r = {corr_duck['correlation']:.4f})")
        print(f"  - Pandas Total Load+Corr  : {t_pd_corr:.2f} ms (r = {corr_pd:.4f})")
        print(f"  - DuckDB Group Agg Time   : {t_duck_agg:.2f} ms ({agg_duck['total_groups']} groups)")
        print(f"  - Pandas Group Agg Time   : {t_pd_agg:.2f} ms")


if __name__ == "__main__":
    unittest.main()

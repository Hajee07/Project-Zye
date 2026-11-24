"""
Performance Benchmark Suite for Day 35 Real-Time Tactical Telemetry Engine.
Measures high-resolution ingestion and analytical computation latency across
100, 1,000, and 5,000 sample windows using time.perf_counter_ns().
Reports p50, p95, p99, average, and maximum observed computation latencies.
"""

import time
import unittest
import numpy as np

from zye_realtime_tactical.telemetry.telemetry_analyzer import TelemetryAnalyzer
from zye_realtime_tactical.telemetry.telemetry_buffer_manager import TelemetryBufferManager


class TestDay35Performance(unittest.TestCase):
    """Benchmarks processing latency and memory throughput."""

    def setUp(self):
        TelemetryBufferManager.reset_instance()
        self.analyzer = TelemetryAnalyzer()

        # Warm up NumPy JIT / internal BLAS caches
        _ = np.mean(np.arange(100, dtype=np.float64))
        _ = np.std(np.arange(100, dtype=np.float64))

    def tearDown(self):
        TelemetryBufferManager.reset_instance()

    def test_single_sample_latency_percentiles(self):
        """Benchmarks 500 sequential single-reading updates measuring p50, p95, p99."""
        stream_name = "perf_single"
        latencies_ms = []

        # Run 500 sequential single-point updates
        for i in range(500):
            t_start = time.perf_counter_ns()
            res = self.analyzer.analyze_realtime_stream(
                stream_name=stream_name,
                new_readings=[float(50.0 + (i % 20))],
                timestamps=[float(i * 0.1)],
            )
            elapsed_ms = (time.perf_counter_ns() - t_start) / 1_000_000.0
            latencies_ms.append(elapsed_ms)
            self.assertEqual(res.status, "SUCCESS")

        p50 = float(np.percentile(latencies_ms, 50))
        p95 = float(np.percentile(latencies_ms, 95))
        p99 = float(np.percentile(latencies_ms, 99))
        avg = float(np.mean(latencies_ms))
        max_lat = float(np.max(latencies_ms))

        print(f"\n[Day 35 Benchmark: Single Sample Ingestion]")
        print(f"  Trials: 500")
        print(f"  p50 Latency: {p50:.4f} ms")
        print(f"  p95 Latency: {p95:.4f} ms")
        print(f"  p99 Latency: {p99:.4f} ms")
        print(f"  Avg Latency: {avg:.4f} ms")
        print(f"  Max Latency: {max_lat:.4f} ms")

        # In-memory single-point analysis must execute sub-5ms on standard hardware
        self.assertLess(p50, 5.0)

    def test_batch_5000_samples_rollover(self):
        """Benchmarks ingestion of 5,000 samples and ring buffer rollover."""
        stream_name = "perf_5000"
        batch_size = 500

        times = []
        for b in range(12):  # 12 * 500 = 6,000 samples (triggers 1,000 rollovers)
            readings = [float(10.0 + (i % 50)) for i in range(batch_size)]
            ts = [float((b * batch_size + i) * 0.01) for i in range(batch_size)]

            t0 = time.perf_counter_ns()
            res = self.analyzer.analyze_realtime_stream(
                stream_name=stream_name,
                new_readings=readings,
                timestamps=ts,
            )
            elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
            times.append(elapsed_ms)
            self.assertEqual(res.status, "SUCCESS")

        status = self.analyzer.stream_manager.get_stream_status(stream_name)
        self.assertEqual(status.current_sample_count, 5000)
        self.assertEqual(status.overwritten_samples, 1000)

        print(f"\n[Day 35 Benchmark: 5,000 Sample Capacity Rollover]")
        print(f"  Total Ingested: 6,000 | In-Memory Retained: 5,000 | Overwritten: 1,000")
        print(f"  Mean Batch Compute Latency: {np.mean(times):.4f} ms")
        self.assertLess(np.mean(times), 25.0)


if __name__ == "__main__":
    unittest.main()

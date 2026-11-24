"""
Comprehensive Unit Tests for Day 35 Real-Time Tactical Telemetry Engine.
Verifies In-Memory Ring Buffer, Input Validation, Timestamp Management,
Rolling Statistics, Kinematics (Velocity/Acceleration), Z-Score Anomaly Detection,
Multi-Stream Isolation, and FastMCP Tool Execution.
"""

import math
import threading
import time
import unittest
import numpy as np

import realtime_tactical_mcp as rtm
from zye_realtime_tactical.security.telemetry_access_policy import (
    TelemetryAccessPolicy,
    TelemetrySecurityError,
)
from zye_realtime_tactical.security.telemetry_input_security import TelemetryInputSecurity
from zye_realtime_tactical.security.telemetry_resource_policy import TelemetryResourcePolicy
from zye_realtime_tactical.telemetry.acceleration_calculator import AccelerationCalculator
from zye_realtime_tactical.telemetry.anomaly_detector import AnomalyDetector
from zye_realtime_tactical.telemetry.ring_buffer import RingBuffer
from zye_realtime_tactical.telemetry.rolling_statistics import RollingStatistics
from zye_realtime_tactical.telemetry.sliding_window import SlidingWindow
from zye_realtime_tactical.telemetry.telemetry_analyzer import TelemetryAnalyzer
from zye_realtime_tactical.telemetry.telemetry_buffer_manager import TelemetryBufferManager
from zye_realtime_tactical.telemetry.telemetry_models import (
    StreamConfig,
    StreamStatus,
    TimestampSource,
)
from zye_realtime_tactical.telemetry.telemetry_result_schema import AnomalyStatus
from zye_realtime_tactical.telemetry.telemetry_stream_manager import TelemetryStreamManager
from zye_realtime_tactical.telemetry.timestamp_manager import TimestampManager
from zye_realtime_tactical.telemetry.velocity_calculator import VelocityCalculator


class TestDay35Telemetry(unittest.TestCase):
    """Test suite covering the complete Day 35 telemetry analytics engine."""

    def setUp(self):
        TelemetryBufferManager.reset_instance()
        self.manager = TelemetryBufferManager.get_instance()
        self.analyzer = TelemetryAnalyzer(buffer_manager=self.manager)

    def tearDown(self):
        TelemetryBufferManager.reset_instance()

    # -----------------------------------------------------------------------
    # 1. Ring Buffer & Rollover Mechanics
    # -----------------------------------------------------------------------
    def test_ring_buffer_basic_operations(self):
        """Verifies ring buffer appends, capacities, and snapshots."""
        cfg = StreamConfig(stream_name="test_basic", capacity=5)
        buf = RingBuffer(cfg)

        self.assertEqual(len(buf), 0)
        buf.append(10.0, 1.0, TimestampSource.CALLER_PROVIDED)
        self.assertEqual(len(buf), 1)
        self.assertEqual(buf.total_samples_ingested, 1)
        self.assertEqual(buf.overwritten_samples, 0)

        # Batch append
        buf.extend([20.0, 30.0], [2.0, 3.0], TimestampSource.CALLER_PROVIDED)
        self.assertEqual(len(buf), 3)
        self.assertEqual(buf.total_samples_ingested, 3)

        # Verify snapshot
        snapshot = buf.get_snapshot()
        self.assertEqual(len(snapshot), 3)
        self.assertEqual([s.value for s in snapshot], [10.0, 20.0, 30.0])

    def test_ring_buffer_rollover_overwrites_oldest(self):
        """Verifies ring buffer discards oldest samples when capacity is reached."""
        cfg = StreamConfig(stream_name="test_rollover", capacity=3)
        buf = RingBuffer(cfg)

        # Add 5 samples to a 3-capacity buffer
        for i in range(1, 6):
            buf.append(float(i * 10), float(i), TimestampSource.CALLER_PROVIDED)

        self.assertEqual(len(buf), 3)
        self.assertEqual(buf.total_samples_ingested, 5)
        self.assertEqual(buf.overwritten_samples, 2)

        # Values should be latest 3: [30.0, 40.0, 50.0]
        vals = [s.value for s in buf.get_snapshot()]
        self.assertEqual(vals, [30.0, 40.0, 50.0])

    def test_ring_buffer_reset(self):
        """Verifies clean reset of samples and counters."""
        cfg = StreamConfig(stream_name="test_reset", capacity=5)
        buf = RingBuffer(cfg)
        buf.extend([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], TimestampSource.CALLER_PROVIDED)
        self.assertEqual(len(buf), 3)

        buf.clear()
        self.assertEqual(len(buf), 0)
        self.assertEqual(buf.total_samples_ingested, 0)
        self.assertEqual(buf.overwritten_samples, 0)
        self.assertIsNone(buf.last_sample_timestamp)

    # -----------------------------------------------------------------------
    # 2. Input Validation & Security Rules
    # -----------------------------------------------------------------------
    def test_input_validation_rejections(self):
        """Verifies rejection of invalid data types, NaNs, infinities, booleans, and oversized batches."""
        # Booleans
        valid, msg = TelemetryInputSecurity.validate_numeric_reading(True)
        self.assertFalse(valid)
        self.assertIn("Boolean", msg)

        # NaN
        valid, msg = TelemetryInputSecurity.validate_numeric_reading(float("nan"))
        self.assertFalse(valid)
        self.assertIn("NaN", msg)

        # Inf
        valid, msg = TelemetryInputSecurity.validate_numeric_reading(float("inf"))
        self.assertFalse(valid)
        self.assertIn("Infinite", msg)

        # Empty batch
        valid, msg = TelemetryInputSecurity.validate_readings_batch([])
        self.assertFalse(valid)

        # Oversized batch
        oversized = [1.0] * (TelemetryResourcePolicy.MAX_BATCH_SIZE + 1)
        valid, msg = TelemetryInputSecurity.validate_readings_batch(oversized)
        self.assertFalse(valid)
        self.assertIn("exceeds maximum", msg)

        # Invalid stream names
        self.assertFalse(TelemetryAccessPolicy.validate_stream_name("")[0])
        self.assertFalse(TelemetryAccessPolicy.validate_stream_name("bad name with spaces")[0])
        self.assertFalse(TelemetryAccessPolicy.validate_stream_name("a" * 65)[0])
        self.assertTrue(TelemetryAccessPolicy.validate_stream_name("cpu_sensor.01-core")[0])

    # -----------------------------------------------------------------------
    # 3. Timestamp Management
    # -----------------------------------------------------------------------
    def test_timestamp_monotonicity_and_duplicates(self):
        """Verifies detection of non-monotonic or duplicate timestamps."""
        # Duplicate timestamp
        valid, msg, _, _ = TimestampManager.validate_and_align_timestamps(
            readings_count=2, timestamps=[10.0, 10.0]
        )
        self.assertFalse(valid)
        self.assertIn("Duplicate timestamp", msg)

        # Out of order timestamp
        valid, msg, _, _ = TimestampManager.validate_and_align_timestamps(
            readings_count=2, timestamps=[15.0, 12.0]
        )
        self.assertFalse(valid)
        self.assertIn("Out-of-order", msg)

        # Monotonic generation when timestamps omitted
        valid, msg, times, src = TimestampManager.validate_and_align_timestamps(
            readings_count=3, timestamps=None
        )
        self.assertTrue(valid)
        self.assertEqual(len(times), 3)
        self.assertTrue(times[0] < times[1] < times[2])
        self.assertEqual(src, TimestampSource.LOCALLY_GENERATED_MONOTONIC)

    # -----------------------------------------------------------------------
    # 4. Rolling Statistics
    # -----------------------------------------------------------------------
    def test_rolling_statistics_calculations(self):
        """Verifies NumPy float64 rolling statistics correctness."""
        arr = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float64)
        stats = RollingStatistics.calculate_window_statistics(arr)

        self.assertEqual(stats["sample_count"], 4)
        self.assertEqual(stats["current_value"], 40.0)
        self.assertEqual(stats["rolling_mean"], 25.0)
        self.assertEqual(stats["min_value"], 10.0)
        self.assertEqual(stats["max_value"], 40.0)
        self.assertAlmostEqual(stats["std_dev"], np.std(arr), places=4)

        # Empty array
        empty_stats = RollingStatistics.calculate_window_statistics(np.empty(0))
        self.assertEqual(empty_stats["sample_count"], 0)
        self.assertIsNone(empty_stats["rolling_mean"])

    # -----------------------------------------------------------------------
    # 5. Kinematics: Velocity and Acceleration
    # -----------------------------------------------------------------------
    def test_velocity_calculator(self):
        """Verifies instantaneous velocity dx/dt in units/sec."""
        vals = np.array([20.0, 30.0], dtype=np.float64)
        times = np.array([10.0, 12.0], dtype=np.float64)  # dt = 2s, dx = 10 -> v = 5.0
        v = VelocityCalculator.calculate_instantaneous_velocity(vals, times)
        self.assertEqual(v, 5.0)

        # Decreasing values (negative velocity)
        vals_neg = np.array([30.0, 10.0], dtype=np.float64)
        v_neg = VelocityCalculator.calculate_instantaneous_velocity(vals_neg, times)
        self.assertEqual(v_neg, -10.0)

        # Insufficient samples (< 2)
        self.assertIsNone(VelocityCalculator.calculate_instantaneous_velocity(np.array([10.0]), np.array([1.0])))

    def test_acceleration_calculator(self):
        """Verifies instantaneous acceleration dv/dt in units/sec^2."""
        # t: [0, 1, 2], values: [10, 20, 35]
        # v1 = (20-10)/1 = 10; v2 = (35-20)/1 = 15; a = (15-10)/1 = 5.0
        vals = np.array([10.0, 20.0, 35.0], dtype=np.float64)
        times = np.array([0.0, 1.0, 2.0], dtype=np.float64)
        a = AccelerationCalculator.calculate_instantaneous_acceleration(vals, times)
        self.assertEqual(a, 5.0)

        # Insufficient samples (< 3)
        self.assertIsNone(AccelerationCalculator.calculate_instantaneous_acceleration(vals[:2], times[:2]))

    # -----------------------------------------------------------------------
    # 6. Z-Score Anomaly Detection
    # -----------------------------------------------------------------------
    def test_z_score_anomaly_detection(self):
        """Verifies outlier detection, baseline exclusion, and zero variance handling."""
        # Insufficient baseline (< 10)
        small_arr = np.array([10.0, 11.0, 12.0], dtype=np.float64)
        res_small = AnomalyDetector.evaluate_measurement_anomaly(small_arr, threshold=2.5)
        self.assertEqual(res_small["anomaly_status"], AnomalyStatus.INSUFFICIENT_BASELINE)
        self.assertFalse(res_small["is_anomaly"])

        # 10 baseline samples around 20.0 followed by extreme outlier 120.0
        baseline = [20.0, 21.0, 19.5, 20.5, 20.0, 21.5, 19.0, 20.2, 20.8, 19.8]
        outlier_data = np.array(baseline + [120.0], dtype=np.float64)
        res_outlier = AnomalyDetector.evaluate_measurement_anomaly(outlier_data, threshold=2.5)

        self.assertTrue(res_outlier["is_anomaly"])
        self.assertEqual(res_outlier["anomaly_status"], AnomalyStatus.ANOMALY_DETECTED)
        self.assertGreater(res_outlier["z_score"], 2.5)
        self.assertEqual(res_outlier["baseline_sample_count"], 10)

        # Zero variance baseline: 12 constant samples
        const_data = np.array([25.0] * 12, dtype=np.float64)
        res_zero = AnomalyDetector.evaluate_measurement_anomaly(const_data, threshold=2.5)
        self.assertEqual(res_zero["anomaly_status"], AnomalyStatus.ZERO_VARIANCE_BASELINE)
        self.assertFalse(res_zero["is_anomaly"])
        self.assertIsNone(res_zero["z_score"])

    # -----------------------------------------------------------------------
    # 7. Multi-Stream Isolation
    # -----------------------------------------------------------------------
    def test_multi_stream_isolation(self):
        """Verifies multiple streams operate completely independently without contamination."""
        res_cpu = self.analyzer.analyze_realtime_stream(
            stream_name="cpu_stream",
            new_readings=[50.0, 55.0, 60.0],
            timestamps=[1.0, 2.0, 3.0],
        )
        res_mem = self.analyzer.analyze_realtime_stream(
            stream_name="mem_stream",
            new_readings=[1000.0, 1050.0],
            timestamps=[1.0, 2.0],
        )

        self.assertEqual(res_cpu.stream, "cpu_stream")
        self.assertEqual(res_cpu.sample_count, 3)
        self.assertEqual(res_cpu.current_value, 60.0)

        self.assertEqual(res_mem.stream, "mem_stream")
        self.assertEqual(res_mem.sample_count, 2)
        self.assertEqual(res_mem.current_value, 1050.0)

        # Reset cpu_stream should not affect mem_stream
        self.assertTrue(self.manager.stream_manager.reset_stream("cpu_stream"))
        status_cpu = self.manager.stream_manager.get_stream_status("cpu_stream")
        status_mem = self.manager.stream_manager.get_stream_status("mem_stream")

        self.assertEqual(status_cpu.current_sample_count, 0)
        self.assertEqual(status_mem.current_sample_count, 2)

    # -----------------------------------------------------------------------
    # 8. Thread Concurrency
    # -----------------------------------------------------------------------
    def test_concurrent_stream_writes(self):
        """Verifies thread-safe ingestion into multiple streams simultaneously."""
        def _worker(stream_name: str, start_val: float):
            for i in range(10):
                self.analyzer.analyze_realtime_stream(
                    stream_name=stream_name,
                    new_readings=[start_val + i],
                )

        threads = [
            threading.Thread(target=_worker, args=("concurrent_a", 10.0)),
            threading.Thread(target=_worker, args=("concurrent_b", 100.0)),
            threading.Thread(target=_worker, args=("concurrent_c", 1000.0)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        status_a = self.manager.stream_manager.get_stream_status("concurrent_a")
        status_b = self.manager.stream_manager.get_stream_status("concurrent_b")
        status_c = self.manager.stream_manager.get_stream_status("concurrent_c")

        self.assertEqual(status_a.total_samples_ingested, 10)
        self.assertEqual(status_b.total_samples_ingested, 10)
        self.assertEqual(status_c.total_samples_ingested, 10)

    # -----------------------------------------------------------------------
    # 9. FastMCP Tools Execution
    # -----------------------------------------------------------------------
    def test_fastmcp_tools_execution(self):
        """Verifies invocation of Tools 01 through 05 via realtime_tactical_mcp."""
        # Tool 01: analyze_realtime_stream
        res1 = rtm.analyze_realtime_stream(
            stream_name="mcp_stream",
            new_readings=[10.0, 15.0, 22.0],
            timestamps=[10.0, 11.0, 12.0],
        )
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertEqual(res1["current_value"], 22.0)
        self.assertEqual(res1["rate_of_change_per_sec"], 7.0)

        # Tool 02: get_telemetry_stream_status
        res2 = rtm.get_telemetry_stream_status("mcp_stream")
        self.assertEqual(res2["status"], "SUCCESS")
        self.assertEqual(res2["stream_status"]["current_sample_count"], 3)

        # Tool 03: list_telemetry_streams
        res3 = rtm.list_telemetry_streams()
        self.assertEqual(res3["status"], "SUCCESS")
        self.assertGreaterEqual(res3["active_stream_count"], 1)

        # Tool 04: reset_telemetry_stream
        res4 = rtm.reset_telemetry_stream("mcp_stream")
        self.assertEqual(res4["status"], "SUCCESS")

        # Tool 05: get_telemetry_performance_metrics
        res5 = rtm.get_telemetry_performance_metrics()
        self.assertEqual(res5["status"], "SUCCESS")
        self.assertIn("average_compute_time_ms", res5["metrics"])


if __name__ == "__main__":
    unittest.main()

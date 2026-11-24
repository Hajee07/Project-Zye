"""
Real-Time Telemetry Analyzer Facade.
Primary entry point for continuous data ingestion, sliding window analytics,
rate-of-change computation, and Z-score anomaly detection.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from zye_realtime_tactical.security.telemetry_access_policy import TelemetrySecurityError
from zye_realtime_tactical.security.telemetry_resource_policy import TelemetryResourcePolicy
from zye_realtime_tactical.telemetry.acceleration_calculator import AccelerationCalculator
from zye_realtime_tactical.telemetry.anomaly_detector import AnomalyDetector
from zye_realtime_tactical.telemetry.ring_buffer import RingBuffer
from zye_realtime_tactical.telemetry.rolling_statistics import RollingStatistics
from zye_realtime_tactical.telemetry.sliding_window import SlidingWindow
from zye_realtime_tactical.telemetry.telemetry_buffer_manager import TelemetryBufferManager
from zye_realtime_tactical.telemetry.telemetry_result_schema import (
    AnomalyStatus,
    TelemetryAnalysisResult,
)
from zye_realtime_tactical.telemetry.telemetry_validator import TelemetryValidator
from zye_realtime_tactical.telemetry.velocity_calculator import VelocityCalculator

logger = logging.getLogger("zye.realtime_tactical.analyzer")


class TelemetryAnalyzer:
    """Coordinates atomic telemetry ingestion and real-time numerical computation."""

    def __init__(self, buffer_manager: Optional[TelemetryBufferManager] = None) -> None:
        self.buffer_manager = buffer_manager or TelemetryBufferManager.get_instance()
        self.stream_manager = self.buffer_manager.stream_manager

    def analyze_realtime_stream(
        self,
        stream_name: str,
        new_readings: List[Any],
        timestamps: Optional[List[float]] = None,
        window_size: Optional[int] = None,
        anomaly_threshold: Optional[float] = None,
        buffer_capacity: Optional[int] = None,
    ) -> TelemetryAnalysisResult:
        """
        Ingests a batch of new readings into the stream's ring buffer and computes
        instantaneous statistics, velocity, acceleration, and anomaly status.
        """
        start_ns = time.perf_counter_ns()
        thresh = anomaly_threshold or TelemetryResourcePolicy.DEFAULT_ANOMALY_THRESHOLD
        cap = buffer_capacity or TelemetryResourcePolicy.DEFAULT_BUFFER_CAPACITY

        try:
            # 1. Resolve or create stream under stream lock
            stream = self.stream_manager.get_or_create_stream(
                stream_name=stream_name,
                capacity=cap,
                anomaly_threshold=thresh,
            )

            lock = self.stream_manager.lock_manager.get_stream_lock(stream_name)
            with lock:
                # 2. Atomic input and timestamp validation
                last_time = stream.last_sample_timestamp
                expected_src = stream.timestamp_source

                is_valid, err_msg, valid_readings, valid_times, time_src = (
                    TelemetryValidator.validate_ingestion_request(
                        stream_name=stream_name,
                        readings=new_readings,
                        timestamps=timestamps,
                        last_stream_timestamp=last_time,
                        expected_timestamp_source=expected_src,
                    )
                )

                if not is_valid:
                    self.buffer_manager.record_analysis_metrics(
                        time.perf_counter_ns() - start_ns, is_error=True
                    )
                    return TelemetryAnalysisResult(
                        status="ERROR",
                        stream=stream_name,
                        sample_count=len(stream),
                        total_samples_ingested=stream.total_samples_ingested,
                        overwritten_samples=stream.overwritten_samples,
                        error_message=err_msg,
                        timestamp_source=str(time_src.value if hasattr(time_src, "value") else time_src),
                    )

                # 3. Ingest validated samples into ring buffer
                stream.extend(valid_readings, valid_times, time_src)

                # 4. Extract contiguous numerical window snapshot
                all_samples = stream.get_snapshot()
                values_arr, times_arr = SlidingWindow.extract_arrays(all_samples, window_size=window_size)

                # 5. Calculate rolling descriptive statistics
                stats = RollingStatistics.calculate_window_statistics(values_arr)

                # 6. Calculate instantaneous velocity (units/sec)
                velocity = VelocityCalculator.calculate_instantaneous_velocity(values_arr, times_arr)

                # 7. Calculate instantaneous acceleration (units/sec^2)
                acceleration = AccelerationCalculator.calculate_instantaneous_acceleration(values_arr, times_arr)

                # 8. Evaluate statistical Z-score anomaly against baseline
                anomaly_eval = AnomalyDetector.evaluate_measurement_anomaly(
                    values=values_arr,
                    threshold=thresh,
                    min_baseline_samples=TelemetryResourcePolicy.MIN_ANOMALY_BASELINE_SAMPLES,
                )

                # 9. Measure compute latency
                compute_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
                self.buffer_manager.record_analysis_metrics(time.perf_counter_ns() - start_ns, is_error=False)

                return TelemetryAnalysisResult(
                    status="SUCCESS",
                    stream=stream_name,
                    sample_count=stats["sample_count"] or 0,
                    total_samples_ingested=stream.total_samples_ingested,
                    overwritten_samples=stream.overwritten_samples,
                    current_value=stats["current_value"],
                    rolling_mean=stats["rolling_mean"],
                    std_dev=stats["std_dev"],
                    min_value=stats["min_value"],
                    max_value=stats["max_value"],
                    rate_of_change_per_sec=velocity,
                    acceleration_per_sec2=acceleration,
                    anomaly_z_score=anomaly_eval["z_score"],
                    is_anomaly=anomaly_eval["is_anomaly"],
                    anomaly_status=anomaly_eval["anomaly_status"],
                    anomaly_threshold=anomaly_eval["threshold"],
                    baseline_sample_count=anomaly_eval["baseline_sample_count"],
                    baseline_mean=anomaly_eval["baseline_mean"],
                    baseline_std_dev=anomaly_eval["baseline_std_dev"],
                    timestamp_source=time_src.value,
                    compute_time_ms=round(compute_ms, 3),
                )

        except TelemetrySecurityError as sec_err:
            self.buffer_manager.record_analysis_metrics(time.perf_counter_ns() - start_ns, is_error=True)
            return TelemetryAnalysisResult(
                status="ERROR",
                stream=stream_name,
                sample_count=0,
                total_samples_ingested=0,
                overwritten_samples=0,
                error_message=str(sec_err),
            )
        except Exception as exc:
            logger.error("Unhandled telemetry analysis error on stream '%s': %s", stream_name, exc, exc_info=True)
            self.buffer_manager.record_analysis_metrics(time.perf_counter_ns() - start_ns, is_error=True)
            return TelemetryAnalysisResult(
                status="ERROR",
                stream=stream_name,
                sample_count=0,
                total_samples_ingested=0,
                overwritten_samples=0,
                error_message=f"Internal telemetry processing error: {exc}",
            )

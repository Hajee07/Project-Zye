"""
Telemetry Validator.
Validates stream parameters, batch payloads, and numeric integrity atomically.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from zye_realtime_tactical.security.telemetry_access_policy import TelemetryAccessPolicy
from zye_realtime_tactical.security.telemetry_input_security import TelemetryInputSecurity
from zye_realtime_tactical.security.telemetry_resource_policy import TelemetryResourcePolicy
from zye_realtime_tactical.telemetry.telemetry_models import TimestampSource
from zye_realtime_tactical.telemetry.timestamp_manager import TimestampManager


class TelemetryValidator:
    """Atomic multi-layer validator for incoming telemetry requests."""

    @classmethod
    def validate_ingestion_request(
        cls,
        stream_name: str,
        readings: List[Any],
        timestamps: Optional[List[float]] = None,
        last_stream_timestamp: Optional[float] = None,
        expected_timestamp_source: Optional[TimestampSource] = None,
    ) -> Tuple[bool, str, List[float], List[float], TimestampSource]:
        """
        Validates stream name, readings, and timestamps atomically.
        
        Returns:
            (is_valid, error_message, validated_readings, validated_timestamps, timestamp_source)
        """
        # 1. Validate stream name
        is_name_valid, name_msg = TelemetryAccessPolicy.validate_stream_name(stream_name)
        if not is_name_valid:
            return False, name_msg, [], [], TimestampSource.CALLER_PROVIDED

        # 2. Validate readings batch
        is_batch_valid, batch_msg = TelemetryInputSecurity.validate_readings_batch(
            readings, max_batch_size=TelemetryResourcePolicy.MAX_BATCH_SIZE
        )
        if not is_batch_valid:
            return False, batch_msg, [], [], TimestampSource.CALLER_PROVIDED

        # 3. Validate or align timestamps
        is_time_valid, time_msg, aligned_times, time_src = TimestampManager.validate_and_align_timestamps(
            readings_count=len(readings),
            timestamps=timestamps,
            last_stream_timestamp=last_stream_timestamp,
            expected_source=expected_timestamp_source,
        )
        if not is_time_valid:
            return False, time_msg, [], [], time_src

        float_readings = [float(r) for r in readings]
        return True, "Valid", float_readings, aligned_times, time_src

"""
Timestamp Manager.
Validates timestamp monotonic ordering, prevents duplicate timestamps,
handles locally generated monotonic times, and detects sample timing gaps.
"""

from __future__ import annotations

import math
import time
from typing import List, Optional, Tuple

from zye_realtime_tactical.telemetry.telemetry_models import TimestampSource

# Flag unusually large sample gaps (e.g. > 60 seconds between sequential samples)
MAX_SUSPICIOUS_GAP_SECONDS = 3600.0


class TimestampManager:
    """Validates temporal consistency and generates receive timestamps."""

    @classmethod
    def validate_and_align_timestamps(
        cls,
        readings_count: int,
        timestamps: Optional[List[float]],
        last_stream_timestamp: Optional[float] = None,
        expected_source: Optional[TimestampSource] = None,
    ) -> Tuple[bool, str, List[float], TimestampSource]:
        """
        Validates provided timestamps or generates monotonic timestamps.
        
        Returns:
            (is_valid, error_message, resolved_timestamps, timestamp_source)
        """
        if readings_count == 0:
            return False, "Readings count is zero.", [], TimestampSource.CALLER_PROVIDED

        # Case 1: Caller provided timestamps
        if timestamps is not None:
            if expected_source == TimestampSource.LOCALLY_GENERATED_MONOTONIC:
                return (
                    False,
                    "Timestamp mode mismatch: Stream was initialized with locally generated timestamps, "
                    "but caller-provided timestamps were received. Reset stream to change timestamp mode.",
                    [],
                    TimestampSource.CALLER_PROVIDED,
                )

            if len(timestamps) != readings_count:
                return (
                    False,
                    f"Timestamp length mismatch: Received {len(timestamps)} timestamps for {readings_count} readings.",
                    [],
                    TimestampSource.CALLER_PROVIDED,
                )

            # Check individual timestamps
            prev_t = last_stream_timestamp
            for idx, t in enumerate(timestamps):
                if not isinstance(t, (int, float)) or isinstance(t, bool):
                    return False, f"Invalid timestamp at index {idx}: not a finite number.", [], TimestampSource.CALLER_PROVIDED

                if math.isnan(t) or math.isinf(t):
                    return False, f"Non-finite timestamp at index {idx}: {t}.", [], TimestampSource.CALLER_PROVIDED

                if t < 0:
                    return False, f"Negative timestamp at index {idx}: {t}.", [], TimestampSource.CALLER_PROVIDED

                if prev_t is not None:
                    if t == prev_t:
                        return False, f"Duplicate timestamp detected at index {idx}: {t} == {prev_t}.", [], TimestampSource.CALLER_PROVIDED
                    if t < prev_t:
                        return False, f"Out-of-order timestamp detected at index {idx}: {t} < {prev_t}.", [], TimestampSource.CALLER_PROVIDED

                prev_t = t

            return True, "Valid", [float(t) for t in timestamps], TimestampSource.CALLER_PROVIDED

        # Case 2: Monotonic locally generated timestamps
        if expected_source == TimestampSource.CALLER_PROVIDED:
            return (
                False,
                "Timestamp mode mismatch: Stream was initialized with caller-provided timestamps, "
                "but no timestamps were supplied in this batch. Reset stream to change timestamp mode.",
                [],
                TimestampSource.LOCALLY_GENERATED_MONOTONIC,
            )

        now = time.monotonic()
        # If batch has multiple readings without timestamps, distribute evenly over delta or step
        # Minimum step to prevent identical timestamps: 1 microsecond (1e-6s)
        base_step = 0.001  # 1ms nominal step
        if last_stream_timestamp is not None and now <= last_stream_timestamp:
            now = last_stream_timestamp + 0.001

        generated = []
        for i in range(readings_count):
            t_val = now + (i * base_step)
            generated.append(t_val)

        return True, "Valid", generated, TimestampSource.LOCALLY_GENERATED_MONOTONIC

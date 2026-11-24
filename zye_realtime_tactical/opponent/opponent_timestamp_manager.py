"""
Opponent Timestamp Manager.
Validates monotonic action timing or generates monotonic timestamps for interval calculations.
"""

from __future__ import annotations

import math
import time
from typing import List, Optional, Tuple

from zye_realtime_tactical.telemetry.telemetry_models import TimestampSource


class OpponentTimestampManager:
    """Validates action event timestamps and maintains temporal ordering."""

    @classmethod
    def validate_timestamps(
        cls,
        raw_timestamps: Optional[List[float]],
        expected_count: int,
        last_known_timestamp: Optional[float] = None,
    ) -> List[float]:
        """Convenience method that validates or generates monotonic timestamps, raising ValueError on error."""
        valid, err, resolved, _ = cls.validate_and_align_timestamps(
            action_count=expected_count,
            timestamps=raw_timestamps,
            last_action_timestamp=last_known_timestamp,
        )
        if not valid:
            raise ValueError(err)
        return resolved

    @classmethod
    def validate_and_align_timestamps(
        cls,
        action_count: int,
        timestamps: Optional[List[float]],
        last_action_timestamp: Optional[float] = None,
        expected_source: Optional[TimestampSource] = None,
    ) -> Tuple[bool, str, List[float], TimestampSource]:
        """
        Validates provided timestamps or creates monotonic sequence timestamps.
        
        Returns:
            (is_valid, error_message, resolved_timestamps, timestamp_source)
        """
        if action_count == 0:
            return False, "Action count is zero.", [], TimestampSource.CALLER_PROVIDED

        if timestamps is not None:
            if expected_source == TimestampSource.LOCALLY_GENERATED_MONOTONIC:
                return (
                    False,
                    "Timestamp mode mismatch: Opponent sequence was initialized with locally generated timestamps, "
                    "but caller-provided timestamps were received. Reset opponent to change timestamp mode.",
                    [],
                    TimestampSource.CALLER_PROVIDED,
                )

            if len(timestamps) != action_count:
                return (
                    False,
                    f"Timestamp length mismatch: Received {len(timestamps)} timestamps for {action_count} actions.",
                    [],
                    TimestampSource.CALLER_PROVIDED,
                )

            prev_t = last_action_timestamp
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

        # Monotonic generation when caller timestamps omitted
        if expected_source == TimestampSource.CALLER_PROVIDED:
            return (
                False,
                "Timestamp mode mismatch: Opponent sequence was initialized with caller-provided timestamps, "
                "but no timestamps were supplied in this batch. Reset opponent to change timestamp mode.",
                [],
                TimestampSource.LOCALLY_GENERATED_MONOTONIC,
            )

        now = time.monotonic()
        base_step = 0.5  # 500ms nominal spacing for simulated action events
        if last_action_timestamp is not None and now <= last_action_timestamp:
            now = last_action_timestamp + 0.5

        generated = [now + (i * base_step) for i in range(action_count)]
        return True, "Valid", generated, TimestampSource.LOCALLY_GENERATED_MONOTONIC

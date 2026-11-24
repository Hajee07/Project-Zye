"""
Telemetry Input Security.
Screens input readings, rejects NaN/Infinity/Booleans, and guarantees atomic batch integrity.
"""

from __future__ import annotations

import math
from typing import Any, List, Tuple


class TelemetryInputSecurity:
    """Validates raw numeric values and batch dimensions before buffer ingestion."""

    @classmethod
    def validate_numeric_reading(cls, val: Any) -> Tuple[bool, str]:
        """Ensures value is a strictly valid, finite float/int and NOT a boolean or NaN/Inf."""
        # Booleans inherit from int in Python (isinstance(True, int) == True)
        if isinstance(val, bool):
            return False, "Boolean values are not permitted as numerical measurements."

        if not isinstance(val, (int, float)):
            return False, f"Value '{val}' is not a numeric type ({type(val).__name__})."

        if math.isnan(val):
            return False, "NaN (Not-a-Number) measurements are rejected."

        if math.isinf(val):
            return False, "Infinite values are rejected."

        return True, "Valid"

    @classmethod
    def validate_readings_batch(cls, readings: List[Any], max_batch_size: int = 1000) -> Tuple[bool, str]:
        """Validates an entire batch of readings atomically."""
        if not isinstance(readings, (list, tuple)):
            return False, "Readings must be provided as a list or tuple."

        if len(readings) == 0:
            return False, "Telemetry batch cannot be empty."

        if len(readings) > max_batch_size:
            return False, f"Batch size ({len(readings)}) exceeds maximum limit of {max_batch_size}."

        for idx, r in enumerate(readings):
            is_valid, msg = cls.validate_numeric_reading(r)
            if not is_valid:
                return False, f"Invalid reading at index {idx}: {msg}"

        return True, "Valid"

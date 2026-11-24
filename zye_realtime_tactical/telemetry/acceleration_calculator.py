"""
Acceleration Calculator.
Calculates instantaneous second derivative: a = (v2 - v1) / dt
in measurement units per second squared, supporting irregular sampling intervals.
"""

from __future__ import annotations

from typing import Optional
import numpy as np


class AccelerationCalculator:
    """Computes second derivative of telemetry stream."""

    @classmethod
    def calculate_instantaneous_acceleration(
        cls,
        values: np.ndarray,
        timestamps: np.ndarray,
    ) -> Optional[float]:
        """
        Computes acceleration using the three latest observations:
            v1 = (x[-2] - x[-3]) / (t[-2] - t[-3])
            v2 = (x[-1] - x[-2]) / (t[-1] - t[-2])
            dt_acc = (t[-1] - t[-3]) / 2.0
            a = (v2 - v1) / dt_acc
            
        Returns:
            Acceleration in units/sec^2, or None if <3 samples or non-positive time intervals.
        """
        if len(values) < 3 or len(timestamps) < 3:
            return None

        x1, x2, x3 = float(values[-3]), float(values[-2]), float(values[-1])
        t1, t2, t3 = float(timestamps[-3]), float(timestamps[-2]), float(timestamps[-1])

        dt1 = t2 - t1
        dt2 = t3 - t2

        if dt1 <= 0 or dt2 <= 0:
            return None

        v1 = (x2 - x1) / dt1
        v2 = (x3 - x2) / dt2

        # Effective time delta between the two velocity estimates
        dt_acc = (t3 - t1) / 2.0
        if dt_acc <= 0:
            return None

        acceleration = (v2 - v1) / dt_acc
        return float(acceleration)

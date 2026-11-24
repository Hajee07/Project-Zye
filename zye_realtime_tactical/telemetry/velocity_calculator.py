"""
Velocity Calculator.
Calculates instantaneous first derivative: v = (x2 - x1) / (t2 - t1)
in measurement units per second, supporting irregular sampling intervals.
"""

from __future__ import annotations

from typing import Optional
import numpy as np


class VelocityCalculator:
    """Computes first derivative of telemetry stream."""

    @classmethod
    def calculate_instantaneous_velocity(
        cls,
        values: np.ndarray,
        timestamps: np.ndarray,
    ) -> Optional[float]:
        """
        Computes velocity between the two latest valid observations:
            v = (x[-1] - x[-2]) / (t[-1] - t[-2])
            
        Returns:
            Rate of change in units/sec, or None if <2 samples or non-positive delta time.
        """
        if len(values) < 2 or len(timestamps) < 2:
            return None

        x1 = float(values[-2])
        x2 = float(values[-1])
        t1 = float(timestamps[-2])
        t2 = float(timestamps[-1])

        dt = t2 - t1
        if dt <= 0:
            # Cannot divide by zero or negative time interval
            return None

        dx = x2 - x1
        velocity = dx / dt
        return float(velocity)

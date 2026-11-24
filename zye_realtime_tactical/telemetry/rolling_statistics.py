"""
Rolling Statistics Engine.
Vectorized NumPy computations for rolling mean, standard deviation, minimum,
and maximum over bounded telemetry windows.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import numpy as np


class RollingStatistics:
    """Calculates summary statistics using NumPy float64 operations."""

    @classmethod
    def calculate_window_statistics(
        cls,
        values: np.ndarray,
        use_sample_std: bool = False,
    ) -> Dict[str, Optional[float]]:
        """
        Computes rolling descriptive statistics on numerical array.
        
        Args:
            values: 1D NumPy array of float64 readings.
            use_sample_std: If True, uses ddof=1 (sample std); if False, ddof=0 (population std).
        
        Returns:
            dict containing current_value, mean, std_dev, min, max, sample_count.
        """
        n = len(values)
        if n == 0:
            return {
                "sample_count": 0,
                "current_value": None,
                "rolling_mean": None,
                "std_dev": None,
                "min_value": None,
                "max_value": None,
            }

        curr_val = float(values[-1])
        if n == 1:
            return {
                "sample_count": 1,
                "current_value": curr_val,
                "rolling_mean": curr_val,
                "std_dev": 0.0,
                "min_value": curr_val,
                "max_value": curr_val,
            }

        mean_val = float(np.mean(values))
        ddof = 1 if (use_sample_std and n > 1) else 0
        std_val = float(np.std(values, ddof=ddof))
        min_val = float(np.min(values))
        max_val = float(np.max(values))

        return {
            "sample_count": n,
            "current_value": curr_val,
            "rolling_mean": mean_val,
            "std_dev": std_val,
            "min_value": min_val,
            "max_value": max_val,
        }

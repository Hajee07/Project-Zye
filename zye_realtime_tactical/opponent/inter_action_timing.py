"""
Inter-Action Timing Analysis Engine (Day 36).
High-precision delta calculation using NumPy diff over valid interval window [0.05s, 60.0s].
Computes expected next attack interval and empirical timing statistics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np


class InterActionTimingAnalyzer:
    """Calculates empirical interval distributions between consecutive tactical events."""

    MIN_VALID_INTERVAL_SEC: float = 0.05
    MAX_VALID_INTERVAL_SEC: float = 60.0

    @classmethod
    def analyze(cls, timestamps: List[float]) -> Dict[str, Any]:
        """
        Computes inter-action deltas using numpy.diff, filters out sub-50ms jitter and
        pauses over 60s, and computes summary statistics.
        Zero fabrication: if fewer than 1 valid interval exists, returns None for expected attack.
        """
        if len(timestamps) < 2:
            return {
                "expected_next_attack_in_sec": None,
                "timing_basis": "INSUFFICIENT_TIMESTAMPS",
                "valid_interval_count": 0,
                "mean_interval_sec": None,
                "median_interval_sec": None,
                "min_interval_sec": None,
                "max_interval_sec": None,
                "std_dev_sec": None,
            }

        ts_array = np.array(timestamps, dtype=np.float64)
        diffs = np.diff(ts_array)

        # Filter to valid realistic combat / interaction range: [0.05s, 60.0s]
        valid_mask = (diffs >= cls.MIN_VALID_INTERVAL_SEC) & (diffs <= cls.MAX_VALID_INTERVAL_SEC)
        valid_diffs = diffs[valid_mask]

        if len(valid_diffs) == 0:
            return {
                "expected_next_attack_in_sec": None,
                "timing_basis": "INSUFFICIENT_VALID_INTERVALS",
                "valid_interval_count": 0,
                "mean_interval_sec": None,
                "median_interval_sec": None,
                "min_interval_sec": None,
                "max_interval_sec": None,
                "std_dev_sec": None,
            }

        mean_val = float(np.mean(valid_diffs))
        median_val = float(np.median(valid_diffs))
        min_val = float(np.min(valid_diffs))
        max_val = float(np.max(valid_diffs))
        std_val = float(np.std(valid_diffs))

        return {
            "expected_next_attack_in_sec": round(mean_val, 4),
            "timing_basis": "AVERAGE_VALID_INTERVALS",
            "valid_interval_count": int(len(valid_diffs)),
            "mean_interval_sec": round(mean_val, 4),
            "median_interval_sec": round(median_val, 4),
            "min_interval_sec": round(min_val, 4),
            "max_interval_sec": round(max_val, 4),
            "std_dev_sec": round(std_val, 4),
        }

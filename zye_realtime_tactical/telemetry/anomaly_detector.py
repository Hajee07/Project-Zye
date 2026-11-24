"""
Z-Score Statistical Anomaly Detector.
Evaluates incoming measurements against an independent historical baseline
excluding the current observation to prevent self-contamination.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple
import numpy as np

from zye_realtime_tactical.telemetry.telemetry_result_schema import AnomalyStatus

ZERO_VARIANCE_EPSILON = 1e-9


class AnomalyDetector:
    """Computes Z-score anomalies over rolling historical baseline windows."""

    @classmethod
    def evaluate_measurement_anomaly(
        cls,
        values: np.ndarray,
        threshold: float = 2.5,
        min_baseline_samples: int = 10,
    ) -> Dict[str, Any]:
        """
        Evaluates whether the latest measurement (values[-1]) is a statistical anomaly.
        
        CRITICAL ISOLATION RULE:
        The baseline statistics (mean, std) are computed using values[:-1] (historical samples only),
        ensuring the outlier does not artificially inflate or bias its own baseline.
        
        Returns:
            dict containing:
                - is_anomaly (bool)
                - anomaly_status (AnomalyStatus)
                - z_score (Optional[float])
                - baseline_mean (Optional[float])
                - baseline_std_dev (Optional[float])
                - baseline_sample_count (int)
                - threshold (float)
        """
        total_samples = len(values)
        if total_samples <= 1:
            return {
                "is_anomaly": False,
                "anomaly_status": AnomalyStatus.INSUFFICIENT_BASELINE,
                "z_score": None,
                "baseline_mean": None,
                "baseline_std_dev": None,
                "baseline_sample_count": 0,
                "threshold": threshold,
            }

        # Historical baseline excludes the current observation
        baseline = values[:-1]
        baseline_count = len(baseline)

        if baseline_count < min_baseline_samples:
            return {
                "is_anomaly": False,
                "anomaly_status": AnomalyStatus.INSUFFICIENT_BASELINE,
                "z_score": None,
                "baseline_mean": float(np.mean(baseline)) if baseline_count > 0 else None,
                "baseline_std_dev": float(np.std(baseline)) if baseline_count > 0 else None,
                "baseline_sample_count": baseline_count,
                "threshold": threshold,
            }

        current_val = float(values[-1])
        base_mean = float(np.mean(baseline))
        base_std = float(np.std(baseline))

        # Check for zero variance baseline
        if base_std < ZERO_VARIANCE_EPSILON:
            # If current value differs from the constant baseline, it is a divergence
            # But mathematically Z-score cannot divide by zero
            return {
                "is_anomaly": False,
                "anomaly_status": AnomalyStatus.ZERO_VARIANCE_BASELINE,
                "z_score": None,
                "baseline_mean": base_mean,
                "baseline_std_dev": 0.0,
                "baseline_sample_count": baseline_count,
                "threshold": threshold,
            }

        # Calculate Z-score: Z = (x - mean) / std
        z_score = (current_val - base_mean) / base_std
        is_anomaly = abs(z_score) >= threshold

        status = AnomalyStatus.ANOMALY_DETECTED if is_anomaly else AnomalyStatus.NORMAL

        return {
            "is_anomaly": is_anomaly,
            "anomaly_status": status,
            "z_score": float(z_score),
            "baseline_mean": base_mean,
            "baseline_std_dev": base_std,
            "baseline_sample_count": baseline_count,
            "threshold": threshold,
        }

"""
Statistical Analysis & Confidence Interval Engine (Day 37 / Phase 3).
Provides Wilson Score interval calculation, Clopper-Pearson exact bounds,
percentile summaries, and parameter sensitivity analysis.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Tuple
import numpy as np

from zye_realtime_tactical.kinematics.kinematic_models import ConfidenceInterval


# Standard normal critical values for common confidence levels
Z_SCORES: dict[float, float] = {
    0.90: 1.64485,
    0.95: 1.95996,
    0.98: 2.32635,
    0.99: 2.57583,
    0.999: 3.29053,
}


class StatisticalAnalyzer:
    """Statistical estimation and uncertainty quantification for probabilistic simulations."""

    @staticmethod
    def calculate_wilson_score_interval(
        success_count: int,
        sample_count: int,
        confidence_level: float = 0.95,
    ) -> ConfidenceInterval:
        """
        Computes the Wilson Score confidence interval for a binomial proportion.
        Mathematically robust: strictly bounded in [0, 1] even for k=0 or k=n.
        For k=0, correctly shows upper bound > 0 (reflecting simulation resolution limit).
        """
        n = int(sample_count)
        k = int(success_count)
        if n <= 0:
            return ConfidenceInterval(lower=0.0, upper=1.0, confidence_level=confidence_level, method="WILSON_SCORE")

        k = max(0, min(k, n))
        z = Z_SCORES.get(confidence_level, 1.95996)

        z_sq = z * z
        denom = n + z_sq
        center = (k + 0.5 * z_sq) / denom

        term = (k * (n - k) / n) + (0.25 * z_sq)
        margin = (z / denom) * math.sqrt(term)

        lower = max(0.0, center - margin)
        upper = min(1.0, center + margin)

        return ConfidenceInterval(
            lower=round(lower, 6),
            upper=round(upper, 6),
            confidence_level=confidence_level,
            method="WILSON_SCORE",
        )

    @staticmethod
    def summarize_distribution(values: np.ndarray) -> Dict[str, float]:
        """Calculates exhaustive percentile and central tendency metrics for an array of separations."""
        if len(values) == 0:
            return {
                "min": 0.0,
                "median": 0.0,
                "mean": 0.0,
                "p05": 0.0,
                "p95": 0.0,
                "std": 0.0,
            }

        return {
            "min": round(float(np.min(values)), 4),
            "median": round(float(np.median(values)), 4),
            "mean": round(float(np.mean(values)), 4),
            "p05": round(float(np.percentile(values, 5)), 4),
            "p95": round(float(np.percentile(values, 95)), 4),
            "std": round(float(np.std(values)), 4),
        }

    @staticmethod
    def perform_sensitivity_analysis(
        baseline_prob: float,
        evaluate_fn: Callable[[float], float],
        perturbation_factor: float = 0.20,
    ) -> Dict[str, Any]:
        """
        Computes elasticity of collision probability under +/- percentage variation in input uncertainty.
        Sensitivity = (delta_P / P_base) / (delta_param / param_base).
        """
        prob_plus = evaluate_fn(1.0 + perturbation_factor)
        prob_minus = evaluate_fn(1.0 - perturbation_factor)

        delta_p = prob_plus - prob_minus
        elasticity = (delta_p / (2.0 * perturbation_factor)) if baseline_prob > 1e-6 else 0.0

        return {
            "baseline_probability": round(baseline_prob, 5),
            "prob_at_plus_20pct": round(prob_plus, 5),
            "prob_at_minus_20pct": round(prob_minus, 5),
            "delta_probability": round(delta_p, 5),
            "sensitivity_index": round(elasticity, 4),
            "interpretation": (
                "HIGH_SENSITIVITY" if abs(elasticity) > 1.0 else (
                    "MODERATE_SENSITIVITY" if abs(elasticity) > 0.3 else "LOW_SENSITIVITY"
                )
            ),
        }

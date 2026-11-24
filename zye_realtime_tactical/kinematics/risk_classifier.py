"""
Risk Classification Engine (Day 37 / Phase 3).
Provides transparent, rule-based risk categorization for deterministic and probabilistic outcomes,
grounded strictly in physical separation thresholds, collision probabilities, and closure rates.
"""

from __future__ import annotations

from typing import Tuple
from zye_realtime_tactical.kinematics.kinematic_models import (
    RiskCategory,
    SafetyEnvelope,
)


class RiskClassifier:
    """Classifies movement-related risk with explainable causal justifications."""

    DISCLAIMER = (
        "ANALYTICAL ADVISORY ONLY: Simulation risk estimates are mathematical projections "
        "under modeled uncertainty and must not be used as sole inputs for certified life-critical machinery control."
    )

    @classmethod
    def classify_probabilistic_risk(
        cls,
        collision_prob: float,
        near_miss_prob: float,
        p05_separation: float,
        median_separation: float,
        envelope: SafetyEnvelope,
    ) -> Tuple[RiskCategory, str]:
        """
        Classifies Monte Carlo probabilistic simulation results.
        Returns:
            (RiskCategory, detailed_explanation)
        """
        # Thresholds
        crit_prob_threshold = 0.25      # > 25% collision probability
        high_prob_threshold = 0.05      # > 5% collision probability
        mod_prob_threshold = 0.01       # > 1% collision probability
        high_near_miss_threshold = 0.40 # > 40% near-miss probability

        # 1. CRITICAL Risk
        if collision_prob >= crit_prob_threshold or p05_separation <= envelope.combined_radius:
            return (
                RiskCategory.CRITICAL,
                f"CRITICAL risk: Collision probability {collision_prob * 100.0:.2f}% exceeds {crit_prob_threshold * 100:.0f}% threshold, "
                f"or 5th-percentile separation ({p05_separation:.2f}m) penetrates combined physical boundary ({envelope.combined_radius:.2f}m). "
                f"{cls.DISCLAIMER}"
            )

        # 2. HIGH Risk
        if collision_prob >= high_prob_threshold or near_miss_prob >= high_near_miss_threshold or p05_separation <= envelope.near_miss_radius:
            return (
                RiskCategory.HIGH,
                f"HIGH risk: Collision probability {collision_prob * 100.0:.2f}% (threshold {high_prob_threshold * 100:.0f}%) "
                f"or near-miss probability {near_miss_prob * 100.0:.2f}% (threshold {high_near_miss_threshold * 100:.0f}%). "
                f"Worst 5% separation ({p05_separation:.2f}m) enters safety envelope ({envelope.near_miss_radius:.2f}m). "
                f"{cls.DISCLAIMER}"
            )

        # 3. MODERATE Risk
        if collision_prob >= mod_prob_threshold or near_miss_prob >= 0.10:
            return (
                RiskCategory.MODERATE,
                f"MODERATE risk: Low but non-negligible collision probability {collision_prob * 100.0:.2f}% "
                f"with near-miss probability {near_miss_prob * 100.0:.2f}%. Median separation is {median_separation:.2f}m. "
                f"{cls.DISCLAIMER}"
            )

        # 4. LOW Risk
        if near_miss_prob > 0.0 or median_separation <= (envelope.near_miss_radius * 2.0):
            return (
                RiskCategory.LOW,
                f"LOW risk: Minimal collision probability ({collision_prob * 100.0:.3f}%). "
                f"Near-miss probability is {near_miss_prob * 100.0:.2f}%, and median separation ({median_separation:.2f}m) maintains adequate clearance. "
                f"{cls.DISCLAIMER}"
            )

        # 5. MINIMAL Risk
        return (
            RiskCategory.MINIMAL,
            f"MINIMAL risk: Zero or statistically negligible collision/near-miss events observed. "
            f"Median separation ({median_separation:.2f}m) well exceeds safety envelope ({envelope.near_miss_radius:.2f}m). "
            f"{cls.DISCLAIMER}"
        )

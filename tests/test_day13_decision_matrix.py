"""
Unit tests for Day 13 Multi-Solution Comparison and Decision Engine.
Tests zye_intelligence.decision_matrix: ZyeDecisionMatrix, compare_and_decide_solutions,
PRIORITY_WEIGHTS, and safety cutoff veto constraints.
"""

from __future__ import annotations

import math
import unittest

from zye_intelligence.decision_matrix import (
    PRIORITY_WEIGHTS,
    ZyeDecisionMatrix,
    compare_and_decide_solutions,
)
from zye_intelligence.schemas import SolutionCandidate


class TestDay13DecisionMatrix(unittest.TestCase):
    def setUp(self) -> None:
        self.matrix = ZyeDecisionMatrix()

    def test_01_balanced_weights(self) -> None:
        """Test balanced priority weights values and summation."""
        w = PRIORITY_WEIGHTS["balanced"]
        self.assertEqual(w["reliability"], 0.35)
        self.assertEqual(w["speed"], 0.25)
        self.assertEqual(w["safety"], 0.25)
        self.assertEqual(w["simplicity"], 0.15)
        self.assertAlmostEqual(sum(w.values()), 1.0)

    def test_02_speed_critical_weights(self) -> None:
        """Test speed_critical priority weights."""
        w = PRIORITY_WEIGHTS["speed_critical"]
        self.assertEqual(w["speed"], 0.50)
        self.assertAlmostEqual(sum(w.values()), 1.0)

    def test_03_maximum_safety_weights(self) -> None:
        """Test maximum_safety priority weights."""
        w = PRIORITY_WEIGHTS["maximum_safety"]
        self.assertEqual(w["safety"], 0.45)
        self.assertAlmostEqual(sum(w.values()), 1.0)

    def test_04_low_resource_weights(self) -> None:
        """Test low_resource priority weights."""
        w = PRIORITY_WEIGHTS["low_resource"]
        self.assertEqual(w["simplicity"], 0.25)
        self.assertAlmostEqual(sum(w.values()), 1.0)

    def test_05_weight_total_validation(self) -> None:
        """Verify that every defined priority mode sums exactly to 1.0."""
        for mode, weights in PRIORITY_WEIGHTS.items():
            total = sum(weights.values())
            self.assertAlmostEqual(total, 1.0, places=5, msg=f"Mode {mode} does not total 1.0")

    def test_06_invalid_scores(self) -> None:
        """Verify that scores outside [1.0, 10.0] or non-finite values are rejected."""
        with self.assertRaises(ValueError):
            SolutionCandidate(name="Bad", description="bad", reliability=0.5, speed=5, safety=5, simplicity=5)

        with self.assertRaises(ValueError):
            SolutionCandidate(name="Bad", description="bad", reliability=11.0, speed=5, safety=5, simplicity=5)

        with self.assertRaises(ValueError):
            SolutionCandidate(name="Bad", description="bad", reliability=float("nan"), speed=5, safety=5, simplicity=5)

    def test_07_missing_scores(self) -> None:
        """Test that missing candidate scores raise validation errors."""
        with self.assertRaises(Exception):
            SolutionCandidate(name="Incomplete", description="incomplete", reliability=5.0)

    def test_08_empty_candidates(self) -> None:
        """Verify that comparing empty candidate list raises ValueError."""
        with self.assertRaises(ValueError):
            self.matrix.compare_solutions("Task", [])

    def test_09_duplicate_solutions(self) -> None:
        """Verify that identical candidates are ranked deterministically."""
        cand_a = {"name": "Candidate_A", "description": "approach A", "reliability": 8.0, "speed": 8.0, "safety": 8.0, "simplicity": 8.0}
        cand_b = {"name": "Candidate_B", "description": "approach B", "reliability": 8.0, "speed": 8.0, "safety": 8.0, "simplicity": 8.0}
        res = self.matrix.compare_solutions("Task", [cand_a, cand_b])
        self.assertEqual(len(res["full_comparison_ranking"]), 2)
        self.assertEqual(res["weighted_scores"]["Candidate_A"], res["weighted_scores"]["Candidate_B"])

    def test_10_safety_constraint(self) -> None:
        """Verify that an unsafe top candidate (safety < threshold) is vetoed in favor of safe option."""
        unsafe_fast = {
            "name": "Unsafe_Fast",
            "description": "Blazing fast but dangerous",
            "reliability": 9.0,
            "speed": 10.0,
            "safety": 1.5,  # Unsafe < 3.0
            "simplicity": 9.0,
        }
        safe_moderate = {
            "name": "Safe_Moderate",
            "description": "Careful AST patch with backup",
            "reliability": 8.5,
            "speed": 7.0,
            "safety": 9.0,  # Safe >= 3.0
            "simplicity": 7.0,
        }
        res = self.matrix.compare_solutions("Patch code", [unsafe_fast, safe_moderate], priority_mode="speed_critical")
        # In speed_critical, unsafe_fast has higher raw score, but must be vetoed by safety threshold
        rec = res["recommended_best_solution"]
        self.assertEqual(rec["name"], "Safe_Moderate")
        self.assertIn("vetoed", res["recommendation_reason"].lower())

    def test_11_no_safe_solution(self) -> None:
        """Verify handling when all candidates violate safety thresholds."""
        unsafe_1 = {"name": "Unsafe_1", "description": "bad 1", "reliability": 5.0, "speed": 5.0, "safety": 1.0, "simplicity": 5.0}
        unsafe_2 = {"name": "Unsafe_2", "description": "bad 2", "reliability": 5.0, "speed": 5.0, "safety": 2.0, "simplicity": 5.0}
        res = self.matrix.compare_solutions("Risky operation", [unsafe_1, unsafe_2])
        self.assertEqual(res["recommended_best_solution"]["name"], "NO_SAFE_SOLUTION")
        self.assertIn("NO_SAFE_SOLUTION", res["recommendation_reason"])

    def test_12_deterministic_ranking(self) -> None:
        """Verify deterministic ranking order."""
        c1 = {"name": "Low", "description": "low", "reliability": 3.0, "speed": 3.0, "safety": 5.0, "simplicity": 3.0}
        c2 = {"name": "High", "description": "high", "reliability": 9.0, "speed": 9.0, "safety": 9.0, "simplicity": 9.0}
        c3 = {"name": "Mid", "description": "mid", "reliability": 6.0, "speed": 6.0, "safety": 6.0, "simplicity": 6.0}
        res = compare_and_decide_solutions("Problem", [c1, c2, c3], priority_mode="balanced")
        ranking = [c["name"] for c in res["full_comparison_ranking"]]
        self.assertEqual(ranking, ["High", "Mid", "Low"])


if __name__ == "__main__":
    unittest.main()

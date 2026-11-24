"""Unit tests for Zye Day 11 Multi-Solution Weighted Decision Matrix."""

import math
import unittest

from zye_autonomy.decision_matrix import PRIORITY_WEIGHTS, ZyeDecisionMatrix


class TestZyeDecisionMatrix(unittest.TestCase):
    def setUp(self):
        self.dm = ZyeDecisionMatrix()
        self.sample_candidates = [
            {"name": "SolA", "description": "Approach A", "reliability": 9.0, "speed": 7.0, "safety": 8.0, "simplicity": 6.0},
            {"name": "SolB", "description": "Approach B", "reliability": 6.0, "speed": 9.0, "safety": 7.0, "simplicity": 8.0},
            {"name": "SolC", "description": "Approach C", "reliability": 8.0, "speed": 6.0, "safety": 9.0, "simplicity": 7.0},
        ]

    def test_01_balanced_scoring(self):
        res = self.dm.compare_solutions("Task 1", self.sample_candidates, "balanced")
        self.assertEqual(res["priority_mode"], "balanced")
        best = res["recommended_best_solution"]
        # SolA: 9*0.35 + 7*0.25 + 8*0.25 + 6*0.15 = 3.15 + 1.75 + 2.0 + 0.9 = 7.8
        # SolB: 6*0.35 + 9*0.25 + 7*0.25 + 8*0.15 = 2.1 + 2.25 + 1.75 + 1.2 = 7.3
        # SolC: 8*0.35 + 6*0.25 + 9*0.25 + 7*0.15 = 2.8 + 1.5 + 2.25 + 1.05 = 7.6
        self.assertEqual(best["name"], "SolA")
        self.assertAlmostEqual(best["weighted_score"], 7.8, places=2)

    def test_02_speed_critical_scoring(self):
        res = self.dm.compare_solutions("Task 2", self.sample_candidates, "speed_critical")
        self.assertEqual(res["priority_mode"], "speed_critical")
        # SolA: 9*0.25 + 7*0.50 + 8*0.15 + 6*0.10 = 2.25 + 3.5 + 1.2 + 0.6 = 7.55
        # SolB: 6*0.25 + 9*0.50 + 7*0.15 + 8*0.10 = 1.5 + 4.5 + 1.05 + 0.8 = 7.85
        # SolC: 8*0.25 + 6*0.50 + 9*0.15 + 7*0.10 = 2.0 + 3.0 + 1.35 + 0.7 = 7.05
        best = res["recommended_best_solution"]
        self.assertEqual(best["name"], "SolB")
        self.assertAlmostEqual(best["weighted_score"], 7.85, places=2)

    def test_03_maximum_safety_scoring(self):
        res = self.dm.compare_solutions("Task 3", self.sample_candidates, "maximum_safety")
        # SolA: 9*0.35 + 7*0.10 + 8*0.45 + 6*0.10 = 3.15 + 0.7 + 3.6 + 0.6 = 8.05
        # SolB: 6*0.35 + 9*0.10 + 7*0.45 + 8*0.10 = 2.1 + 0.9 + 3.15 + 0.8 = 6.95
        # SolC: 8*0.35 + 6*0.10 + 9*0.45 + 7*0.10 = 2.8 + 0.6 + 4.05 + 0.7 = 8.15
        best = res["recommended_best_solution"]
        self.assertEqual(best["name"], "SolC")
        self.assertAlmostEqual(best["weighted_score"], 8.15, places=2)

    def test_04_low_resource_scoring(self):
        res = self.dm.compare_solutions("Task 4", self.sample_candidates, "low_resource")
        self.assertEqual(res["priority_mode"], "low_resource")
        self.assertIn("recommended_best_solution", res)

    def test_05_invalid_priority_mode_raises(self):
        with self.assertRaises(ValueError):
            self.dm.compare_solutions("Task", self.sample_candidates, "invalid_mode")

    def test_06_invalid_score_range_raises(self):
        bad_candidates = [
            {"name": "Bad", "description": "d", "reliability": 15.0, "speed": 5.0, "safety": 5.0, "simplicity": 5.0}
        ]
        with self.assertRaises(Exception):
            self.dm.compare_solutions("Task", bad_candidates)

    def test_07_nan_input_raises(self):
        bad_candidates = [
            {"name": "Bad", "description": "d", "reliability": float("nan"), "speed": 5.0, "safety": 5.0, "simplicity": 5.0}
        ]
        with self.assertRaises(Exception):
            self.dm.compare_solutions("Task", bad_candidates)

    def test_08_infinity_input_raises(self):
        bad_candidates = [
            {"name": "Bad", "description": "d", "reliability": float("inf"), "speed": 5.0, "safety": 5.0, "simplicity": 5.0}
        ]
        with self.assertRaises(Exception):
            self.dm.compare_solutions("Task", bad_candidates)

    def test_09_missing_candidates_raises(self):
        with self.assertRaises(ValueError):
            self.dm.compare_solutions("Task", [])

    def test_10_candidate_ranking_order(self):
        res = self.dm.compare_solutions("Task", self.sample_candidates, "balanced")
        ranking = res["full_comparison_ranking"]
        self.assertEqual(len(ranking), 3)
        self.assertGreaterEqual(ranking[0]["weighted_score"], ranking[1]["weighted_score"])
        self.assertGreaterEqual(ranking[1]["weighted_score"], ranking[2]["weighted_score"])

    def test_11_weighted_score_accuracy(self):
        sol = {"reliability": 10.0, "speed": 10.0, "safety": 10.0, "simplicity": 10.0}
        weights = PRIORITY_WEIGHTS["balanced"]
        score = self.dm.calculate_weighted_score(sol, weights)
        self.assertAlmostEqual(score, 10.0, places=4)

    def test_12_safety_rejection(self):
        candidates = [
            {"name": "DangerousFast", "description": "Very fast but unsafe", "reliability": 9.0, "speed": 10.0, "safety": 1.5, "simplicity": 9.0},
            {"name": "SafeModerate", "description": "Balanced and safe", "reliability": 8.0, "speed": 6.0, "safety": 8.5, "simplicity": 7.0},
        ]
        res = self.dm.compare_solutions("Task", candidates, "speed_critical")
        # DangerousFast has higher weighted score, but safety < 3.0, so SafeModerate must be chosen
        best = res["recommended_best_solution"]
        self.assertEqual(best["name"], "SafeModerate")
        self.assertIn("REJECTED", res["recommendation_reason"])

    def test_13_tie_handling(self):
        candidates = [
            {"name": "TieA", "description": "A", "reliability": 8.0, "speed": 8.0, "safety": 8.0, "simplicity": 8.0},
            {"name": "TieB", "description": "B", "reliability": 8.0, "speed": 8.0, "safety": 8.0, "simplicity": 8.0},
        ]
        res = self.dm.compare_solutions("Task", candidates, "balanced")
        self.assertEqual(len(res["full_comparison_ranking"]), 2)
        self.assertEqual(
            res["full_comparison_ranking"][0]["weighted_score"],
            res["full_comparison_ranking"][1]["weighted_score"],
        )


if __name__ == "__main__":
    unittest.main()

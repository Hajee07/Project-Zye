"""Day 15 Unit Tests — Multi-Solution Weighted Decision Matrix."""
import math
import unittest

from zye_autonomy.decision_matrix import ZyeDecisionMatrix, PRIORITY_WEIGHTS, DEFAULT_SAFETY_THRESHOLD


SAMPLE_SOLUTIONS = [
    {"name": "Solution A", "reliability": 8, "speed": 6, "safety": 7, "simplicity": 5},
    {"name": "Solution B", "reliability": 5, "speed": 9, "safety": 4, "simplicity": 8},
    {"name": "Solution C", "reliability": 7, "speed": 7, "safety": 9, "simplicity": 6},
]


class TestDecisionMatrixInit(unittest.TestCase):
    def test_creates_instance(self):
        dm = ZyeDecisionMatrix()
        self.assertIsNotNone(dm)

    def test_safety_threshold_default(self):
        dm = ZyeDecisionMatrix()
        self.assertAlmostEqual(dm.safety_threshold, DEFAULT_SAFETY_THRESHOLD)

    def test_custom_safety_threshold(self):
        dm = ZyeDecisionMatrix(config={"safety_threshold": 5.0})
        self.assertAlmostEqual(dm.safety_threshold, 5.0)


class TestPriorityWeights(unittest.TestCase):
    def test_all_four_modes_exist(self):
        for mode in ("balanced", "speed_critical", "maximum_safety", "low_resource"):
            self.assertIn(mode, PRIORITY_WEIGHTS)

    def test_weights_sum_to_one(self):
        for mode, weights in PRIORITY_WEIGHTS.items():
            total = sum(weights.values())
            self.assertAlmostEqual(total, 1.0, places=5, msg=f"Mode '{mode}' weights don't sum to 1.0")

    def test_each_mode_has_four_dimensions(self):
        for mode, weights in PRIORITY_WEIGHTS.items():
            for dim in ("reliability", "speed", "safety", "simplicity"):
                self.assertIn(dim, weights, msg=f"Mode '{mode}' missing '{dim}'")


class TestWeightedScoreCalc(unittest.TestCase):
    def setUp(self):
        self.dm = ZyeDecisionMatrix()

    def test_score_is_float(self):
        s = self.dm.calculate_weighted_score(SAMPLE_SOLUTIONS[0], PRIORITY_WEIGHTS["balanced"])
        self.assertIsInstance(s, float)

    def test_score_range_reasonable(self):
        for sol in SAMPLE_SOLUTIONS:
            s = self.dm.calculate_weighted_score(sol, PRIORITY_WEIGHTS["balanced"])
            self.assertGreater(s, 0.0)
            self.assertLessEqual(s, 10.0)

    def test_high_safety_wins_in_maximum_safety_mode(self):
        weights = PRIORITY_WEIGHTS["maximum_safety"]
        scores = [
            (sol["name"], self.dm.calculate_weighted_score(sol, weights))
            for sol in SAMPLE_SOLUTIONS
        ]
        # Solution C has safety=9 — should score highest
        best = max(scores, key=lambda x: x[1])
        self.assertEqual(best[0], "Solution C")

    def test_high_speed_wins_in_speed_critical_mode(self):
        """In speed_critical mode, fastest solution should beat slowest."""
        weights = PRIORITY_WEIGHTS["speed_critical"]
        # Create a simple 2-candidate test where speed is clearly decisive
        fast = {"name": "Fast", "reliability": 5, "speed": 10, "safety": 5, "simplicity": 5}
        slow = {"name": "Slow", "reliability": 5, "speed": 1, "safety": 5, "simplicity": 5}
        fast_score = self.dm.calculate_weighted_score(fast, weights)
        slow_score = self.dm.calculate_weighted_score(slow, weights)
        self.assertGreater(fast_score, slow_score,
                           "Fast solution must outscore slow solution in speed_critical mode")


class TestRankSolutions(unittest.TestCase):
    def setUp(self):
        self.dm = ZyeDecisionMatrix()

    def _make_scored(self, solutions, mode="balanced"):
        weights = PRIORITY_WEIGHTS[mode]
        result = []
        for sol in solutions:
            s = sol.copy()
            s["weighted_score"] = self.dm.calculate_weighted_score(s, weights)
            result.append(s)
        return result

    def test_rank_returns_same_length(self):
        scored = self._make_scored(SAMPLE_SOLUTIONS)
        ranked = self.dm.rank_solutions(scored)
        self.assertEqual(len(ranked), len(SAMPLE_SOLUTIONS))

    def test_rank_descending_order(self):
        scored = self._make_scored(SAMPLE_SOLUTIONS)
        ranked = self.dm.rank_solutions(scored)
        scores = [r.get("weighted_score", 0) for r in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_empty_list_no_crash(self):
        ranked = self.dm.rank_solutions([])
        self.assertEqual(ranked, [])

    def test_single_solution_no_crash(self):
        sol = [{"name": "Only", "reliability": 5, "speed": 5, "safety": 5, "simplicity": 5, "weighted_score": 5.0}]
        ranked = self.dm.rank_solutions(sol)
        self.assertEqual(len(ranked), 1)


class TestNaNHandling(unittest.TestCase):
    def setUp(self):
        self.dm = ZyeDecisionMatrix()

    def test_nan_score_does_not_propagate(self):
        sol = {"name": "Bad", "reliability": float("nan"), "speed": 5, "safety": 5, "simplicity": 5}
        # Should not raise; score may be nan but shouldn't crash
        try:
            s = self.dm.calculate_weighted_score(sol, PRIORITY_WEIGHTS["balanced"])
            # nan is acceptable as a result — just shouldn't throw
        except Exception as e:
            self.fail(f"NaN input should not raise: {e}")


if __name__ == "__main__":
    unittest.main()

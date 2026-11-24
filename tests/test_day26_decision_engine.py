"""Day 26 Unit Tests: Multi-Criteria Weighted Decision Engine.

Tests:
- Priority modes (BALANCED, SPEED_CRITICAL, MAXIMUM_SAFETY, LOW_RESOURCE, etc.)
- Custom weight normalization
- Solution ranking, score separation, and provisional decision flags
"""

import unittest

from zye_ai_plugins.decision_engine import (
    PRIORITY_MODES,
    calculate_weighted_scores,
    get_priority_mode_weights,
    rank_candidate_solutions,
)


class TestDay26DecisionEngine(unittest.TestCase):
    """Test suite for Decision Engine."""

    def test_01_priority_modes_exist(self):
        """Verify all 6 core priority presets exist."""
        expected = ["balanced", "speed_critical", "maximum_safety", "low_resource", "high_reliability", "maintainability_first"]
        for exp in expected:
            self.assertIn(exp, PRIORITY_MODES)
            weights = get_priority_mode_weights(exp)
            self.assertAlmostEqual(sum(weights.values()), 1.0, places=2)

    def test_02_custom_weights_normalization(self):
        """Verify arbitrary custom weights normalize cleanly to 1.0."""
        custom = {"performance": 10.0, "safety": 30.0}
        weights = get_priority_mode_weights("user_custom", custom_weights=custom)
        self.assertEqual(weights["performance"], 0.25)
        self.assertEqual(weights["safety"], 0.75)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=2)

    def test_03_rank_solutions_differentiation(self):
        """Verify candidate ranking shifts accurately based on selected priority mode."""
        candidates = {
            "fast_api": {
                "title": "FastAPI Architecture",
                "provider_id": "chatgpt",
                "scores": {"performance": 0.95, "safety": 0.70, "reliability": 0.80},
                "pros": ["Ultra low latency"],
                "cons": ["Requires careful async handling"],
            },
            "django_monolith": {
                "title": "Django Architecture",
                "provider_id": "claude",
                "scores": {"performance": 0.65, "safety": 0.98, "reliability": 0.95},
                "pros": ["Built-in security", "Battle tested"],
                "cons": ["Higher CPU overhead"],
            },
        }

        # 1. Under speed_critical -> fast_api must rank #1
        res_speed = rank_candidate_solutions(candidates, priority_mode="speed_critical")
        self.assertEqual(res_speed["recommended_solution"], "fast_api")
        self.assertEqual(res_speed["ranked_solutions"][0]["solution_id"], "fast_api")

        # 2. Under maximum_safety -> django_monolith must rank #1
        res_safety = rank_candidate_solutions(candidates, priority_mode="maximum_safety")
        self.assertEqual(res_safety["recommended_solution"], "django_monolith")
        self.assertEqual(res_safety["ranked_solutions"][0]["solution_id"], "django_monolith")

    def test_04_provisional_decision_detection(self):
        """Verify close scores (<0.05 separation) trigger is_provisional flag."""
        candidates = {
            "cand_1": {"title": "Option 1", "scores": {"performance": 0.80, "reliability": 0.80}},
            "cand_2": {"title": "Option 2", "scores": {"performance": 0.81, "reliability": 0.80}},
        }
        res = rank_candidate_solutions(candidates, priority_mode="balanced")
        self.assertTrue(res["is_provisional"])
        self.assertLess(res["score_separation"], 0.05)


if __name__ == "__main__":
    unittest.main()

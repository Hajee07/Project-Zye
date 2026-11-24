"""
Acceptance Test Suite: Day 36 Markov Prediction Adapter Integration.
Tests 20-21 covering conversion of Markov transition probabilities into kinematic acceleration priors,
handling insufficient observations, and unobserved pattern fallbacks.
"""

import time
import unittest

from zye_realtime_tactical.kinematics.markov_adapter import MarkovPredictionAdapter
from zye_realtime_tactical.opponent.opponent_buffer_manager import OpponentBufferManager


class TestMarkovIntegration(unittest.TestCase):
    """Verifies synthesis between Day 36 Opponent Markov Predictions and Day 37 Kinematics."""

    def setUp(self):
        OpponentBufferManager.reset_instance()
        self.mgr = OpponentBufferManager.get_instance()
        self.adapter = MarkovPredictionAdapter(buffer_manager=self.mgr)

    def tearDown(self):
        OpponentBufferManager.reset_instance()

    def test_20_markov_conditioned_acceleration_prior(self):
        """Test 20: Repeating action sequence produces conditioned kinematic acceleration prior."""
        now = time.time()
        buf = self.mgr.sequence_manager.get_or_create_buffer("boss_1")
        # Repeating pattern: punch -> dodge -> punch -> dodge -> punch -> dodge (>= 6 actions)
        seq = ["punch", "dodge", "punch", "dodge", "punch", "dodge"]
        for idx, act in enumerate(seq):
            buf.append(act, timestamp=now + idx * 0.5)

        status, expected_a, uncertainty, meta = self.adapter.extract_tactical_acceleration_prior(
            opponent_id="boss_1",
            dimension=2,
        )

        self.assertEqual(status, "MARKOV_CONDITIONED")
        self.assertIsNotNone(expected_a)
        self.assertEqual(len(expected_a), 2)
        self.assertIsNotNone(uncertainty)
        self.assertGreater(len(meta["action_breakdown"]), 0)
        # Expected action is "punch" after "dodge", which has positive forward acceleration [3.0, 0.0]
        self.assertGreater(expected_a[0], 0.0)

    def test_21_insufficient_actions_and_fallback(self):
        """Test 21: Fewer than 6 actions returns INSUFFICIENT_DATA and preserves baseline model."""
        now = time.time()
        buf = self.mgr.sequence_manager.get_or_create_buffer("trainee")
        # Only 3 actions
        for idx, act in enumerate(["attack", "dodge", "attack"]):
            buf.append(act, timestamp=now + idx * 0.5)

        status, expected_a, uncertainty, meta = self.adapter.extract_tactical_acceleration_prior(
            opponent_id="trainee",
            dimension=2,
        )

        self.assertEqual(status, "INSUFFICIENT_DATA")
        self.assertIsNone(expected_a)
        self.assertIsNone(uncertainty)
        self.assertIn("minimum 6 required", meta["message"])

    def test_21b_uninitialized_opponent_buffer(self):
        """Test 21b: Uninitialized opponent returns NOT_FOUND."""
        status, expected_a, uncertainty, meta = self.adapter.extract_tactical_acceleration_prior(
            opponent_id="ghost",
            dimension=2,
        )
        self.assertEqual(status, "NOT_FOUND")
        self.assertIsNone(expected_a)


if __name__ == "__main__":
    unittest.main()

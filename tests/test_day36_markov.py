"""
Unit Tests for ZYE AI Day 36: Opponent Behaviour Pattern Recognition & Markov Prediction.
15 deterministic acceptance tests covering evidence guards, 1st/2nd-order Markov transitions,
context selection, non-renormalization, bigrams/trigrams, timing, rollover, isolation, and MCP tools.
"""

import time
import unittest
from typing import List

from zye_realtime_tactical.opponent.bigram_pattern_detector import BigramPatternDetector
from zye_realtime_tactical.opponent.first_order_markov import FirstOrderMarkov
from zye_realtime_tactical.opponent.inter_action_timing import InterActionTimingAnalyzer
from zye_realtime_tactical.opponent.markov_context_selector import MarkovContextSelector
from zye_realtime_tactical.opponent.next_action_predictor import NextActionPredictor
from zye_realtime_tactical.opponent.opponent_action_models import OpponentAction, OpponentSequenceConfig
from zye_realtime_tactical.opponent.opponent_action_validator import OpponentActionValidator
from zye_realtime_tactical.opponent.opponent_buffer_manager import OpponentBufferManager
from zye_realtime_tactical.opponent.opponent_prediction_engine import OpponentPredictionEngine
from zye_realtime_tactical.opponent.opponent_sequence_buffer import OpponentSequenceBuffer
from zye_realtime_tactical.opponent.pattern_ranking_engine import PatternRankingEngine
from zye_realtime_tactical.opponent.prediction_evidence_guard import PredictionEvidenceGuard
from zye_realtime_tactical.opponent.second_order_markov import SecondOrderMarkov
from zye_realtime_tactical.opponent.trigram_pattern_detector import TrigramPatternDetector
import realtime_tactical_mcp


class TestDay36MarkovOpponentIntelligence(unittest.TestCase):
    def setUp(self) -> None:
        OpponentBufferManager.reset_instance()
        self.engine = OpponentPredictionEngine()

    def tearDown(self) -> None:
        OpponentBufferManager.reset_instance()

    def test_01_insufficient_evidence_guard(self) -> None:
        """Test 1: Actions < 6 strictly return INSUFFICIENT_DATA."""
        for count in range(1, 6):
            actions = ["punch"] * count
            res = self.engine.predict_opponent_attack(
                opponent_id=f"guard_test_{count}",
                observed_actions=actions,
            )
            self.assertEqual(res.status, "INSUFFICIENT_DATA")
            self.assertEqual(res.total_observed_actions, count)
            self.assertEqual(len(res.next_attack_probabilities), 0)

    def test_02_first_order_markov_probabilities(self) -> None:
        """Test 2: First-order Markov transition probabilities reflect exact observed counts."""
        # Sequence: A -> B -> A -> B -> A -> C (length 6)
        # From 'a': followed by 'b' (2 times) and 'c' (1 time). Total = 3.
        # P(b|a) = 2/3 = 66.67%, P(c|a) = 1/3 = 33.33%
        seq = ["a", "b", "a", "b", "a", "c"]
        matrix = FirstOrderMarkov.build_transition_matrix(seq)
        self.assertEqual(matrix["a"]["b"], 2)
        self.assertEqual(matrix["a"]["c"], 1)

        counts, total = FirstOrderMarkov.get_transitions_for_action(seq, "a")
        self.assertEqual(total, 3)
        preds = NextActionPredictor.predict_top_next_actions(counts, total)
        self.assertEqual(len(preds), 2)
        self.assertEqual(preds[0].predicted_action, "b")
        self.assertAlmostEqual(preds[0].probability_pct, 66.67, places=2)
        self.assertEqual(preds[1].predicted_action, "c")
        self.assertAlmostEqual(preds[1].probability_pct, 33.33, places=2)

    def test_03_second_order_markov_probabilities(self) -> None:
        """Test 3: Second-order Markov transition probabilities reflect exact pair transitions."""
        # Sequence: (guard, dodge) -> attack (twice), (guard, dodge) -> jump (once)
        seq = [
            "guard", "dodge", "attack",
            "guard", "dodge", "attack",
            "guard", "dodge", "jump",
        ]
        matrix = SecondOrderMarkov.build_transition_matrix(seq)
        pair = ("guard", "dodge")
        self.assertIn(pair, matrix)
        self.assertEqual(matrix[pair]["attack"], 2)
        self.assertEqual(matrix[pair]["jump"], 1)

        counts, total = SecondOrderMarkov.get_transitions_for_pair(seq, pair)
        self.assertEqual(total, 3)
        preds = NextActionPredictor.predict_top_next_actions(counts, total)
        self.assertEqual(preds[0].predicted_action, "attack")
        self.assertAlmostEqual(preds[0].probability_pct, 66.67, places=2)

    def test_04_markov_context_selector_preference(self) -> None:
        """Test 4: Selector prefers 2nd-order context when outgoing transitions >= 2."""
        # Repeated pattern where ("guard", "dodge") is followed by "attack" twice
        seq = ["guard", "dodge", "attack", "guard", "dodge", "attack", "guard", "dodge"]
        res = self.engine.predict_opponent_attack(
            opponent_id="boss_selector_pref",
            observed_actions=seq,
        )
        self.assertEqual(res.status, "PREDICTION_AVAILABLE")
        self.assertEqual(res.prediction_basis, "2nd-Order Sequence Context")
        self.assertTrue(len(res.next_attack_probabilities) > 0)
        self.assertEqual(res.next_attack_probabilities[0].predicted_action, "attack")
        self.assertEqual(res.next_attack_probabilities[0].probability_pct, 100.0)

    def test_05_markov_context_selector_fallback(self) -> None:
        """Test 5: Selector falls back to 1st-order when 2nd-order support is < 2."""
        # "jump" followed by "dodge" only once, but "dodge" followed by "attack" multiple times
        seq = [
            "guard", "dodge", "attack",
            "guard", "dodge", "attack",
            "jump", "dodge",
        ]
        res = self.engine.predict_opponent_attack(
            opponent_id="boss_fallback",
            observed_actions=seq,
        )
        self.assertEqual(res.status, "PREDICTION_AVAILABLE")
        self.assertEqual(res.prediction_basis, "1st-Order Transition Context")
        self.assertTrue(len(res.next_attack_probabilities) > 0)
        self.assertEqual(res.next_attack_probabilities[0].predicted_action, "attack")

    def test_06_no_repeat_transition_found(self) -> None:
        """Test 6: Returns NO_REPEAT_TRANSITION_FOUND when current action was never followed by anything."""
        # 'teleport' only appears as the final action and was never previously observed
        seq = ["guard", "dodge", "attack", "guard", "dodge", "attack", "teleport"]
        res = self.engine.predict_opponent_attack(
            opponent_id="boss_no_repeat",
            observed_actions=seq,
        )
        self.assertEqual(res.status, "NO_REPEAT_TRANSITION_FOUND")
        self.assertEqual(res.prediction_basis, "NO_REPEAT_TRANSITION_FOUND")
        self.assertEqual(len(res.next_attack_probabilities), 0)

    def test_07_zero_fabrication_strictly_empirical(self) -> None:
        """Test 7: Predictions never contain actions not actually observed after context."""
        seq = ["light_hit", "kick", "light_hit", "kick", "light_hit", "punch", "light_hit"]
        res = self.engine.predict_opponent_attack(
            opponent_id="boss_zero_fab",
            observed_actions=seq,
        )
        self.assertEqual(res.status, "PREDICTION_AVAILABLE")
        predicted_actions = {p.predicted_action for p in res.next_attack_probabilities}
        # Only 'kick' and 'punch' followed 'light_hit'
        self.assertEqual(predicted_actions, {"kick", "punch"})
        self.assertNotIn("laser_beam", predicted_actions)

    def test_08_probability_non_renormalization(self) -> None:
        """Test 8: Top 3 candidate probabilities must NOT be artificially renormalized to 100%."""
        # After context 'x', 4 different actions occur: a(4), b(2), c(2), d(2). Total = 10.
        # Top 3 are a (40%), b (20%), c (20%). Sum = 80%.
        # A flawed engine would renormalize 40/80=50%, 20/80=25%, 20/80=25%.
        # Zero-fabrication requires 40.0%, 20.0%, 20.0%.
        trans = {"a": 4, "b": 2, "c": 2, "d": 2}
        preds = NextActionPredictor.predict_top_next_actions(trans, total_transitions=10, max_candidates=3)
        self.assertEqual(len(preds), 3)
        self.assertEqual(preds[0].probability_pct, 40.0)
        self.assertEqual(preds[1].probability_pct, 20.0)
        self.assertEqual(preds[2].probability_pct, 20.0)
        total_sum = sum(p.probability_pct for p in preds)
        self.assertEqual(total_sum, 80.0)

    def test_09_bigram_tactical_sequence_detection(self) -> None:
        """Test 9: Bigrams occurring >= 2 times are detected."""
        actions = ["guard", "dodge", "attack", "guard", "dodge", "jump"]
        bigrams = BigramPatternDetector.detect(actions)
        sequences = {b.sequence: b.count for b in bigrams}
        self.assertIn("guard -> dodge", sequences)
        self.assertEqual(sequences["guard -> dodge"], 2)
        # "attack -> guard" occurs only once, should not be included
        self.assertNotIn("attack -> guard", sequences)

    def test_10_trigram_tactical_sequence_detection(self) -> None:
        """Test 10: Trigrams occurring >= 2 times are detected."""
        actions = ["a", "b", "c", "d", "a", "b", "c", "e"]
        trigrams = TrigramPatternDetector.detect(actions)
        sequences = {t.sequence: t.count for t in trigrams}
        self.assertIn("a -> b -> c", sequences)
        self.assertEqual(sequences["a -> b -> c"], 2)
        self.assertNotIn("b -> c -> d", sequences)

    def test_11_pattern_ranking_engine(self) -> None:
        """Test 11: Top 4 patterns ranked by frequency with alphabetical tie-breaking."""
        bigrams = BigramPatternDetector.detect(["a", "b", "a", "b", "a", "b"])  # "a -> b": 3, "b -> a": 2
        trigrams = TrigramPatternDetector.detect(["a", "b", "a", "b", "a", "b"])  # "a -> b -> a": 2, "b -> a -> b": 2
        ranked = PatternRankingEngine.rank(bigrams, trigrams, top_n=4)
        self.assertLessEqual(len(ranked), 4)
        self.assertEqual(ranked[0].sequence, "a -> b")
        self.assertEqual(ranked[0].count, 3)

    def test_12_inter_action_timing_analysis(self) -> None:
        """Test 12: Inter-action timing calculates expected interval within [0.05, 60.0]s filter."""
        # Jitter < 0.05s and pauses > 60s should be excluded
        ts = [10.0, 10.01, 10.5, 11.0, 100.0, 100.6]
        # Intervals:
        # 10.01 - 10.00 = 0.01 (FILTERED OUT, < 0.05)
        # 10.50 - 10.01 = 0.49 (VALID)
        # 11.00 - 10.50 = 0.50 (VALID)
        # 100.0 - 11.00 = 89.0 (FILTERED OUT, > 60.0)
        # 100.6 - 100.0 = 0.60 (VALID)
        # Valid: [0.49, 0.50, 0.60] -> mean = 0.53
        timing = InterActionTimingAnalyzer.analyze(ts)
        self.assertEqual(timing["timing_basis"], "AVERAGE_VALID_INTERVALS")
        self.assertEqual(timing["valid_interval_count"], 3)
        self.assertAlmostEqual(timing["expected_next_attack_in_sec"], 0.53, places=2)

    def test_13_bounded_ring_buffer_rollover(self) -> None:
        """Test 13: Circular buffer respects max capacity and tracks overwritten actions."""
        buf = OpponentSequenceBuffer(opponent_id="boss_rollover", capacity=10)
        for i in range(15):
            buf.append(OpponentAction(action=f"action_{i}", timestamp=10.0 + i))

        self.assertEqual(buf.size, 10)
        status = buf.get_status()
        self.assertEqual(status.overwritten_actions, 5)
        self.assertEqual(status.total_actions_observed, 15)
        actions = buf.get_all_actions()
        self.assertEqual(actions[0], "action_5")
        self.assertEqual(actions[-1], "action_14")

    def test_14_multi_opponent_isolation(self) -> None:
        """Test 14: Multiple opponents tracked in RAM maintain strictly independent state."""
        res_a = self.engine.predict_opponent_attack(
            opponent_id="opponent_alpha",
            observed_actions=["alpha_punch", "alpha_kick"] * 4,
        )
        res_b = self.engine.predict_opponent_attack(
            opponent_id="opponent_beta",
            observed_actions=["beta_slash", "beta_thrust"] * 4,
        )

        self.assertEqual(res_a.opponent_id, "opponent_alpha")
        self.assertEqual(res_b.opponent_id, "opponent_beta")
        # Alpha should have no beta actions
        alpha_preds = [p.predicted_action for p in res_a.next_attack_probabilities]
        beta_preds = [p.predicted_action for p in res_b.next_attack_probabilities]
        for act in alpha_preds:
            self.assertTrue(act.startswith("alpha_"))
        for act in beta_preds:
            self.assertTrue(act.startswith("beta_"))

    def test_15_fastmcp_tools_execution(self) -> None:
        """Test 15: All 5 Day 36 FastMCP tools execute successfully."""
        # Tool 06: predict_opponent_attack
        p_res = realtime_tactical_mcp.predict_opponent_attack(
            opponent_id="mcp_test_boss",
            observed_actions=["guard", "dodge", "attack", "guard", "dodge", "attack"],
        )
        self.assertIn("status", p_res)
        self.assertEqual(p_res["status"], "PREDICTION_AVAILABLE")

        # Tool 07: get_opponent_sequence_status
        s_res = realtime_tactical_mcp.get_opponent_sequence_status(opponent_id="mcp_test_boss")
        self.assertEqual(s_res["status"], "SUCCESS")
        self.assertEqual(s_res["opponent_status"]["current_action_count"], 6)

        # Tool 08: list_tracked_opponents
        l_res = realtime_tactical_mcp.list_tracked_opponents()
        self.assertEqual(l_res["status"], "SUCCESS")
        self.assertGreaterEqual(l_res["active_opponent_count"], 1)

        # Tool 10: get_opponent_pattern_summary
        sum_res = realtime_tactical_mcp.get_opponent_pattern_summary(opponent_id="mcp_test_boss")
        self.assertEqual(sum_res["status"], "SUCCESS")
        self.assertEqual(sum_res["total_actions"], 6)

        # Tool 09: reset_opponent_sequence
        r_res = realtime_tactical_mcp.reset_opponent_sequence(opponent_id="mcp_test_boss")
        self.assertEqual(r_res["status"], "SUCCESS")
        self.assertEqual(r_res["action"], "SEQUENCE_RESET_COMPLETED")


if __name__ == "__main__":
    unittest.main()

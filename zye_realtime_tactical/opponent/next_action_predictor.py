"""
Next-Action Predictor.
Calculates empirical next-action probabilities from selected Markov transitions,
sorts by likelihood, and returns the top 3 candidates without artificial renormalization.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Union

from zye_realtime_tactical.opponent.opponent_prediction_schema import NextActionProbability


class NextActionPredictor:
    """Calculates empirical probabilities for top candidate next actions."""

    @classmethod
    def predict_next_actions(
        cls,
        transitions: Union[Counter[str], Dict[str, int]],
        context_observation_count: int,
        top_k: int = 3,
    ) -> List[NextActionProbability]:
        """Convenience alias for predict_top_next_actions."""
        counts = Counter(transitions) if isinstance(transitions, dict) else transitions
        return cls.predict_top_next_actions(
            transition_counts=counts,
            total_transitions=context_observation_count,
            max_candidates=top_k,
        )

    @classmethod
    def predict_top_next_actions(
        cls,
        transition_counts: Counter[str],
        total_transitions: int,
        max_candidates: int = 3,
    ) -> List[NextActionProbability]:
        """
        Computes probabilities: P(action) = count / total_transitions * 100.0
        Sorts descending by observed count / probability.
        Returns up to max_candidates without artificial renormalization.
        """
        if total_transitions <= 0 or not transition_counts:
            return []

        # Sort actions by hit count descending, then alphabetically for deterministic tie-breaking
        sorted_candidates = sorted(
            transition_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )

        results: List[NextActionProbability] = []
        for action_name, hit_count in sorted_candidates[:max_candidates]:
            pct = round((hit_count / total_transitions) * 100.0, 2)
            results.append(
                NextActionProbability(
                    predicted_action=action_name,
                    probability_pct=pct,
                    sample_hits=hit_count,
                )
            )

        return results

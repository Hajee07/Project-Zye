"""
Intelligent Markov Context Selector.
Selects second-order model if context has at least 2 observed outgoing transitions;
otherwise falls back to first-order model if valid transition exists.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Tuple, Union

from zye_realtime_tactical.opponent.first_order_markov import FirstOrderMarkov
from zye_realtime_tactical.opponent.second_order_markov import SecondOrderMarkov


class MarkovContextSelector:
    """Selects the best-supported empirical Markov context."""

    DEFAULT_MIN_SECOND_ORDER_SUPPORT: int = 2

    @classmethod
    def select_context(
        cls,
        current_state: Any,
        first_order_matrix: Dict[str, Any],
        second_order_matrix: Dict[Tuple[str, str], Any],
        min_second_order_support: int = DEFAULT_MIN_SECOND_ORDER_SUPPORT,
    ) -> Dict[str, Any]:
        """
        Selects between 2nd-order context and 1st-order context based on current_state
        and pre-computed transition matrices.
        """
        # Parse current state (last_action, last_two_actions)
        last_action = None
        last_two = None

        if isinstance(current_state, tuple):
            if len(current_state) == 2 and isinstance(current_state[1], tuple):
                last_action = current_state[0]
                last_two = current_state[1]
            elif len(current_state) == 2 and isinstance(current_state[0], str) and isinstance(current_state[1], str):
                last_action = current_state[1]
                last_two = current_state
            elif len(current_state) == 1:
                last_action = current_state[0]
        elif isinstance(current_state, str):
            last_action = current_state

        # Check 2nd-order context
        if last_two and last_two in second_order_matrix:
            trans_2 = second_order_matrix[last_two]
            count_2 = sum(trans_2.values()) if hasattr(trans_2, "values") else 0
            if count_2 >= min_second_order_support:
                return {
                    "status": "PREDICTION_AVAILABLE",
                    "basis": "2nd-Order Sequence Context",
                    "transitions": dict(trans_2),
                    "context_total": count_2,
                    "context_key": last_two,
                }

        # Fallback to 1st-order context
        if last_action and last_action in first_order_matrix:
            trans_1 = first_order_matrix[last_action]
            count_1 = sum(trans_1.values()) if hasattr(trans_1, "values") else 0
            if count_1 >= 1:
                return {
                    "status": "PREDICTION_AVAILABLE",
                    "basis": "1st-Order Transition Context",
                    "transitions": dict(trans_1),
                    "context_total": count_1,
                    "context_key": last_action,
                }

        return {
            "status": "NO_REPEAT_TRANSITION_FOUND",
            "basis": "NO_REPEAT_TRANSITION_FOUND",
            "transitions": {},
            "context_total": 0,
            "context_key": None,
        }

    @classmethod
    def select_prediction_context(
        cls,
        actions: List[str],
        min_second_order_support: int = DEFAULT_MIN_SECOND_ORDER_SUPPORT,
    ) -> Dict[str, Any]:
        """
        Selects Markov context directly from full actions sequence.
        """
        n = len(actions)
        if n < 2:
            return {
                "prediction_basis": "NO_REPEAT_TRANSITION_FOUND",
                "context_counts": Counter(),
                "total_context_transitions": 0,
                "context_key": None,
            }

        # Step 1: Evaluate Second-Order Markov context (latest two actions)
        if n >= 3:
            current_pair = (actions[-2], actions[-1])
            pair_counts, pair_total = SecondOrderMarkov.get_transitions_for_pair(actions, current_pair)

            if pair_total >= min_second_order_support:
                return {
                    "prediction_basis": "2nd-Order Sequence Context",
                    "context_counts": pair_counts,
                    "total_context_transitions": pair_total,
                    "context_key": current_pair,
                }

        # Step 2: Fallback to First-Order Markov context (latest single action)
        current_action = actions[-1]
        action_counts, action_total = FirstOrderMarkov.get_transitions_for_action(actions, current_action)

        if action_total > 0:
            return {
                "prediction_basis": "1st-Order Transition Context",
                "context_counts": action_counts,
                "total_context_transitions": action_total,
                "context_key": current_action,
            }

        # Step 3: No repeat transition found
        return {
            "prediction_basis": "NO_REPEAT_TRANSITION_FOUND",
            "context_counts": Counter(),
            "total_context_transitions": 0,
            "context_key": None,
        }

"""
Second-Order Markov Chain Transition Engine.
Builds pair transition matrix P(X_{t+1} = k | X_{t-1} = i, X_t = j) = N(i,j -> k) / sum_m N(i,j -> m)
using two-action historical contexts.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, Tuple


class SecondOrderMarkov:
    """Builds empirical transition counts for two-action sequential contexts."""

    @classmethod
    def build_transition_counts(cls, actions: List[str]) -> Dict[Tuple[str, str], Counter[str]]:
        """
        Builds mapping from pair (i, j) to Counter of observed next actions k.
        """
        transitions: Dict[Tuple[str, str], Counter[str]] = defaultdict(Counter)
        n = len(actions)
        for i in range(n - 2):
            pair = (actions[i], actions[i + 1])
            next_act = actions[i + 2]
            transitions[pair][next_act] += 1

        return transitions

    @classmethod
    def build_transition_matrix(cls, actions: List[str]) -> Dict[Tuple[str, str], Dict[str, int]]:
        """Builds plain dictionary transition matrix {(act_i, act_j): {next_action: count}}."""
        counts = cls.build_transition_counts(actions)
        return {k: dict(v) for k, v in counts.items()}

    @classmethod
    def get_transitions_for_pair(
        cls,
        actions: List[str],
        pair: Tuple[str, str],
    ) -> Tuple[Counter[str], int]:
        """
        Returns observed next-action Counter and total transitions from pair (i, j).
        """
        transitions = cls.build_transition_counts(actions)
        counts = transitions.get(pair, Counter())
        total = sum(counts.values())
        return counts, total

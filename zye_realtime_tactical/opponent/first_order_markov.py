"""
First-Order Markov Chain Transition Engine.
Builds transition matrix P(X_{t+1} = j | X_t = i) = N(i -> j) / sum_k N(i -> k)
from actual observed action sequences.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, Tuple


class FirstOrderMarkov:
    """Builds empirical transition counts for single-action contexts."""

    @classmethod
    def build_transition_counts(cls, actions: List[str]) -> Dict[str, Counter[str]]:
        """
        Builds mapping from action i to Counter of observed next actions j.
        """
        transitions: Dict[str, Counter[str]] = defaultdict(Counter)
        n = len(actions)
        for i in range(n - 1):
            curr_act = actions[i]
            next_act = actions[i + 1]
            transitions[curr_act][next_act] += 1

        return transitions

    @classmethod
    def build_transition_matrix(cls, actions: List[str]) -> Dict[str, Dict[str, int]]:
        """Builds plain dictionary transition matrix {curr_action: {next_action: count}}."""
        counts = cls.build_transition_counts(actions)
        return {k: dict(v) for k, v in counts.items()}

    @classmethod
    def get_transitions_for_action(
        cls,
        actions: List[str],
        current_action: str,
    ) -> Tuple[Counter[str], int]:
        """
        Returns observed next-action Counter and total transitions from current_action.
        """
        transitions = cls.build_transition_counts(actions)
        counts = transitions.get(current_action, Counter())
        total = sum(counts.values())
        return counts, total

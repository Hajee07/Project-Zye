"""
Fighting Pattern Ranking Engine (Day 36).
Merges bigrams and trigrams, sorts by observed recurrence descending,
and returns the top 4 fighting patterns with deterministic tie-breaking.
"""

from __future__ import annotations

from typing import List

from zye_realtime_tactical.opponent.opponent_prediction_schema import FightingPattern


class PatternRankingEngine:
    """Ranks and selects top fighting patterns."""

    @staticmethod
    def rank(
        bigrams: List[FightingPattern],
        trigrams: List[FightingPattern],
        top_n: int = 4,
    ) -> List[FightingPattern]:
        """
        Combines bigrams and trigrams, sorting by:
        1. Recurrence count descending
        2. Sequence string ascending (alphabetical tie-breaker)
        Returns up to top_n patterns.
        """
        combined = list(bigrams) + list(trigrams)
        # Deterministic sort: higher count first, then alphabetical sequence
        combined.sort(key=lambda p: (-p.count, p.sequence))
        return combined[:top_n]

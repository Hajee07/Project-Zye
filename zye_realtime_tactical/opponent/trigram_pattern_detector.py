"""
Trigram Tactical Pattern Detector (Day 36).
Detects recurring 3-action combinations occurring at least twice.
Optimized for zero-lag high-throughput combat telemetry streams.
"""

from __future__ import annotations

from collections import Counter
from typing import List, Tuple

from zye_realtime_tactical.opponent.opponent_prediction_schema import FightingPattern, PatternType


class TrigramPatternDetector:
    """Detects adjacent three-action recurring sequences."""

    @staticmethod
    def detect(actions: List[str]) -> List[FightingPattern]:
        """
        Extracts all adjacent 3-action triplets and filters for frequency >= 2.
        Zero fabrication: returns strictly observed combinations.
        """
        n = len(actions)
        if n < 3:
            return []

        counts: Counter[Tuple[str, str, str]] = Counter()
        for i in range(n - 2):
            counts[(actions[i], actions[i + 1], actions[i + 2])] += 1

        patterns: List[FightingPattern] = []
        for (a, b, c), count in counts.items():
            if count >= 2:
                patterns.append(
                    FightingPattern(
                        pattern_type=PatternType.TRIGRAM,
                        sequence=f"{a} -> {b} -> {c}",
                        count=count,
                    )
                )

        return patterns

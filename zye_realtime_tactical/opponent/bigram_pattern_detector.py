"""
Bigram Tactical Pattern Detector (Day 36).
Detects recurring 2-action combinations occurring at least twice.
Optimized for zero-lag high-throughput combat telemetry streams.
"""

from __future__ import annotations

from collections import Counter
from typing import List, Tuple

from zye_realtime_tactical.opponent.opponent_prediction_schema import FightingPattern, PatternType


class BigramPatternDetector:
    """Detects adjacent two-action recurring sequences."""

    @staticmethod
    def detect(actions: List[str]) -> List[FightingPattern]:
        """
        Extracts all adjacent 2-action pairs and filters for frequency >= 2.
        Zero fabrication: returns strictly observed combinations.
        """
        n = len(actions)
        if n < 2:
            return []

        counts: Counter[Tuple[str, str]] = Counter()
        for i in range(n - 1):
            counts[(actions[i], actions[i + 1])] += 1

        patterns: List[FightingPattern] = []
        for (a, b), count in counts.items():
            if count >= 2:
                patterns.append(
                    FightingPattern(
                        pattern_type=PatternType.BIGRAM,
                        sequence=f"{a} -> {b}",
                        count=count,
                    )
                )

        return patterns

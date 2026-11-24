"""Multi-Solution Weighted Decision Matrix — Zye Day 11/13 Compatibility."""

from zye_intelligence.decision_matrix import (
    PRIORITY_WEIGHTS,
    DEFAULT_SAFETY_THRESHOLD,
    ZyeDecisionMatrix,
    compare_and_decide_solutions,
)

# Alias for Day 11 tests expecting SAFETY_THRESHOLD
SAFETY_THRESHOLD = DEFAULT_SAFETY_THRESHOLD

__all__ = [
    "PRIORITY_WEIGHTS",
    "SAFETY_THRESHOLD",
    "DEFAULT_SAFETY_THRESHOLD",
    "ZyeDecisionMatrix",
    "compare_and_decide_solutions",
]

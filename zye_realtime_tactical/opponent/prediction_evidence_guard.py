"""
Prediction Evidence Guard.
Enforces the mandatory minimum of at least 6 observed actions before allowing predictions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Union


class PredictionEvidenceGuard:
    """Zero-fabrication evidence check preventing premature or guessed predictions."""

    MINIMUM_OBSERVATIONS: int = 6

    @classmethod
    def check_sufficient_evidence(cls, count_or_actions: Union[int, List[Any]]) -> bool:
        """Returns True if at least 6 observed actions are present."""
        if isinstance(count_or_actions, int):
            return count_or_actions >= cls.MINIMUM_OBSERVATIONS
        if isinstance(count_or_actions, list):
            return len(count_or_actions) >= cls.MINIMUM_OBSERVATIONS
        return False

    @classmethod
    def validate_prediction_evidence(cls, actions: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """
        Validates whether sufficient observations exist for statistical prediction.
        Returns:
            (is_sufficient, details_dict)
        """
        count = len(actions)
        if count < cls.MINIMUM_OBSERVATIONS:
            return False, {
                "status": "INSUFFICIENT_DATA",
                "observed_count": count,
                "minimum_required": cls.MINIMUM_OBSERVATIONS,
                "message": f"Need at least {cls.MINIMUM_OBSERVATIONS} observed actions to detect patterns without guessing (observed {count}).",
            }

        return True, {
            "status": "EVIDENCE_SUFFICIENT",
            "observed_count": count,
            "minimum_required": cls.MINIMUM_OBSERVATIONS,
        }

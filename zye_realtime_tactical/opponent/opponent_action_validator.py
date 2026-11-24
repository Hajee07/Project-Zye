"""
Opponent Action Validator.
Enforces character sets, length bounds, normalization hygiene, and atomic batch integrity.
"""

from __future__ import annotations

import re
from typing import Any, List, Tuple

OPPONENT_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.:]{1,64}$")
ACTION_LABEL_REGEX = re.compile(r"^[a-zA-Z0-9_\-\. ]{1,64}$")
MAX_ACTION_BATCH_SIZE = 1000


class OpponentActionValidator:
    """Validates action labels and opponent identifiers before sequence buffering."""

    @classmethod
    def normalize_action_label(cls, raw: str) -> str:
        """Standardizes action label using lowercase stripping."""
        if not raw or not isinstance(raw, str):
            return ""
        return raw.strip().casefold()

    @classmethod
    def check_opponent_id(cls, opponent_id: str) -> Tuple[bool, str]:
        """Validates opponent ID format and length, returning boolean and message."""
        if not opponent_id or not isinstance(opponent_id, str):
            return False, "Opponent ID must be a non-empty string."

        trimmed = opponent_id.strip()
        if len(trimmed) > 64:
            return False, "Opponent ID exceeds maximum length of 64 characters."

        if not OPPONENT_ID_REGEX.match(trimmed):
            return False, "Opponent ID contains invalid characters. Only alphanumeric, underscores, hyphens, and colons are permitted."

        return True, "Valid"

    @classmethod
    def validate_opponent_id(cls, opponent_id: str) -> str:
        """
        Validates opponent ID format and length.
        Returns cleaned ID string if valid, raises ValueError if invalid.
        """
        is_valid, msg = cls.check_opponent_id(opponent_id)
        if not is_valid:
            raise ValueError(msg)
        return opponent_id.strip()

    @classmethod
    def validate_actions(
        cls,
        actions: List[Any],
        max_batch_size: int = MAX_ACTION_BATCH_SIZE,
    ) -> List[str]:
        """
        Validates and standardizes a list of action strings.
        Raises ValueError if empty, exceeding max_batch_size, or containing invalid items.
        """
        if not actions or not isinstance(actions, list):
            raise ValueError("Actions must be a non-empty list of strings.")

        if len(actions) > max_batch_size:
            raise ValueError(f"Action batch size {len(actions)} exceeds maximum allowed of {max_batch_size}.")

        cleaned: List[str] = []
        for i, act in enumerate(actions):
            if not isinstance(act, str):
                raise ValueError(f"Action at index {i} must be a string, got {type(act).__name__}.")
            norm = cls.normalize_action_label(act)
            if not norm:
                raise ValueError(f"Action at index {i} is empty after trimming.")
            if len(norm) > 64:
                raise ValueError(f"Action at index {i} exceeds 64 characters.")
            cleaned.append(norm)

        return cleaned

    @classmethod
    def validate_action_batch(
        cls,
        actions: List[Any],
        max_batch_size: int = MAX_ACTION_BATCH_SIZE,
    ) -> Tuple[bool, str, List[str], List[str]]:
        """
        Atomically validates an action batch.
        Returns:
            (is_valid, error_msg, raw_list, normalized_list)
        """
        try:
            cleaned = cls.validate_actions(actions, max_batch_size=max_batch_size)
            raw_list = [str(a) for a in actions]
            return True, "Valid", raw_list, cleaned
        except Exception as exc:
            return False, str(exc), [], []

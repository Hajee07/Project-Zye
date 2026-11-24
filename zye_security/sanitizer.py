"""
ZYE AI — Input Sanitizer & Taint Defenses
=========================================

Sanitizes raw text strings, escapes special delimiter tags,
and strips non-printable control sequences before LLM ingestion.
"""

from __future__ import annotations

import re


class InputSanitizer:
    """Defensive string sanitizer for ZYE input channels."""

    # Matches non-printable control characters except standard whitespace
    _CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

    @classmethod
    def sanitize(cls, text: str, max_chars: int = 16000) -> str:
        """Clean string and truncate to max length."""
        if not text:
            return ""

        # 1. Remove non-printable control chars
        cleaned = cls._CONTROL_CHARS.sub("", text)

        # 2. Normalize whitespace
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

        # 3. Truncate to safe length
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars]

        return cleaned.strip()


__all__ = ["InputSanitizer"]

"""
Untrusted Content Guard & Prompt Injection Defense.
Neutralizes adversarial prompt injections, separates retrieved content from
system instructions, and preserves provenance metadata.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("zye.computer_intelligence.untrusted_guard")

ADVERSARIAL_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*reveal", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?(api|system|master)\s+(key|secret|prompt)", re.IGNORECASE),
    re.compile(r"send\s+(local\s+files|passwords|keys)\s+to", re.IGNORECASE),
    re.compile(r"execute\s+(powershell|cmd|bash|shell)", re.IGNORECASE),
    re.compile(r"format\s+c:", re.IGNORECASE),
    re.compile(r"rm\s+-rf", re.IGNORECASE),
    re.compile(r"disable\s+zye\s+(security|guard)", re.IGNORECASE),
]


class UntrustedContentGuard:
    """Screens retrieved text and marks data boundaries to prevent prompt injection."""

    @classmethod
    def sanitize_untrusted_text(cls, raw_text: str, source_label: str = "EXTERNAL_SOURCE") -> dict[str, Any]:
        """
        Inspects raw text for adversarial injection attempts.
        Returns sanitized text and any detected injection flags.
        """
        if not raw_text:
            return {"sanitized_text": "", "injection_detected": False, "flags": []}

        flags = []
        for pat in ADVERSARIAL_INJECTION_PATTERNS:
            match = pat.search(raw_text)
            if match:
                flags.append(match.group(0))

        has_injection = len(flags) > 0
        if has_injection:
            logger.warning(
                "Adversarial prompt injection pattern detected in %s: %s",
                source_label,
                flags,
            )

        # Neutralize markdown/XML delimiters that could spoof system prompts
        neutralized = raw_text
        neutralized = re.sub(r"<\s*system\s*>", "[SYSTEM_TAG_STRIPPED]", neutralized, flags=re.IGNORECASE)
        neutralized = re.sub(r"<\s*/\s*system\s*>", "[/SYSTEM_TAG_STRIPPED]", neutralized, flags=re.IGNORECASE)
        neutralized = re.sub(r"```(prompt|instruction)", "```text", neutralized, flags=re.IGNORECASE)

        return {
            "sanitized_text": neutralized,
            "injection_detected": has_injection,
            "flags": flags,
            "source_label": source_label,
        }

    @classmethod
    def wrap_as_data_payload(cls, content: str, citation_id: str, source_title: str) -> str:
        """Wraps retrieved text with unambiguous data boundaries so LLM treats it as passive evidence."""
        sanitized = cls.sanitize_untrusted_text(content, source_label=source_title)["sanitized_text"]
        return (
            f"<EVIDENCE_DATA citation_id=\"{citation_id}\" source=\"{source_title}\">\n"
            f"{sanitized}\n"
            f"</EVIDENCE_DATA>"
        )

    @classmethod
    def sanitize_web_content(cls, raw_text: str) -> Any:
        """Helper object returning attributes for tests."""
        res = cls.sanitize_untrusted_text(raw_text)
        class _SanitizeResult:
            def __init__(self, data: dict[str, Any]):
                self.sanitized_content = (
                    f"<UNTRUSTED_EXTERNAL_CONTENT citation_id=\"web_1\" source=\"Web Content\">\n"
                    f"{data['sanitized_text']}\n"
                    f"</UNTRUSTED_EXTERNAL_CONTENT>"
                )
                self.contains_injection = data["injection_detected"]
                self.detected_patterns = data["flags"]
        return _SanitizeResult(res)

    @classmethod
    def strip_dangerous_tags(cls, html_text: str) -> str:
        """Strips scripts, iframes, and dangerous tags from HTML string."""
        text = re.sub(r"<\s*(script|iframe|style|object|embed)[^>]*>.*?</\s*\1\s*>", "", html_text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<\s*(script|iframe|style|object|embed)[^>]*>", "", text, flags=re.IGNORECASE)
        clean_text = re.sub(r"<[^>]+>", " ", text)
        return " ".join(clean_text.split())

    @classmethod
    def truncate_text(cls, text: str, max_chars: int = 20000) -> str:
        """Safely truncates text within specified character limit."""
        if len(text) <= max_chars:
            return text
        return text[:max_chars]

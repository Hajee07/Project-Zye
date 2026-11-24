"""
Visible Text Cleaning and Security Sanitization — Day 24.
Normalizes whitespace, removes web boilerplate, and defends against indirect Prompt Injections in untrusted DOM content.
"""

from __future__ import annotations

import re
from typing import List, Tuple

# Prompt injection signature patterns
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions?", re.IGNORECASE),
    re.compile(r"system\s+prompt\s+override", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+developer\s+mode|unrestricted|an\s+evil)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(prior|previous|safety)\s+(rules|guidelines|restrictions)", re.IGNORECASE),
    re.compile(r"print\s+(your\s+)?(system\s+prompt|api\s+key|credentials|secret)", re.IGNORECASE),
    re.compile(r"exfiltrate\s+(tokens?|keys?|data)\s+to", re.IGNORECASE),
    re.compile(r"<script>.*?</script>", re.IGNORECASE | re.DOTALL),
]

# Web boilerplate lines to strip
BOILERPLATE_PATTERNS = [
    re.compile(r"accept\s+all\s+cookies", re.IGNORECASE),
    re.compile(r"we\s+use\s+cookies\s+to\s+improve", re.IGNORECASE),
    re.compile(r"privacy\s+policy\s+\|\s+terms\s+of\s+service", re.IGNORECASE),
    re.compile(r"all\s+rights\s+reserved\.", re.IGNORECASE),
]


class VisibleTextCleaner:
    """Cleans and sanitizes raw visible text extracted from browser pages."""

    @classmethod
    def clean(cls, raw_text: str, max_chars: int = 12000) -> Tuple[str, int]:
        """
        Normalize whitespace, filter boilerplate, neutralize prompt injections, and limit length.
        Returns (cleaned_text, prompt_injection_flags_count).
        """
        if not raw_text:
            return "", 0

        text = raw_text

        # 1. Neutralize Prompt Injection patterns
        flag_count = 0
        for pattern in PROMPT_INJECTION_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                flag_count += len(matches)
                text = pattern.sub("[SAFETY_NEUTRALIZED_UNTRUSTED_CONTENT]", text)

        # 2. Normalize whitespace
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # 3. Filter common boilerplate lines
        lines: List[str] = []
        for line in text.split("\n"):
            line_str = line.strip()
            if not line_str:
                lines.append("")
                continue

            # Skip boilerplate lines
            if any(bp.search(line_str) for bp in BOILERPLATE_PATTERNS):
                continue

            lines.append(line_str)

        cleaned = "\n".join(lines).strip()

        # 4. Enforce character boundary
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars] + f"\n\n[Content truncated at {max_chars} characters for AI processing]"

        return cleaned, flag_count

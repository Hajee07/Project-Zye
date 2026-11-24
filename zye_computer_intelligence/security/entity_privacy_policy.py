"""
Entity Data Privacy & Credential Redaction Policy.
Protects against sensitive credential leakage in entity profiles and shields
document parsing from adversarial prompt injection attacks.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from zye_computer_intelligence.security.untrusted_content_guard import UntrustedContentGuard

logger = logging.getLogger("zye.computer_intelligence.entity_linking.privacy")

# Patterns for credentials that should never be stored as entities
CREDENTIAL_PATTERNS = [
    re.compile(r"(api[_-]?key|secret|token|password|auth|jwt)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?", re.IGNORECASE),
    re.compile(r"AIza[0-9A-Za-z-_]{10,40}"), # Google API Key
    re.compile(r"sk-[a-zA-Z0-9]{15,}"),     # OpenAI / standard secret key format
    re.compile(r"ghp_[a-zA-Z0-9]{30,}"),    # GitHub Personal Access Token
    re.compile(r"(?i)\bbearer\s+[a-zA-Z0-9_\-\.]{6,}\b"), # Bearer token
]


class EntityPrivacyPolicy:
    """Enforces data boundary isolation, credential filtering, and prompt injection defense."""

    @classmethod
    def redact_sensitive_content(cls, raw_text: str) -> str:
        """
        Masks API keys, bearer tokens, and secrets in text before entity extraction.
        """
        if not raw_text:
            return ""

        text = raw_text
        # Specific Google API Key pattern
        text = re.sub(r"AIza[0-9A-Za-z-_]{10,40}", "[REDACTED_API_KEY]", text)
        # OpenAI keys
        text = re.sub(r"sk-[a-zA-Z0-9]{15,}", "[REDACTED_API_KEY]", text)
        # GitHub PATs
        text = re.sub(r"ghp_[a-zA-Z0-9]{30,}", "[REDACTED_TOKEN]", text)
        # Bearer token
        text = re.sub(r"(?i)\bbearer\s+[a-zA-Z0-9_\-\.]{6,}\b", "[REDACTED_BEARER_TOKEN]", text)

        for pat in CREDENTIAL_PATTERNS:
            text = pat.sub("[REDACTED_CREDENTIAL]", text)

        return text

    @classmethod
    def sanitize_entity_value(cls, raw_value: str) -> str:
        """Removes or masks secrets if accidentally captured in entity extraction."""
        return cls.redact_sensitive_content(raw_value).strip()

    @classmethod
    def is_credential_mention(cls, text: str) -> bool:
        """Returns True if the candidate mention resembles a raw secret or API key."""
        if not text or len(text) < 8:
            return False
        for pat in CREDENTIAL_PATTERNS:
            if pat.search(text):
                return True
        return False

    @classmethod
    def screen_document_content(cls, raw_text: str, source_label: str = "DOCUMENT") -> dict[str, Any]:
        """Screens extracted document text through UntrustedContentGuard for prompt injections."""
        return UntrustedContentGuard.sanitize_untrusted_text(raw_text, source_label=source_label)

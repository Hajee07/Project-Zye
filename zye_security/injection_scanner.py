"""
ZYE AI — Prompt Injection & Adversarial Payload Scanner
======================================================

Implements Section 26 of Master Engineering Specification.
Scans incoming text from user prompts, external tools, web searches, and documents
for prompt injection, jailbreaks, hidden override instructions, and system exploits.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from zye_core.event_bus import ZyeEventBus
from zye_core.types import ZyeEvent, ZyeEventType

logger = logging.getLogger("zye.security.injection_scanner")


class ThreatLevel(str, Enum):
    """Severity levels for detected security findings."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(slots=True)
class ScanFinding:
    """Security violation detected by the scanner."""

    pattern_name: str
    threat_level: ThreatLevel
    matched_text: str
    description: str


# Canonical prompt injection and command escape signatures
INJECTION_PATTERNS = [
    # System prompt override / jailbreaks
    (
        r"(?i)\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions?|prompts?|rules?)\b",
        "prompt_override",
        ThreatLevel.HIGH,
        "Attempt to override system prompt instructions",
    ),
    (
        r"(?i)\byou\s+are\s+now\s+(?:a\s+)?(?:different|new|unrestricted|DAN|jailbroken)\b",
        "identity_jailbreak",
        ThreatLevel.HIGH,
        "Attempt to change AI identity or remove safety boundaries",
    ),
    (
        r"(?i)\bdisregard\s+(?:all\s+)?(?:prior|safety|guardrail|ethical)\s+(?:rules?|guidelines?)\b",
        "guardrail_bypass",
        ThreatLevel.HIGH,
        "Attempt to bypass assistant safety guardrails",
    ),
    # Dangerous shell injection patterns
    (
        r"(?i)(?:;|\||&&)\s*(?:rm\s+-rf|del\s+/[fF]|format\s+[cC]:|powershell\s+-[eE]nc)\b",
        "destructive_command_injection",
        ThreatLevel.CRITICAL,
        "Destructive shell command execution payload detected",
    ),
    # Path traversal attempts
    (
        r"(?:\.\.[\\/]){2,}(?:windows|system32|etc|passwd)",
        "path_traversal",
        ThreatLevel.CRITICAL,
        "Directory path traversal targeting system directories",
    ),
    # Hidden instruction tags
    (
        r"(?i)<!--\s*(?:system|override|hidden|secret)\s*:",
        "comment_injection",
        ThreatLevel.MEDIUM,
        "Suspicious hidden comment injection",
    ),
]


class InjectionScanner:
    """
    Scans text payloads for adversarial prompt injections and jailbreaks.
    """

    def __init__(self, event_bus: Optional[ZyeEventBus] = None) -> None:
        self.event_bus = event_bus
        self._compiled_patterns = [
            (re.compile(pat), name, level, desc)
            for pat, name, level, desc in INJECTION_PATTERNS
        ]

    def scan(self, text: str) -> List[ScanFinding]:
        """Inspect text and return all findings."""
        if not text:
            return []

        findings: List[ScanFinding] = []
        for regex, name, level, desc in self._compiled_patterns:
            for match in regex.finditer(text):
                matched_snippet = match.group(0)[:100]
                finding = ScanFinding(
                    pattern_name=name,
                    threat_level=level,
                    matched_text=matched_snippet,
                    description=desc,
                )
                findings.append(finding)
                logger.warning(
                    "Security finding detected [%s / %s]: %s (%s)",
                    level.value,
                    name,
                    desc,
                    matched_snippet,
                )

                if level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL) and self.event_bus:
                    self.event_bus.publish_sync(
                        ZyeEvent(
                            event_type=ZyeEventType.SECURITY_ALERT,
                            source_module="zye.security.injection_scanner",
                            payload={
                                "threat_level": level.value,
                                "pattern": name,
                                "snippet": matched_snippet,
                                "description": desc,
                            },
                        )
                    )

        return findings

    def is_safe(self, text: str, block_levels: Optional[List[ThreatLevel]] = None) -> bool:
        """Return True if no findings meet or exceed blocked threat levels."""
        blocked = block_levels or [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
        findings = self.scan(text)
        for f in findings:
            if f.threat_level in blocked:
                return False
        return True


__all__ = [
    "ThreatLevel",
    "ScanFinding",
    "InjectionScanner",
]

"""
ZYE AI — Brute-Force Pattern Detection Engine (Day 40).
Identifies repeated failed authentication attempts against single accounts
from specific source IPs over configurable rolling windows.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Tuple

from zye_cybersecurity.authentication.auth_models import (
    AuthPatternFinding,
    NormalizedAuthEvent,
)

logger = logging.getLogger("zye.cybersecurity.brute_force")


class BruteForceDetector:
    """Detects repeated single-target failed authentication attempts."""

    def __init__(
        self,
        attempt_threshold: int = 3,
        threshold: Optional[int] = None,
        window_minutes: float = 5.0,
    ) -> None:
        self.attempt_threshold = threshold if threshold is not None else attempt_threshold
        self.window_minutes = window_minutes

    def detect(self, events: List[NormalizedAuthEvent]) -> List[AuthPatternFinding]:
        """Alias for detect_patterns."""
        return self.detect_patterns(events)

    def detect_patterns(
        self,
        events: List[NormalizedAuthEvent],
    ) -> List[AuthPatternFinding]:
        """
        Analyze events for brute-force signatures.
        Groups by (source_ip, target_account) within rolling time window.
        """
        findings: List[AuthPatternFinding] = []
        if not events:
            return findings

        # Filter events within window_minutes of now
        now = datetime.now(timezone.utc)
        recent_events = []
        for ev in events:
            age_min = (now - ev.time_created).total_seconds() / 60.0
            if age_min <= (self.window_minutes + 1.0):
                recent_events.append(ev)

        if not recent_events:
            return findings

        groups: Dict[Tuple[str, str], List[NormalizedAuthEvent]] = defaultdict(list)

        for ev in recent_events:
            src = ev.source_ip or "LOCAL_MACHINE"
            tgt = ev.target_username or "UNKNOWN_ACCOUNT"
            groups[(src, tgt)].append(ev)

        for (src_ip, target_acct), ev_list in groups.items():
            if len(ev_list) < self.attempt_threshold:
                continue

            ev_list.sort(key=lambda x: x.timestamp_utc)
            first_attempt = ev_list[0].time_created
            last_attempt = ev_list[-1].time_created
            logon_types = list({e.logon_type for e in ev_list if e.logon_type is not None})
            primary_logon_type = logon_types[0] if logon_types else None

            # Severity calculation
            is_rdp = primary_logon_type in (10, 12)
            if len(ev_list) >= (self.attempt_threshold * 3) or (is_rdp and len(ev_list) >= self.attempt_threshold):
                sev = "HIGH" if not is_rdp else "CRITICAL"
            elif len(ev_list) >= (self.attempt_threshold * 2):
                sev = "HIGH"
            else:
                sev = "MEDIUM"

            finding = AuthPatternFinding(
                category="BRUTE_FORCE",
                severity=sev,
                failed_attempts=len(ev_list),
                time_window_minutes=self.window_minutes,
                source_ip=src_ip,
                target_account=target_acct,
                logon_type=primary_logon_type,
                first_attempt_time=first_attempt,
                last_attempt_time=last_attempt,
                evidence=[
                    f"{len(ev_list)} failed authentication attempts targeting account '{target_acct}' from IP {src_ip}",
                    f"Logon type: {primary_logon_type}",
                ],
                details={
                    "attempt_count": len(ev_list),
                    "first_attempt": first_attempt.isoformat(),
                    "last_attempt": last_attempt.isoformat(),
                }
            )
            findings.append(finding)

        return findings

"""
ZYE AI — Password-Spraying Pattern Detection Engine (Day 40).
Detects 1-to-N horizontal authentication attack patterns where a single source IP
attempts authentication against multiple distinct accounts.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Set

from zye_cybersecurity.authentication.auth_models import (
    AuthPatternFinding,
    NormalizedAuthEvent,
)

logger = logging.getLogger("zye.cybersecurity.password_spray")


class PasswordSprayDetector:
    """Detects 1-to-N horizontal password spraying patterns across distinct accounts."""

    def __init__(
        self,
        min_distinct_accounts: int = 3,
        min_accounts: Optional[int] = None,
        window_minutes: float = 15.0,
    ) -> None:
        self.min_distinct_accounts = min_accounts if min_accounts is not None else min_distinct_accounts
        self.window_minutes = window_minutes

    def detect(self, events: List[NormalizedAuthEvent]) -> List[AuthPatternFinding]:
        """Alias for detect_patterns."""
        return self.detect_patterns(events)

    def detect_patterns(
        self,
        events: List[NormalizedAuthEvent],
    ) -> List[AuthPatternFinding]:
        """
        Analyze events for password-spraying signatures.
        Identifies single source IPs targeting multiple distinct usernames.
        """
        findings: List[AuthPatternFinding] = []
        if not events:
            return findings

        # Filter events within window_minutes
        now = datetime.now(timezone.utc)
        recent_events = []
        for ev in events:
            age_min = (now - ev.time_created).total_seconds() / 60.0
            if age_min <= (self.window_minutes + 1.0):
                recent_events.append(ev)

        ip_groups: Dict[str, List[NormalizedAuthEvent]] = defaultdict(list)
        for ev in recent_events:
            if ev.source_ip and ev.source_ip != "-":
                ip_groups[ev.source_ip].append(ev)

        for src_ip, ev_list in ip_groups.items():
            distinct_accounts: Set[str] = {
                e.target_username for e in ev_list if e.target_username and e.target_username != "UNKNOWN"
            }

            if len(distinct_accounts) >= self.min_distinct_accounts:
                ev_list.sort(key=lambda x: x.timestamp_utc)
                first_attempt = ev_list[0].time_created
                last_attempt = ev_list[-1].time_created

                sev = "CRITICAL" if len(distinct_accounts) >= 6 else ("HIGH" if len(distinct_accounts) >= 3 else "MEDIUM")
                findings.append(
                    AuthPatternFinding(
                        category="PASSWORD_SPRAY",
                        severity=sev,
                        failed_attempts=len(ev_list),
                        time_window_minutes=self.window_minutes,
                        source_ip=src_ip,
                        distinct_accounts_count=len(distinct_accounts),
                        first_attempt_time=first_attempt,
                        last_attempt_time=last_attempt,
                        evidence=[
                            f"Single IP {src_ip} attempted authentication across {len(distinct_accounts)} distinct accounts",
                        ],
                        details={
                            "distinct_accounts": sorted(list(distinct_accounts)),
                            "total_attempts": len(ev_list),
                        }
                    )
                )

        return findings

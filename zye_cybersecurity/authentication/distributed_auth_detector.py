"""
ZYE AI — Distributed Authentication Attempt Detector (Day 40).
Detects N-to-1 distributed authentication patterns where a single target account
is probed from multiple distinct source IP addresses.
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

logger = logging.getLogger("zye.cybersecurity.distributed_auth")


class DistributedAuthDetector:
    """Detects N-to-1 distributed authentication patterns targeting a single account."""

    def __init__(
        self,
        min_distinct_sources: int = 3,
        min_source_ips: Optional[int] = None,
        window_minutes: float = 30.0,
    ) -> None:
        self.min_distinct_sources = min_source_ips if min_source_ips is not None else min_distinct_sources
        self.window_minutes = window_minutes

    def detect(self, events: List[NormalizedAuthEvent]) -> List[AuthPatternFinding]:
        """Alias for detect_patterns."""
        return self.detect_patterns(events)

    def detect_patterns(
        self,
        events: List[NormalizedAuthEvent],
    ) -> List[AuthPatternFinding]:
        """
        Analyze events for distributed brute-force signatures.
        Identifies a single username targeted by multiple distinct source IPs.
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

        acct_groups: Dict[str, List[NormalizedAuthEvent]] = defaultdict(list)
        for ev in recent_events:
            if ev.target_username and ev.target_username != "UNKNOWN":
                acct_groups[ev.target_username].append(ev)

        for target_acct, ev_list in acct_groups.items():
            distinct_sources: Set[str] = {
                e.source_ip for e in ev_list if e.source_ip and e.source_ip not in ("-", "LOCAL_MACHINE")
            }

            if len(distinct_sources) >= self.min_distinct_sources:
                ev_list.sort(key=lambda x: x.timestamp_utc)
                first_attempt = ev_list[0].time_created
                last_attempt = ev_list[-1].time_created

                findings.append(
                    AuthPatternFinding(
                        category="DISTRIBUTED_AUTH_ATTACK",
                        severity="CRITICAL" if len(distinct_sources) >= 5 else "HIGH",
                        failed_attempts=len(ev_list),
                        time_window_minutes=self.window_minutes,
                        target_account=target_acct,
                        distinct_sources_count=len(distinct_sources),
                        first_attempt_time=first_attempt,
                        last_attempt_time=last_attempt,
                        evidence=[
                            f"Account '{target_acct}' targeted by {len(distinct_sources)} distinct source IPs",
                        ],
                        details={
                            "distinct_sources": sorted(list(distinct_sources)),
                            "total_attempts": len(ev_list),
                        }
                    )
                )

        return findings

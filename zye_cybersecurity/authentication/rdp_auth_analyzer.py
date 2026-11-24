"""
ZYE AI — RDP Authentication Failure Intelligence Engine (Day 40).
Specialized analyzer for Remote Desktop (LogonType 10 / 12) authentication failures.
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
from zye_cybersecurity.authentication.logon_type_analyzer import LogonTypeAnalyzer

logger = logging.getLogger("zye.cybersecurity.rdp_analyzer")


class RdpAuthAnalyzer:
    """Specialized analyzer for Remote Desktop authentication failures."""

    def __init__(
        self,
        failure_threshold: int = 3,
        threshold: Optional[int] = None,
        window_minutes: float = 30.0,
    ) -> None:
        self.failure_threshold = threshold if threshold is not None else failure_threshold
        self.window_minutes = window_minutes

    def detect(self, events: List[NormalizedAuthEvent]) -> List[AuthPatternFinding]:
        """Alias for detect_patterns."""
        _, findings = self.analyze_rdp_events(events)
        return findings

    def analyze_rdp_events(
        self,
        events: List[NormalizedAuthEvent],
    ) -> Tuple[int, List[AuthPatternFinding]]:
        """
        Filter and analyze Remote Desktop (LogonType 10/12) failed logons.
        Returns (rdp_failures_count, rdp_findings).
        """
        rdp_events = [e for e in events if LogonTypeAnalyzer.is_remote_desktop(e.logon_type)]
        total_rdp = len(rdp_events)

        findings: List[AuthPatternFinding] = []
        if total_rdp == 0:
            return 0, findings

        groups: Dict[tuple[str, str], List[NormalizedAuthEvent]] = defaultdict(list)
        for ev in rdp_events:
            src = ev.source_ip or "REMOTE_UNKNOWN"
            tgt = ev.target_username or "UNKNOWN_ACCOUNT"
            groups[(src, tgt)].append(ev)

        for (src_ip, target_acct), ev_list in groups.items():
            if len(ev_list) >= self.failure_threshold:
                ev_list.sort(key=lambda x: x.timestamp_utc)
                first_attempt = ev_list[0].time_created
                last_attempt = ev_list[-1].time_created

                findings.append(
                    AuthPatternFinding(
                        category="RDP_AUTH_FAILURE",
                        severity="CRITICAL" if len(ev_list) >= 5 else "HIGH",
                        failed_attempts=len(ev_list),
                        time_window_minutes=self.window_minutes,
                        source_ip=src_ip,
                        target_account=target_acct,
                        logon_type=10,
                        first_attempt_time=first_attempt,
                        last_attempt_time=last_attempt,
                        evidence=[
                            f"{len(ev_list)} Remote Desktop (RDP) failed logons from IP {src_ip} targeting account '{target_acct}'",
                        ],
                        details={
                            "attempt_count": len(ev_list),
                        }
                    )
                )

        return total_rdp, findings

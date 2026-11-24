"""
ZYE AI — Master Windows Authentication Security Intelligence Engine (Day 40).
Orchestrates Event ID 4625 retrieval, XML parsing, attack pattern recognition,
Day 39 LAN enrichment, alert logging with cooldown, and overall risk classification.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from zye_cybersecurity.authentication.auth_models import (
    AuthAnalysisSummary,
    AuthPatternFinding,
    NormalizedAuthEvent,
    get_utc_iso_timestamp,
    mask_identifier,
)
from zye_cybersecurity.authentication.brute_force_detector import BruteForceDetector
from zye_cybersecurity.authentication.distributed_auth_detector import DistributedAuthDetector
from zye_cybersecurity.authentication.event_retriever import EventRetriever
from zye_cybersecurity.authentication.password_spray_detector import PasswordSprayDetector
from zye_cybersecurity.authentication.rdp_auth_analyzer import RdpAuthAnalyzer
from zye_cybersecurity.discovery.lan_scanner import LanScanner

logger = logging.getLogger("zye.cybersecurity.auth_engine")


class AuthSecurityEngine:
    """Master facade for Windows authentication security intelligence and failed-logon monitoring."""

    def __init__(
        self,
        alert_log_path: Optional[Any] = None,
        alert_cooldown_minutes: float = 10.0,
    ) -> None:
        self.alert_log_path = Path(alert_log_path) if alert_log_path is not None else Path("logs/zye_security_alerts.log")
        self.alert_cooldown_minutes = alert_cooldown_minutes
        self.retriever = EventRetriever
        self._last_processed_record_id: Optional[int] = None
        self._last_query_timestamp: Optional[str] = None
        self._last_query_status: str = "IDLE"
        self._last_query_error: Optional[str] = None
        # incident_fingerprint -> last_alert_time
        self._alert_cooldown_tracker: Dict[str, float] = {}

        # Component detectors
        self.brute_force_detector = BruteForceDetector(attempt_threshold=3, window_minutes=5.0)
        self.password_spray_detector = PasswordSprayDetector(min_distinct_accounts=3, window_minutes=15.0)
        self.distributed_detector = DistributedAuthDetector(min_distinct_sources=3, window_minutes=30.0)
        self.rdp_analyzer = RdpAuthAnalyzer(failure_threshold=3)

    def emit_alert_if_due(self, finding: AuthPatternFinding) -> Optional[Dict[str, Any]]:
        """Log alert if cooldown has expired, returning alert dict or None."""
        return self._log_security_alert(finding)

    def run_analysis(
        self,
        minutes: int = 60,
        max_events: int = 500,
        source_ip_filter: Optional[str] = None,
        target_account_filter: Optional[str] = None,
        logon_type_filter: Optional[int] = None,
        mask_accounts: bool = True,
    ) -> AuthAnalysisSummary:
        """Alias for analyze_authentication_security."""
        return self.analyze_authentication_security(
            time_window_minutes=minutes,
            max_events=max_events,
            source_ip_filter=source_ip_filter,
            target_account_filter=target_account_filter,
            logon_type_filter=logon_type_filter,
            mask_accounts=mask_accounts,
        )

    def set_thresholds(
        self,
        brute_force_threshold: int = 3,
        password_spray_threshold: int = 3,
        distinct_accounts_threshold: int = 3,
    ) -> None:
        """Update detection thresholds dynamically."""
        self.brute_force_detector.attempt_threshold = brute_force_threshold
        self.password_spray_detector.min_distinct_accounts = distinct_accounts_threshold
        self.distributed_detector.min_distinct_sources = distinct_accounts_threshold

    def _enrich_with_day39_lan(self, ip_str: Optional[str]) -> Optional[str]:
        """Cross-reference source IP against Day 39 LAN Device Discovery inventory."""
        if not ip_str or ip_str in ("-", "127.0.0.1", "::1", "LOCAL_MACHINE"):
            return None

        try:
            # Query in-memory LAN observation registry
            from zye_cybersecurity.discovery.device_deduplicator import DeviceDeduplicator
            from zye_cybersecurity.discovery.device_models import normalize_mac_address

            # Check if LanScanner singleton has observed this IP
            # (In Day 39, _dedup tracks historical observations)
            from cyber_security_mcp import _dedup
            tracked = _dedup.get_tracked_devices()
            match = next((d for d in tracked if d.ip_address == ip_str), None)
            if match:
                return (
                    f"Source IP matches recently observed LAN device "
                    f"(MAC: {match.mac_address}, status: {match.observation_status}, method: {match.discovery_method})"
                )
        except Exception:
            pass

        return "DEVICE_NOT_IDENTIFIED in local ARP cache"

    def _log_security_alert(self, finding: AuthPatternFinding) -> None:
        """Log structured security alert with cooldown deduplication."""
        fingerprint = hashlib.sha256(
            f"{finding.category}|{finding.source_ip}|{finding.target_account}".encode("utf-8")
        ).hexdigest()[:16]

        now = time.time()
        last_time = self._alert_cooldown_tracker.get(fingerprint, 0.0)
        if (now - last_time) < (self.alert_cooldown_minutes * 60.0):
            # Cooldown active; suppress duplicate alert
            return

        self._alert_cooldown_tracker[fingerprint] = now

        alert_entry = {
            "alert_id": f"alt_{fingerprint}_{int(now)}",
            "timestamp_utc": get_utc_iso_timestamp(),
            "category": finding.category,
            "pattern_type": finding.category,
            "severity": finding.severity,
            "source_ip": finding.source_ip,
            "target_account": mask_identifier(finding.target_account),
            "failed_attempts": finding.failed_attempts,
            "time_window_minutes": finding.time_window_minutes,
            "logon_type": finding.logon_type,
            "evidence": finding.evidence,
            "confidence": finding.confidence,
            "confirmed_compromise": finding.confirmed_compromise,
            "correlation_id": fingerprint,
        }

        try:
            self.alert_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.alert_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert_entry) + "\n")
            return alert_entry
        except Exception as e:
            logger.warning("Could not write security alert to %s: %s", self.alert_log_path, e)
            return None

    def analyze_authentication_security(
        self,
        time_window_minutes: int = 60,
        max_events: int = 500,
        source_ip_filter: Optional[str] = None,
        target_account_filter: Optional[str] = None,
        logon_type_filter: Optional[int] = None,
        mask_accounts: bool = True,
    ) -> AuthAnalysisSummary:
        """
        Main analysis pipeline:
          1. Retrieve Event ID 4625 records from Security log / provider
          2. Filter events (source IP, account, logon type)
          3. Evaluate brute-force, password-spraying, distributed, and RDP patterns
          4. Enrich findings with Day 39 LAN observations
          5. Compute overall risk classification
          6. Record security alerts and return structured JSON summary
        """
        t0 = time.perf_counter()
        query_ts = get_utc_iso_timestamp()
        self._last_query_timestamp = query_ts
        warnings: List[str] = []
        errors: List[str] = []

        status, raw_events, err = EventRetriever.fetch_failed_logon_events(
            time_window_minutes=time_window_minutes,
            max_events=max_events,
        )
        self._last_query_status = status
        self._last_query_error = err

        if err:
            errors.append(err)

        if status == "SECURITY_LOG_ACCESS_DENIED":
            warnings.append("Security log access requires elevated administrator privileges.")
            return AuthAnalysisSummary(
                status="ACCESS_DENIED",
                query_timestamp_utc=query_ts,
                analysis_window_minutes=time_window_minutes,
                total_events_retrieved=0,
                valid_events=0,
                invalid_events=0,
                unique_source_ips=0,
                unique_target_accounts=0,
                rdp_failures=0,
                overall_risk="MONITORING_DEGRADED",
                warnings=warnings,
                errors=errors,
                execution_time_ms=(time.perf_counter() - t0) * 1000,
            )

        if status == "AUDIT_POLICY_DISABLED":
            warnings.append("Logon failure auditing appears disabled in local security policy.")
            return AuthAnalysisSummary(
                status="AUDIT_DISABLED",
                query_timestamp_utc=query_ts,
                analysis_window_minutes=time_window_minutes,
                total_events_retrieved=0,
                valid_events=0,
                invalid_events=0,
                unique_source_ips=0,
                unique_target_accounts=0,
                rdp_failures=0,
                overall_risk="MONITORING_DEGRADED",
                warnings=warnings,
                errors=errors,
                execution_time_ms=(time.perf_counter() - t0) * 1000,
            )

        # Apply user filters
        filtered_events: List[NormalizedAuthEvent] = []
        for ev in raw_events:
            if source_ip_filter and ev.source_ip != source_ip_filter:
                continue
            if target_account_filter and ev.target_username != target_account_filter:
                continue
            if logon_type_filter is not None and ev.logon_type != logon_type_filter:
                continue
            filtered_events.append(ev)

            # Update max record id
            if ev.event_record_id is not None:
                if self._last_processed_record_id is None or ev.event_record_id > self._last_processed_record_id:
                    self._last_processed_record_id = ev.event_record_id

        # Unique metrics
        source_ips: Set[str] = {e.source_ip for e in filtered_events if e.source_ip}
        target_accounts: Set[str] = {e.target_username for e in filtered_events if e.target_username}

        # 3. Attack Pattern Evaluations
        all_findings: List[AuthPatternFinding] = []

        # Brute-force
        bf_findings = self.brute_force_detector.detect_patterns(filtered_events)
        all_findings.extend(bf_findings)

        # Password spraying
        spray_findings = self.password_spray_detector.detect_patterns(filtered_events)
        all_findings.extend(spray_findings)

        # Distributed authentication
        dist_findings = self.distributed_detector.detect_patterns(filtered_events)
        all_findings.extend(dist_findings)

        # RDP analysis
        rdp_count, rdp_findings = self.rdp_analyzer.analyze_rdp_events(filtered_events)
        all_findings.extend(rdp_findings)

        # 4. LAN Enrichment & Alert Logging
        for f in all_findings:
            if f.source_ip:
                enrichment = self._enrich_with_day39_lan(f.source_ip)
                if enrichment:
                    f.local_network_enrichment = enrichment
                    f.evidence.append(f"Network discovery: {enrichment}")

            # Log alert
            self._log_security_alert(f)

        # 5. Overall Risk Determination
        if any(f.severity == "CRITICAL" for f in all_findings):
            overall_risk = "CRITICAL"
        elif any(f.severity == "HIGH" for f in all_findings):
            overall_risk = "HIGH"
        elif any(f.severity == "MEDIUM" for f in all_findings):
            overall_risk = "MEDIUM"
        elif len(filtered_events) >= 3:
            overall_risk = "MEDIUM"
        elif len(filtered_events) > 0:
            overall_risk = "LOW"
        else:
            overall_risk = "CLEAN"

        summary = AuthAnalysisSummary(
            status=status if status in ("SUCCESS", "NO_EVENTS_FOUND", "SECURITY_LOG_ACCESS_DENIED", "AUDIT_POLICY_DISABLED", "EVENT_QUERY_TIMEOUT", "EVENT_QUERY_FAILED") else "ANALYSIS_COMPLETED",
            query_timestamp_utc=query_ts,
            analysis_window_minutes=time_window_minutes,
            total_events_retrieved=len(raw_events),
            valid_events=len(filtered_events),
            invalid_events=0,
            unique_source_ips=len(source_ips),
            unique_target_accounts=len(target_accounts),
            rdp_failures=rdp_count,
            overall_risk=overall_risk,
            findings=[f.to_dict(mask_accounts=mask_accounts) for f in all_findings],
            events=[e.to_dict(mask_accounts=mask_accounts) for e in filtered_events[:20]],
            monitoring={
                "enabled": False,
                "last_processed_record_id": self._last_processed_record_id,
            },
            warnings=warnings,
            errors=errors,
            execution_time_ms=round((time.perf_counter() - t0) * 1000, 2),
        )

        return summary

    def get_security_status(self) -> Dict[str, Any]:
        """Return diagnostic health status of the authentication monitoring engine."""
        import sys
        return {
            "status": "HEALTHY" if self._last_query_status in ("SUCCESS", "NO_EVENTS_FOUND", "IDLE") else "DEGRADED",
            "windows_audit_capability": "SUPPORTED" if sys.platform == "win32" else "UNSUPPORTED",
            "windows_security_log_query_status": self._last_query_status,
            "last_query_timestamp": self._last_query_timestamp,
            "last_processed_record_id": self._last_processed_record_id,
            "last_error": self._last_query_error,
            "alert_log_file": str(self.alert_log_path),
            "alert_cooldown_minutes": self.alert_cooldown_minutes,
            "active_monitored_incidents": len(self._alert_cooldown_tracker),
            "detection_policy": {
                "brute_force_threshold": self.brute_force_detector.attempt_threshold,
                "spray_threshold": self.password_spray_detector.min_distinct_accounts,
                "cooldown_minutes": self.alert_cooldown_minutes,
            },
        }

    def get_recorded_alerts(
        self,
        limit: int = 20,
        severity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Read recorded security alerts from logs/zye_security_alerts.log."""
        alerts: List[Dict[str, Any]] = []
        if not self.alert_log_path.exists():
            return alerts

        try:
            with open(self.alert_log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        record = json.loads(line_str)
                        if severity and record.get("severity", "").upper() != severity.upper():
                            continue
                        alerts.append(record)
                        if len(alerts) >= limit:
                            break
                    except Exception:
                        pass
        except Exception as e:
            logger.warning("Error reading alerts from %s: %s", self.alert_log_path, e)

        return alerts

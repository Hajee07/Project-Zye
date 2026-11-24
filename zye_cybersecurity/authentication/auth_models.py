"""
ZYE AI — Authentication Event Models & Data Structures (Day 40).
Normalized schemas for Windows Event ID 4625 failed logins, pattern findings,
and authentication security summaries.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional


def get_utc_iso_timestamp() -> str:
    """Return current UTC timestamp formatted as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def mask_identifier(ident: Optional[str]) -> Optional[str]:
    """
    Mask sensitive account or user identifiers for privacy protection.
    Example: 'Administrator' -> 'A***r', 'alice' -> 'A***e', 'Bob' -> 'B*b', 'sa' -> '**'.
    """
    if not ident or not isinstance(ident, str):
        return "-" if ident == "" else ident
    s = ident.strip()
    if not s or s == "-":
        return "-"
    if len(s) == 1:
        return s
    if len(s) == 2:
        return f"{s[0]}*"
    if len(s) == 3:
        return f"{s[0]}*{s[-1]}"
    if len(s) <= 4:
        return f"{s[0]}**{s[-1]}"
    return f"{s[0]}***{s[-1]}"


@dataclass
class NormalizedAuthEvent:
    """Normalized representation of a Windows Security Event ID 4625."""
    event_id: int = 4625
    event_record_id: Optional[int] = None
    timestamp_utc: str = field(default_factory=get_utc_iso_timestamp)
    computer: str = "LOCAL_COMPUTER"
    channel: str = "Security"
    provider_name: str = "Microsoft-Windows-Security-Auditing"
    target_username: Optional[str] = None
    target_domain: Optional[str] = None
    target_sid: Optional[str] = None
    subject_username: Optional[str] = None
    source_ip: Optional[str] = None
    source_port: Optional[int] = None
    workstation_name: Optional[str] = None
    logon_type: Optional[int] = None
    logon_type_name: str = "UNKNOWN_LOGON_TYPE"
    logon_process_name: Optional[str] = None
    authentication_package: Optional[str] = None
    status: Optional[str] = None
    sub_status: Optional[str] = None
    status_description: Optional[str] = None
    sub_status_description: Optional[str] = None
    failure_reason: Optional[str] = None
    process_id: Optional[int] = None
    process_name: Optional[str] = None
    event_source: str = "WINDOWS_SECURITY_LOG"
    raw_data: Dict[str, Any] = field(default_factory=dict)

    # Aliases for flexible test and diagnostic access
    def __init__(
        self,
        event_id: int = 4625,
        event_record_id: Optional[int] = None,
        timestamp_utc: Optional[str] = None,
        time_created: Optional[datetime] = None,
        computer: str = "LOCAL_COMPUTER",
        computer_name: Optional[str] = None,
        channel: str = "Security",
        provider_name: str = "Microsoft-Windows-Security-Auditing",
        target_username: Optional[str] = None,
        target_user_name: Optional[str] = None,
        target_domain: Optional[str] = None,
        target_domain_name: Optional[str] = None,
        target_sid: Optional[str] = None,
        subject_username: Optional[str] = None,
        source_ip: Optional[str] = None,
        ip_address: Optional[str] = None,
        source_port: Optional[int] = None,
        ip_port: Optional[int] = None,
        workstation_name: Optional[str] = None,
        logon_type: Optional[int] = None,
        logon_type_name: str = "UNKNOWN_LOGON_TYPE",
        logon_process_name: Optional[str] = None,
        authentication_package: Optional[str] = None,
        status: Optional[str] = None,
        status_code: Optional[str] = None,
        sub_status: Optional[str] = None,
        sub_status_code: Optional[str] = None,
        status_description: Optional[str] = None,
        sub_status_description: Optional[str] = None,
        failure_reason: Optional[str] = None,
        process_id: Optional[int] = None,
        process_name: Optional[str] = None,
        event_source: str = "WINDOWS_SECURITY_LOG",
        raw_data: Optional[Dict[str, Any]] = None,
    ):
        self.event_id = event_id
        self.event_record_id = event_record_id
        if time_created is not None:
            if time_created.tzinfo is None:
                time_created = time_created.replace(tzinfo=timezone.utc)
            self.timestamp_utc = time_created.astimezone(timezone.utc).isoformat()
        else:
            self.timestamp_utc = timestamp_utc or get_utc_iso_timestamp()
        self.computer = computer_name or computer
        self.channel = channel
        self.provider_name = provider_name
        self.target_username = target_user_name or target_username
        self.target_domain = target_domain_name or target_domain
        self.target_sid = target_sid
        self.subject_username = subject_username
        self.source_ip = ip_address or source_ip
        self.source_port = ip_port if ip_port is not None else source_port
        self.workstation_name = workstation_name
        self.logon_type = logon_type
        self.logon_type_name = logon_type_name
        self.logon_process_name = logon_process_name
        self.authentication_package = authentication_package
        self.status = status_code or status
        self.sub_status = sub_status_code or sub_status
        self.status_description = status_description
        self.sub_status_description = sub_status_description
        self.failure_reason = failure_reason
        self.process_id = process_id
        self.process_name = process_name
        self.event_source = event_source
        self.raw_data = raw_data or {}

    @property
    def target_user_name(self) -> str:
        return self.target_username or "UNKNOWN"

    @property
    def target_domain_name(self) -> Optional[str]:
        return self.target_domain

    @property
    def ip_address(self) -> str:
        return self.source_ip or "-"

    @property
    def ip_port(self) -> Optional[int]:
        return self.source_port

    @property
    def status_code(self) -> Optional[str]:
        return self.status

    @property
    def sub_status_code(self) -> Optional[str]:
        return self.sub_status

    @property
    def effective_status(self) -> Optional[str]:
        return self.sub_status or self.status

    @property
    def computer_name(self) -> str:
        return self.computer

    @property
    def time_created(self) -> datetime:
        try:
            dt = datetime.fromisoformat(self.timestamp_utc)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return datetime.now(timezone.utc)

    @property
    def masked_account(self) -> str:
        return mask_identifier(self.target_username or "UNKNOWN")

    @property
    def is_loopback(self) -> bool:
        return self.source_ip in ("127.0.0.1", "::1", "localhost")

    def to_dict(self, mask_accounts: bool = True) -> Dict[str, Any]:
        """Convert to dictionary with optional account masking."""
        d = {
            "event_id": self.event_id,
            "event_record_id": self.event_record_id,
            "timestamp_utc": self.timestamp_utc,
            "computer": self.computer,
            "channel": self.channel,
            "provider_name": self.provider_name,
            "target_username": self.target_username,
            "target_domain": self.target_domain,
            "target_sid": self.target_sid,
            "subject_username": self.subject_username,
            "source_ip": self.source_ip,
            "source_port": self.source_port,
            "workstation_name": self.workstation_name,
            "logon_type": self.logon_type,
            "logon_type_name": self.logon_type_name,
            "logon_process_name": self.logon_process_name,
            "authentication_package": self.authentication_package,
            "status": self.status,
            "sub_status": self.sub_status,
            "status_description": self.status_description,
            "sub_status_description": self.sub_status_description,
            "failure_reason": self.failure_reason,
            "process_id": self.process_id,
            "process_name": self.process_name,
            "event_source": self.event_source,
        }
        if mask_accounts and d.get("target_username"):
            d["target_username"] = mask_identifier(d["target_username"])
        if mask_accounts and d.get("subject_username"):
            d["subject_username"] = mask_identifier(d["subject_username"])
        return d


@dataclass
class AuthPatternFinding:
    """Detailed finding of an identified authentication pattern or anomaly."""
    category: str
    severity: str  # INFORMATIONAL, LOW, MEDIUM, HIGH, CRITICAL
    failed_attempts: int
    time_window_minutes: float
    source_ip: Optional[str] = None
    target_account: Optional[str] = None
    distinct_accounts_count: int = 1
    distinct_sources_count: int = 1
    logon_type: Optional[int] = None
    evidence: List[str] = field(default_factory=list)
    confidence: str = "RULE_BASED_HIGH"
    confirmed_compromise: bool = False
    local_network_enrichment: Optional[str] = None
    first_attempt_time: Optional[datetime] = None
    last_attempt_time: Optional[datetime] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        category: Optional[str] = None,
        pattern_type: Optional[str] = None,
        severity: str = "MEDIUM",
        failed_attempts: Optional[int] = None,
        attempt_count: Optional[int] = None,
        time_window_minutes: float = 15.0,
        source_ip: Optional[str] = None,
        target_account: Optional[str] = None,
        distinct_accounts_count: Optional[int] = None,
        target_accounts_count: Optional[int] = None,
        distinct_sources_count: Optional[int] = None,
        source_ips_count: Optional[int] = None,
        logon_type: Optional[int] = None,
        evidence: Optional[List[str]] = None,
        confidence: str = "RULE_BASED_HIGH",
        confirmed_compromise: bool = False,
        local_network_enrichment: Optional[str] = None,
        first_attempt_time: Optional[datetime] = None,
        last_attempt_time: Optional[datetime] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.category = pattern_type or category or "UNKNOWN_PATTERN"
        self.severity = severity
        self.failed_attempts = attempt_count if attempt_count is not None else (failed_attempts or 1)
        self.time_window_minutes = time_window_minutes
        self.source_ip = source_ip
        self.target_account = target_account
        self.distinct_accounts_count = target_accounts_count if target_accounts_count is not None else (distinct_accounts_count or 1)
        self.distinct_sources_count = source_ips_count if source_ips_count is not None else (distinct_sources_count or 1)
        self.logon_type = logon_type
        self.evidence = evidence or []
        self.confidence = confidence
        self.confirmed_compromise = confirmed_compromise
        self.local_network_enrichment = local_network_enrichment
        self.first_attempt_time = first_attempt_time
        self.last_attempt_time = last_attempt_time
        self.details = details or {}

    @property
    def pattern_type(self) -> str:
        return self.category

    @property
    def attempt_count(self) -> int:
        return self.failed_attempts

    @property
    def target_accounts_count(self) -> int:
        return self.distinct_accounts_count

    @property
    def source_ips_count(self) -> int:
        return self.distinct_sources_count

    def to_dict(self, mask_accounts: bool = True) -> Dict[str, Any]:
        d = {
            "category": self.category,
            "pattern_type": self.category,
            "severity": self.severity,
            "failed_attempts": self.failed_attempts,
            "attempt_count": self.failed_attempts,
            "time_window_minutes": self.time_window_minutes,
            "source_ip": self.source_ip,
            "target_account": self.target_account,
            "distinct_accounts_count": self.distinct_accounts_count,
            "distinct_sources_count": self.distinct_sources_count,
            "logon_type": self.logon_type,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "confirmed_compromise": self.confirmed_compromise,
            "local_network_enrichment": self.local_network_enrichment,
            "details": self.details,
        }
        if mask_accounts and d.get("target_account"):
            d["target_account"] = mask_identifier(d["target_account"])
        return d


@dataclass
class AuthAnalysisSummary:
    """Master structured output schema for Day 40 authentication analysis."""
    status: str
    query_timestamp_utc: str
    analysis_window_minutes: int
    total_events_retrieved: int
    valid_events: int
    invalid_events: int
    unique_source_ips: int
    unique_target_accounts: int
    rdp_failures: int
    overall_risk: str  # CLEAN, INFORMATIONAL, LOW, MEDIUM, HIGH, CRITICAL, INSUFFICIENT_DATA, MONITORING_DEGRADED
    findings: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    monitoring: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0

    @property
    def total_failed_logins(self) -> int:
        return self.valid_events

    @property
    def retrieval_status(self) -> str:
        return self.status

    @property
    def risk_level(self) -> str:
        return self.overall_risk

    @property
    def risk_score(self) -> int:
        mapping = {
            "CRITICAL": 95,
            "HIGH": 80,
            "MEDIUM": 50,
            "LOW": 10,
            "INFORMATIONAL": 5,
            "CLEAN": 0,
        }
        return mapping.get(self.overall_risk, 0)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

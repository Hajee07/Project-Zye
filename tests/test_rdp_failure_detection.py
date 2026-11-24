"""
Tests for RDP Authentication Failure Detection (LogonType 10 / 12).
Tests remote desktop failed login tracking and external IP threat evaluation.
"""
from datetime import datetime, timezone, timedelta
from zye_cybersecurity.authentication.auth_models import NormalizedAuthEvent
from zye_cybersecurity.authentication.rdp_auth_analyzer import RdpAuthAnalyzer


def _make_rdp_event(rec_id: int, user: str, ip: str, logon_type: int = 10, minutes_ago: int = 0) -> NormalizedAuthEvent:
    return NormalizedAuthEvent(
        event_record_id=rec_id,
        time_created=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
        target_user_name=user,
        ip_address=ip,
        logon_type=logon_type,
        status_code="0xC000006D",
        sub_status_code="0xC000006A",
    )


def test_rdp_failures_detected():
    """Detect RDP failed logins meeting threshold."""
    analyzer = RdpAuthAnalyzer(threshold=3, window_minutes=30)
    events = [
        _make_rdp_event(1000 + i, "rdp_user", "198.51.100.50", logon_type=10, minutes_ago=i)
        for i in range(4)
    ]
    findings = analyzer.detect(events)
    assert len(findings) == 1
    f = findings[0]
    assert f.pattern_type == "RDP_AUTH_FAILURE"
    assert f.source_ip == "198.51.100.50"
    assert f.attempt_count == 4
    assert f.severity in ("HIGH", "CRITICAL")


def test_non_rdp_logons_ignored_by_rdp_analyzer():
    """Interactive or network logons ignored by RDP analyzer."""
    analyzer = RdpAuthAnalyzer(threshold=3, window_minutes=30)
    events = [
        _make_rdp_event(1100 + i, "console_user", "127.0.0.1", logon_type=2, minutes_ago=i)
        for i in range(5)
    ]
    findings = analyzer.detect(events)
    assert len(findings) == 0

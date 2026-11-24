"""
Tests 21-24: Brute-Force Pattern Detection Engine.
Tests repeated failures against single account, mixed unrelated events,
sliding time window bounding, and RDP repeated attempts.
"""
from datetime import datetime, timezone, timedelta
from zye_cybersecurity.authentication.auth_models import NormalizedAuthEvent
from zye_cybersecurity.authentication.brute_force_detector import BruteForceDetector


def _make_event(rec_id: int, user: str, ip: str, logon_type: int = 3, minutes_ago: int = 0) -> NormalizedAuthEvent:
    now = datetime.now(timezone.utc)
    return NormalizedAuthEvent(
        event_record_id=rec_id,
        time_created=now - timedelta(minutes=minutes_ago),
        target_user_name=user,
        ip_address=ip,
        logon_type=logon_type,
        status_code="0xC000006D",
        sub_status_code="0xC000006A",
        computer_name="DESKTOP-01"
    )


def test_21_repeated_failures_single_account():
    """Test 21: Detect brute-force pattern when attempts exceed threshold (>=5)."""
    detector = BruteForceDetector(threshold=5, window_minutes=15)
    events = [
        _make_event(100 + i, "Admin", "192.168.1.100", minutes_ago=i)
        for i in range(6)
    ]
    findings = detector.detect(events)
    assert len(findings) == 1
    f = findings[0]
    assert f.pattern_type == "BRUTE_FORCE"
    assert f.source_ip == "192.168.1.100"
    assert f.target_account == "Admin"
    assert f.attempt_count == 6
    assert f.severity in ("MEDIUM", "HIGH", "CRITICAL")


def test_22_unrelated_failures_below_threshold():
    """Test 22: Events below threshold do not trigger brute-force alarm."""
    detector = BruteForceDetector(threshold=5, window_minutes=15)
    events = [
        _make_event(201, "Alice", "192.168.1.101"),
        _make_event(202, "Bob", "192.168.1.102"),
        _make_event(203, "Charlie", "192.168.1.103"),
    ]
    findings = detector.detect(events)
    assert len(findings) == 0


def test_23_sliding_window_filtering():
    """Test 23: Events outside window are ignored."""
    detector = BruteForceDetector(threshold=5, window_minutes=10)
    events = [
        _make_event(300 + i, "Admin", "192.168.1.100", minutes_ago=20 + i)
        for i in range(6)
    ]
    findings = detector.detect(events)
    assert len(findings) == 0


def test_24_rdp_repeated_failures():
    """Test 24: Brute-force over RDP (LogonType 10) correctly triggers HIGH/CRITICAL."""
    detector = BruteForceDetector(threshold=3, window_minutes=15)
    events = [
        _make_event(400 + i, "Administrator", "203.0.113.5", logon_type=10, minutes_ago=i)
        for i in range(4)
    ]
    findings = detector.detect(events)
    assert len(findings) == 1
    assert findings[0].logon_type == 10
    assert findings[0].severity in ("HIGH", "CRITICAL")

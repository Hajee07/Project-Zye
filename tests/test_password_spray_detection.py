"""
Tests 25-27: Password Spraying Detection (1-to-N pattern).
Tests single source IP targeting multiple distinct accounts.
"""
from datetime import datetime, timezone, timedelta
from zye_cybersecurity.authentication.auth_models import NormalizedAuthEvent
from zye_cybersecurity.authentication.password_spray_detector import PasswordSprayDetector


def _make_spray_event(rec_id: int, user: str, ip: str, minutes_ago: int = 0) -> NormalizedAuthEvent:
    return NormalizedAuthEvent(
        event_record_id=rec_id,
        time_created=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
        target_user_name=user,
        ip_address=ip,
        logon_type=3,
        status_code="0xC000006D",
        sub_status_code="0xC000006A",
    )


def test_25_password_spray_detection():
    """Test 25: Single IP attempting logins across >=3 distinct accounts triggers spray alert."""
    detector = PasswordSprayDetector(min_accounts=3, window_minutes=30)
    users = ["admin", "root", "guest", "test_user"]
    events = [
        _make_spray_event(500 + i, user, "192.168.1.200", minutes_ago=i * 2)
        for i, user in enumerate(users)
    ]
    findings = detector.detect(events)
    assert len(findings) == 1
    f = findings[0]
    assert f.pattern_type == "PASSWORD_SPRAY"
    assert f.source_ip == "192.168.1.200"
    assert f.target_accounts_count == 4
    assert f.severity in ("HIGH", "CRITICAL")


def test_26_password_spray_single_account_ignored():
    """Test 26: Multiple attempts against a single account do not trigger spray detector."""
    detector = PasswordSprayDetector(min_accounts=3, window_minutes=30)
    events = [
        _make_spray_event(600 + i, "admin", "192.168.1.200", minutes_ago=i)
        for i in range(5)
    ]
    findings = detector.detect(events)
    assert len(findings) == 0


def test_27_password_spray_distinct_ips_separated():
    """Test 27: Distinct IPs attacking separate accounts independently evaluated."""
    detector = PasswordSprayDetector(min_accounts=3, window_minutes=30)
    events = [
        _make_spray_event(701, "user1", "192.168.1.210"),
        _make_spray_event(702, "user2", "192.168.1.211"),
        _make_spray_event(703, "user3", "192.168.1.212"),
    ]
    findings = detector.detect(events)
    assert len(findings) == 0

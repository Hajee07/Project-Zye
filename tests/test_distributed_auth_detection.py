"""
Tests for Distributed Authentication Failure Detection (N-to-1 pattern).
Tests multiple distinct source IPs targeting a single victim account.
"""
from datetime import datetime, timezone, timedelta
from zye_cybersecurity.authentication.auth_models import NormalizedAuthEvent
from zye_cybersecurity.authentication.distributed_auth_detector import DistributedAuthDetector


def _make_dist_event(rec_id: int, user: str, ip: str, minutes_ago: int = 0) -> NormalizedAuthEvent:
    return NormalizedAuthEvent(
        event_record_id=rec_id,
        time_created=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
        target_user_name=user,
        ip_address=ip,
        logon_type=3,
        status_code="0xC000006D",
        sub_status_code="0xC000006A",
    )


def test_distributed_auth_detection_success():
    """Detect distributed attack: >=3 source IPs targeting single account."""
    detector = DistributedAuthDetector(min_source_ips=3, window_minutes=30)
    ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3", "10.0.0.4"]
    events = [
        _make_dist_event(800 + i, "target_admin", ip, minutes_ago=i)
        for i, ip in enumerate(ips)
    ]
    findings = detector.detect(events)
    assert len(findings) == 1
    f = findings[0]
    assert f.pattern_type == "DISTRIBUTED_AUTH_ATTACK"
    assert f.target_account == "target_admin"
    assert f.source_ips_count == 4
    assert f.severity in ("HIGH", "CRITICAL")


def test_distributed_auth_single_ip_ignored():
    """Single IP repeated attempts do not trigger distributed detector."""
    detector = DistributedAuthDetector(min_source_ips=3, window_minutes=30)
    events = [
        _make_dist_event(900 + i, "target_admin", "10.0.0.1", minutes_ago=i)
        for i in range(5)
    ]
    findings = detector.detect(events)
    assert len(findings) == 0

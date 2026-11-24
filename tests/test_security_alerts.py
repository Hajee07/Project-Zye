"""
Tests for Security Alert Logger and Cooldown Deduplication.
Tests alert formatting, cooldown deduplication, and persistence to zye_security_alerts.log.
"""
import os
import json
from datetime import datetime, timezone
from zye_cybersecurity.authentication.auth_models import AuthPatternFinding
from zye_cybersecurity.authentication.auth_security_engine import AuthSecurityEngine


def test_security_alert_deduplication(tmp_path):
    """Test that duplicate alerts within cooldown window are suppressed."""
    alert_log_file = tmp_path / "test_alerts.log"
    engine = AuthSecurityEngine(alert_log_path=str(alert_log_file), alert_cooldown_minutes=10)

    finding = AuthPatternFinding(
        pattern_type="BRUTE_FORCE",
        severity="HIGH",
        target_account="Admin",
        source_ip="192.168.1.100",
        attempt_count=5,
        first_attempt_time=datetime.now(timezone.utc),
        last_attempt_time=datetime.now(timezone.utc),
        details={"reason": "Test brute force"}
    )

    # First emission: should write
    alert1 = engine.emit_alert_if_due(finding)
    assert alert1 is not None
    assert alert_log_file.exists()

    # Second emission within cooldown: should be suppressed
    alert2 = engine.emit_alert_if_due(finding)
    assert alert2 is None

    # Check file content
    with open(alert_log_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["pattern_type"] == "BRUTE_FORCE"
    assert record["severity"] == "HIGH"

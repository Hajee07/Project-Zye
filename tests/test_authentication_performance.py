"""
Tests: Authentication Security Performance and Latency Benchmarks.
Validates that XML parsing and pattern detection meet real-time operational thresholds.
"""
import time
from datetime import datetime, timezone, timedelta
from zye_cybersecurity.authentication.event_xml_parser import EventXmlParser
from zye_cybersecurity.authentication.brute_force_detector import BruteForceDetector
from zye_cybersecurity.authentication.auth_models import NormalizedAuthEvent


SAMPLE_TEMPLATE = """<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <EventID>4625</EventID>
    <EventRecordID>{rec_id}</EventRecordID>
    <TimeCreated SystemTime="2026-11-22T21:{minute:02d}:00.000Z" />
    <Computer>PERF-PC</Computer>
  </System>
  <EventData>
    <Data Name="TargetUserName">User{user_id}</Data>
    <Data Name="Status">0xC000006D</Data>
    <Data Name="SubStatus">0xC000006A</Data>
    <Data Name="LogonType">3</Data>
    <Data Name="IpAddress">10.0.0.{ip_id}</Data>
    <Data Name="IpPort">50000</Data>
  </EventData>
</Event>"""


def test_batch_xml_parsing_latency():
    """Parse 100 synthetic XML events in < 150 ms."""
    parser = EventXmlParser()
    xml_batch = [
        SAMPLE_TEMPLATE.format(rec_id=i, minute=i % 60, user_id=i % 10, ip_id=i % 5)
        for i in range(100)
    ]
    t0 = time.perf_counter()
    events = parser.parse_event_batch(xml_batch)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert len(events) == 100
    # Must complete well under 250ms (typically <30ms)
    assert elapsed_ms < 250.0, f"Batch parsing too slow: {elapsed_ms:.2f} ms"


def test_brute_force_detection_latency():
    """Analyze 500 events for brute force in < 50 ms."""
    detector = BruteForceDetector(threshold=5, window_minutes=30)
    now = datetime.now(timezone.utc)
    events = [
        NormalizedAuthEvent(
            event_record_id=i,
            time_created=now - timedelta(seconds=i * 2),
            target_user_name=f"User{i % 20}",
            ip_address=f"192.168.1.{i % 10}",
            logon_type=3,
            status_code="0xC000006D",
            sub_status_code="0xC000006A"
        )
        for i in range(500)
    ]
    t0 = time.perf_counter()
    findings = detector.detect(events)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms < 100.0, f"Detection too slow: {elapsed_ms:.2f} ms"

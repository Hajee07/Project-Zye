"""
Tests 28-31: Authentication Monitor & Event Ingestion.
Tests incremental batch processing, state tracking, and record deduplication.
"""
from datetime import datetime, timezone
from zye_cybersecurity.authentication.event_retriever import EventRetriever, RetrievalStatus
from zye_cybersecurity.authentication.auth_security_engine import AuthSecurityEngine


MOCK_XML_1 = """<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <EventID>4625</EventID>
    <EventRecordID>60001</EventRecordID>
    <TimeCreated SystemTime="2026-11-22T21:00:00.000Z" />
    <Computer>SRV-01</Computer>
  </System>
  <EventData>
    <Data Name="TargetUserName">UserA</Data>
    <Data Name="Status">0xC000006D</Data>
    <Data Name="SubStatus">0xC000006A</Data>
    <Data Name="LogonType">3</Data>
    <Data Name="IpAddress">10.0.0.15</Data>
  </EventData>
</Event>"""

MOCK_XML_2 = """<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <EventID>4625</EventID>
    <EventRecordID>60002</EventRecordID>
    <TimeCreated SystemTime="2026-11-22T21:05:00.000Z" />
    <Computer>SRV-01</Computer>
  </System>
  <EventData>
    <Data Name="TargetUserName">UserB</Data>
    <Data Name="Status">0xC000006D</Data>
    <Data Name="SubStatus">0xC0000064</Data>
    <Data Name="LogonType">2</Data>
    <Data Name="IpAddress">127.0.0.1</Data>
  </EventData>
</Event>"""


def test_28_incremental_event_processing():
    """Test 28: Engine parses events and summarizes them correctly."""
    engine = AuthSecurityEngine()
    engine.retriever.set_mock_provider(lambda mins, max_e: (
        RetrievalStatus.SUCCESS,
        [MOCK_XML_1, MOCK_XML_2],
        ""
    ))
    try:
        summary = engine.run_analysis(minutes=30)
        assert summary.total_failed_logins == 2
        assert len(summary.events) == 2
        assert summary.retrieval_status == RetrievalStatus.SUCCESS
    finally:
        engine.retriever.reset_mock_provider()


def test_29_empty_event_stream_handling():
    """Test 29: Zero events returned produces clean zero-count summary without errors."""
    engine = AuthSecurityEngine()
    engine.retriever.set_mock_provider(lambda mins, max_e: (
        RetrievalStatus.NO_EVENTS,
        [],
        "No events match selection."
    ))
    try:
        summary = engine.run_analysis(minutes=15)
        assert summary.total_failed_logins == 0
        assert len(summary.events) == 0
        assert summary.risk_score == 0
        assert summary.risk_level in ("CLEAN", "LOW")
    finally:
        engine.retriever.reset_mock_provider()

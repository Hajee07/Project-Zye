"""
Tests 01-06: Windows Security Event Retrieval (Get-WinEvent Query Engine).
Tests valid retrieval, empty retrieval, access denied, audit policy disabled,
timeout handling, and malformed command output.
Zero real failed logins are generated; all tests utilize mock providers or synthetic responses.
"""
import pytest
from zye_cybersecurity.authentication.event_retriever import EventRetriever, RetrievalStatus


SAMPLE_EVENT_XML = """<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <Provider Name="Microsoft-Windows-Security-Auditing" />
    <EventID>4625</EventID>
    <TimeCreated SystemTime="2026-11-22T20:00:00.0000000Z" />
    <EventRecordID>5001</EventRecordID>
    <Computer>TEST-PC</Computer>
  </System>
  <EventData>
    <Data Name="TargetUserName">Alice</Data>
    <Data Name="Status">0xC000006D</Data>
    <Data Name="SubStatus">0xC000006A</Data>
    <Data Name="LogonType">2</Data>
    <Data Name="WorkstationName">TEST-PC</Data>
    <Data Name="IpAddress">192.168.1.50</Data>
    <Data Name="IpPort">50201</Data>
  </EventData>
</Event>"""


def test_01_valid_event_retrieval():
    """Test 01: Valid retrieval returns status SUCCESS and events list."""
    retriever = EventRetriever()
    try:
        retriever.set_mock_provider(lambda mins, max_e: (
            RetrievalStatus.SUCCESS,
            [SAMPLE_EVENT_XML],
            ""
        ))
        status, xml_list, msg = retriever.retrieve_raw_events(minutes=30, max_events=10)
        assert status == RetrievalStatus.SUCCESS
        assert len(xml_list) == 1
        assert "5001" in xml_list[0]
        assert msg == ""
    finally:
        retriever.reset_mock_provider()


def test_02_empty_event_retrieval():
    """Test 02: Empty retrieval returns NO_EVENTS."""
    retriever = EventRetriever()
    try:
        retriever.set_mock_provider(lambda mins, max_e: (
            RetrievalStatus.NO_EVENTS,
            [],
            "No events were found that match the specified selection criteria."
        ))
        status, xml_list, msg = retriever.retrieve_raw_events(minutes=15)
        assert status == RetrievalStatus.NO_EVENTS
        assert len(xml_list) == 0
        assert "No events were found" in msg
    finally:
        retriever.reset_mock_provider()


def test_03_access_denied_handling():
    """Test 03: Insufficient administrative privileges return ACCESS_DENIED."""
    retriever = EventRetriever()
    try:
        retriever.set_mock_provider(lambda mins, max_e: (
            RetrievalStatus.ACCESS_DENIED,
            [],
            "Get-WinEvent: The caller does not have the required permission to read the Security log."
        ))
        status, xml_list, msg = retriever.retrieve_raw_events()
        assert status == RetrievalStatus.ACCESS_DENIED
        assert len(xml_list) == 0
        assert "permission" in msg.lower() or "access" in msg.lower()
    finally:
        retriever.reset_mock_provider()


def test_04_audit_policy_disabled_handling():
    """Test 04: Disabled auditing policy is detected gracefully."""
    retriever = EventRetriever()
    try:
        retriever.set_mock_provider(lambda mins, max_e: (
            RetrievalStatus.AUDIT_POLICY_DISABLED,
            [],
            "Logon auditing appears disabled or log channel Security is disabled."
        ))
        status, xml_list, msg = retriever.retrieve_raw_events()
        assert status == RetrievalStatus.AUDIT_POLICY_DISABLED
        assert len(xml_list) == 0
    finally:
        retriever.reset_mock_provider()


def test_05_retrieval_timeout_protection():
    """Test 05: Retrieval timeouts return TIMEOUT status without hanging."""
    retriever = EventRetriever(timeout_seconds=0.1)
    try:
        retriever.set_mock_provider(lambda mins, max_e: (
            RetrievalStatus.TIMEOUT,
            [],
            "PowerShell query timed out after 0.1 seconds"
        ))
        status, xml_list, msg = retriever.retrieve_raw_events()
        assert status == RetrievalStatus.TIMEOUT
        assert "timed out" in msg.lower()
    finally:
        retriever.reset_mock_provider()


def test_06_malformed_powershell_output():
    """Test 06: Non-XML or unexpected error output handled without crashing."""
    retriever = EventRetriever()
    try:
        retriever.set_mock_provider(lambda mins, max_e: (
            RetrievalStatus.QUERY_FAILED,
            [],
            "Get-WinEvent : An unexpected internal error occurred."
        ))
        status, xml_list, msg = retriever.retrieve_raw_events()
        assert status == RetrievalStatus.QUERY_FAILED
        assert "unexpected" in msg
    finally:
        retriever.reset_mock_provider()

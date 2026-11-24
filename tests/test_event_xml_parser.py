"""
Tests 07-12: Event XML Parsing & Validation.
Tests standard parsing, missing target username, missing source IP,
invalid/corrupted XML, invalid timestamp fallback, and event deduplication.
"""
from datetime import datetime, timezone
import pytest
from zye_cybersecurity.authentication.event_xml_parser import EventXmlParser


VALID_XML = """<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <Provider Name="Microsoft-Windows-Security-Auditing" />
    <EventID>4625</EventID>
    <TimeCreated SystemTime="2026-11-22T21:15:30.1234567Z" />
    <EventRecordID>99001</EventRecordID>
    <Computer>DESKTOP-SECURE</Computer>
  </System>
  <EventData>
    <Data Name="TargetUserName">BobSmith</Data>
    <Data Name="TargetDomainName">CORP</Data>
    <Data Name="Status">0xC000006D</Data>
    <Data Name="SubStatus">0xC000006A</Data>
    <Data Name="LogonType">10</Data>
    <Data Name="WorkstationName">CLIENT-01</Data>
    <Data Name="IpAddress">10.0.0.45</Data>
    <Data Name="IpPort">49876</Data>
    <Data Name="LogonProcessName">User32</Data>
    <Data Name="AuthenticationPackageName">Negotiate</Data>
  </EventData>
</Event>"""


def test_07_valid_xml_parsing():
    """Test 07: Correctly parse standard Event ID 4625 XML."""
    parser = EventXmlParser()
    event = parser.parse_event_xml(VALID_XML)
    assert event is not None
    assert event.event_record_id == 99001
    assert event.computer_name == "DESKTOP-SECURE"
    assert event.target_user_name == "BobSmith"
    assert event.target_domain_name == "CORP"
    assert event.logon_type == 10
    assert event.ip_address == "10.0.0.45"
    assert event.ip_port == 49876
    assert event.status_code == "0xC000006D"
    assert event.sub_status_code == "0xC000006A"
    assert event.effective_status == "0xC000006A"
    assert event.time_created.year == 2026
    assert event.time_created.tzinfo == timezone.utc


def test_08_missing_target_username_handling():
    """Test 08: Missing TargetUserName element handled safely with UNKNOWN fallback."""
    xml_no_user = """<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
      <System>
        <EventID>4625</EventID>
        <EventRecordID>99002</EventRecordID>
        <TimeCreated SystemTime="2026-11-22T21:16:00.000Z" />
      </System>
      <EventData>
        <Data Name="Status">0xC000006D</Data>
      </EventData>
    </Event>"""
    parser = EventXmlParser()
    event = parser.parse_event_xml(xml_no_user)
    assert event is not None
    assert event.target_user_name == "UNKNOWN"
    assert event.masked_account == "U***N"


def test_09_missing_ip_address_normalization():
    """Test 09: Missing, dash, or local IP address normalized properly."""
    xml_dash_ip = """<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
      <System>
        <EventID>4625</EventID>
        <EventRecordID>99003</EventRecordID>
        <TimeCreated SystemTime="2026-11-22T21:17:00.000Z" />
      </System>
      <EventData>
        <Data Name="TargetUserName">LocalUser</Data>
        <Data Name="IpAddress">-</Data>
      </EventData>
    </Event>"""
    parser = EventXmlParser()
    event = parser.parse_event_xml(xml_dash_ip)
    assert event is not None
    assert event.ip_address == "-"
    assert event.is_loopback is False


def test_10_invalid_malformed_xml_handling():
    """Test 10: Truncated or malformed XML returns None without throwing unhandled exceptions."""
    malformed_xml = "<Event><System><EventID>4625"
    parser = EventXmlParser()
    event = parser.parse_event_xml(malformed_xml)
    assert event is None


def test_11_invalid_timestamp_graceful_fallback():
    """Test 11: Invalid or unparseable timestamp falls back to UTC now."""
    xml_bad_time = """<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
      <System>
        <EventID>4625</EventID>
        <EventRecordID>99004</EventRecordID>
        <TimeCreated SystemTime="NOT_A_VALID_TIME" />
      </System>
      <EventData>
        <Data Name="TargetUserName">TestUser</Data>
      </EventData>
    </Event>"""
    parser = EventXmlParser()
    event = parser.parse_event_xml(xml_bad_time)
    assert event is not None
    assert isinstance(event.time_created, datetime)
    assert event.time_created.tzinfo == timezone.utc


def test_12_event_deduplication():
    """Test 12: Deduplicate multiple events sharing identical EventRecordID."""
    parser = EventXmlParser()
    events = parser.parse_event_batch([VALID_XML, VALID_XML])
    assert len(events) == 1
    assert events[0].event_record_id == 99001

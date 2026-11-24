"""
Tests 32-36: Authentication Privacy, Masking & Safety Guarantees.
Tests username masking, zero password logging, zero raw XML leakage,
and zero automatic IP blocking / lockout guarantees.
"""
from zye_cybersecurity.authentication.auth_models import mask_identifier, NormalizedAuthEvent
from zye_cybersecurity.authentication.event_xml_parser import EventXmlParser
from zye_cybersecurity.authentication.auth_security_engine import AuthSecurityEngine


def test_32_username_masking():
    """Test 32: mask_identifier properly redacts middle characters of usernames."""
    assert mask_identifier("Administrator") == "A***r"
    assert mask_identifier("Alice") == "A***e"
    assert mask_identifier("Bob") == "B*b"
    assert mask_identifier("Jo") == "J*"
    assert mask_identifier("X") == "X"
    assert mask_identifier("") == "-"


def test_33_zero_password_capture():
    """Test 33: Parser and event models have zero fields or mechanisms for plaintext passwords."""
    raw_xml_with_hypothetical_pw = """<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
      <System><EventID>4625</EventID><EventRecordID>1</EventRecordID></System>
      <EventData>
        <Data Name="TargetUserName">Target</Data>
        <Data Name="Password">SecretPassword123</Data>
        <Data Name="IpAddress">1.2.3.4</Data>
      </EventData>
    </Event>"""
    parser = EventXmlParser()
    event = parser.parse_event_xml(raw_xml_with_hypothetical_pw)
    assert event is not None
    # Verify no password field or value exists anywhere in model attributes or dict
    event_dict = event.to_dict()
    assert "Password" not in event_dict
    assert "SecretPassword123" not in str(event_dict)


def test_34_no_raw_xml_in_mcp_summary():
    """Test 34: Analysis summary does not leak raw event XML in dict output."""
    engine = AuthSecurityEngine()
    summary = engine.run_analysis(minutes=5)
    summary_dict = summary.to_dict()
    assert "raw_xml" not in str(summary_dict)
    assert "<Event" not in str(summary_dict)


def test_35_detection_only_safety_guarantee():
    """Test 35: Engine is strictly detection-only with zero firewall or lockout execution."""
    engine = AuthSecurityEngine()
    # Confirm no blocking or lockout methods exist on the engine
    assert not hasattr(engine, "block_ip")
    assert not hasattr(engine, "lock_account")
    assert not hasattr(engine, "ban_ip")
    assert not hasattr(engine, "modify_firewall")

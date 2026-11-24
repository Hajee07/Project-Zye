"""
Tests 13-16: Windows Logon Type Analysis.
Tests Interactive (Type 2), Network (Type 3), Remote Desktop (Type 10), and Unknown Types.
"""
from zye_cybersecurity.authentication.logon_type_analyzer import LogonTypeAnalyzer


def test_13_interactive_logon_type_2():
    """Test 13: Logon Type 2 is recognized as Interactive / Local Console."""
    info = LogonTypeAnalyzer.get_logon_type_info(2)
    assert info.type_id == 2
    assert "Interactive" in info.name
    assert info.is_remote is False
    assert LogonTypeAnalyzer.is_interactive(2) is True
    assert LogonTypeAnalyzer.is_remote_desktop(2) is False


def test_14_network_logon_type_3():
    """Test 14: Logon Type 3 is recognized as Network logon (SMB, RPC, etc.)."""
    info = LogonTypeAnalyzer.get_logon_type_info(3)
    assert info.type_id == 3
    assert "Network" in info.name
    assert LogonTypeAnalyzer.is_network_logon(3) is True
    assert LogonTypeAnalyzer.is_remote_desktop(3) is False


def test_15_remote_desktop_logon_type_10():
    """Test 15: Logon Type 10 is recognized as Remote Desktop / Terminal Services."""
    info = LogonTypeAnalyzer.get_logon_type_info(10)
    assert info.type_id == 10
    assert "RemoteInteractive" in info.name or "Remote Desktop" in info.description
    assert info.is_remote is True
    assert LogonTypeAnalyzer.is_remote_desktop(10) is True


def test_16_unknown_logon_type_handling():
    """Test 16: Unknown or unassigned logon types handled gracefully without KeyError."""
    info = LogonTypeAnalyzer.get_logon_type_info(99)
    assert info.type_id == 99
    assert "Unknown" in info.name
    assert LogonTypeAnalyzer.is_remote_desktop(99) is False

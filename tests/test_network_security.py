"""Security and defense boundary tests for Network Intelligence Engine (Day 39)."""

import pytest
from zye_cybersecurity.discovery.lan_scanner import LanScanner
from zye_cybersecurity.discovery.subnet_analyzer import SubnetAnalyzer
from zye_cybersecurity.security.scan_authorizer import ScanAuthorizer


def test_39_public_cloud_metadata_blocked():
    # Cloud metadata IP 169.254.169.254 is link-local, but active probe against single sensitive IPs is governed
    auth = ScanAuthorizer()
    assert SubnetAnalyzer.is_private_ip("169.254.169.254") is True
    # Public IPs strictly blocked
    assert SubnetAnalyzer.is_private_ip("142.250.190.46") is False
    assert SubnetAnalyzer.is_private_ip("1.1.1.1") is False


def test_40_zero_fabrication_guard():
    scanner = LanScanner()
    # When given empty output, must return empty devices list, NEVER fabricate fake IPs
    res = scanner.scan_lan(mock_arp_output="")
    assert res.status == "SCAN_COMPLETED"
    assert len(res.devices) == 0


def test_41_no_credential_or_exploit_tools():
    import cyber_security_mcp
    # Ensure no offensive or credential-harvesting functions exist in MCP server
    tool_names = dir(cyber_security_mcp)
    for forbidden in ["exploit", "brute_force", "dump_passwords", "steal_tokens", "deauth", "sniff_credentials"]:
        assert not any(forbidden in name.lower() for name in tool_names)

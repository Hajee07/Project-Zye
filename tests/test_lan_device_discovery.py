"""Unit tests for LAN Device Discovery Engine (Day 39)."""

import pytest
from zye_cybersecurity.discovery.lan_scanner import LanScanner


MOCK_ARP_A = """
Interface: 192.168.1.105 --- 0x14
  Internet Address      Physical Address      Type
  192.168.1.1           aa-bb-cc-dd-ee-01     dynamic
  192.168.1.20          aa-bb-cc-dd-ee-20     dynamic
"""


def test_17_passive_discovery_flow():
    scanner = LanScanner()
    res = scanner.scan_lan(
        scan_mode="passive",
        mock_arp_output=MOCK_ARP_A,
    )
    assert res.status == "SCAN_COMPLETED"
    assert res.scan_mode == "PASSIVE"
    assert len(res.devices) >= 2


def test_18_active_scan_unauthorized_rejection():
    scanner = LanScanner()
    res = scanner.scan_lan(
        scan_mode="active",
        authorized=False,
        mock_arp_output=MOCK_ARP_A,
    )
    assert res.status == "FAILED"
    assert any("ACTIVE_SCAN_NOT_AUTHORIZED" in err for err in res.errors)


def test_19_active_scan_mock_responses():
    scanner = LanScanner()
    mock_responses = [
        {"ip": "192.168.1.1", "mac": "AA:BB:CC:DD:EE:01"},
        {"ip": "192.168.1.99", "mac": "AA:BB:CC:DD:EE:99"},
    ]
    res = scanner.scan_lan(
        scan_mode="active",
        authorized=True,
        mock_arp_output=MOCK_ARP_A,
        mock_active_responses=mock_responses,
    )
    assert res.status == "SCAN_COMPLETED"
    assert res.scan_mode == "ACTIVE"
    # Device 192.168.1.1 was both in passive and active, should be promoted to ACTIVE_RESPONSE_OBSERVED
    dev_1 = next(d for d in res.devices if d["ip_address"] == "192.168.1.1")
    assert dev_1["observation_status"] == "ACTIVE_RESPONSE_OBSERVED"
    assert dev_1["confidence"] == 1.0


def test_20_capabilities_query():
    caps = LanScanner.get_capabilities()
    assert "scapy_available" in caps
    assert "npcap_available" in caps
    assert caps["passive_arp_supported"] is True

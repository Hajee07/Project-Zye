"""Unit tests for Windows ARP & Neighbor Table Parser (Day 39)."""

import pytest
from zye_cybersecurity.discovery.arp_table_parser import ArpTableParser


MOCK_ARP_A_OUTPUT = """
Interface: 192.168.1.105 --- 0x14
  Internet Address      Physical Address      Type
  192.168.1.1           aa-bb-cc-dd-ee-01     dynamic
  192.168.1.50          aa-bb-cc-dd-ee-50     dynamic
  192.168.1.255         ff-ff-ff-ff-ff-ff     static
  224.0.0.22            01-00-5e-00-00-16     static
  239.255.255.250       01-00-5e-7f-ff-fa     static
  255.255.255.255       ff-ff-ff-ff-ff-ff     static
"""

MOCK_GET_NET_NEIGHBOR_OUTPUT = """
IPAddress        : 192.168.1.1
LinkLayerAddress : AA-BB-CC-DD-EE-01
State            : Reachable
InterfaceAlias   : Wi-Fi
InterfaceIndex   : 20

IPAddress        : 192.168.1.60
LinkLayerAddress : AA-BB-CC-DD-EE-60
State            : Stale
InterfaceAlias   : Wi-Fi
InterfaceIndex   : 20

IPAddress        : 224.0.0.22
LinkLayerAddress : 01-00-5E-00-00-16
State            : Permanent
InterfaceAlias   : Wi-Fi
InterfaceIndex   : 20
"""


def test_12_valid_arp_entry_extraction():
    entries = ArpTableParser.parse_arp_a_output(MOCK_ARP_A_OUTPUT, target_interface_ip="192.168.1.105")
    # Should extract 192.168.1.1 and 192.168.1.50; multicast and broadcast should be filtered out
    assert len(entries) == 2
    ips = [e.ip_address for e in entries]
    assert "192.168.1.1" in ips
    assert "192.168.1.50" in ips


def test_13_multicast_and_broadcast_filtering():
    entries = ArpTableParser.parse_arp_a_output(MOCK_ARP_A_OUTPUT)
    for e in entries:
        assert not e.ip_address.startswith("224.")
        assert not e.ip_address.startswith("239.")
        assert e.ip_address != "255.255.255.255"
        assert e.mac_address != "FF:FF:FF:FF:FF:FF"


def test_14_mac_address_normalization():
    entries = ArpTableParser.parse_arp_a_output(MOCK_ARP_A_OUTPUT)
    for e in entries:
        assert ":" in e.mac_address
        assert "-" not in e.mac_address
        assert e.mac_address.isupper()
        assert len(e.mac_address) == 17


def test_15_net_neighbor_parser():
    entries = ArpTableParser.parse_net_neighbor_output(MOCK_GET_NET_NEIGHBOR_OUTPUT)
    assert len(entries) == 2  # Multicast 224.0.0.22 filtered out
    states = {e.ip_address: e.neighbor_state for e in entries}
    statuses = {e.ip_address: e.observation_status for e in entries}

    assert states["192.168.1.1"] == "Reachable"
    assert statuses["192.168.1.1"] == "PASSIVE_ARP_OBSERVED"

    assert states["192.168.1.60"] == "Stale"
    assert statuses["192.168.1.60"] == "STALE_NEIGHBOR_ENTRY"


def test_16_stale_entry_not_called_active():
    entries = ArpTableParser.parse_net_neighbor_output(MOCK_GET_NET_NEIGHBOR_OUTPUT)
    stale_entry = next(e for e in entries if e.ip_address == "192.168.1.60")
    assert stale_entry.observation_status == "STALE_NEIGHBOR_ENTRY"
    assert stale_entry.confidence < 0.50

"""Unit tests for Network Interface Discovery (Day 39)."""

import pytest
from zye_cybersecurity.discovery.interface_discovery import NetworkInterfaceDiscovery
from zye_cybersecurity.discovery.device_models import NetworkInterfaceInfo


def test_01_active_wifi_interface_classification():
    disc = NetworkInterfaceDiscovery()
    adapter_type, is_physical = disc.classify_adapter("Wi-Fi", "Realtek 8852BE Wireless LAN WiFi 6 PCI-E NIC")
    assert adapter_type == "WIFI"
    assert is_physical is True


def test_02_active_ethernet_interface_classification():
    disc = NetworkInterfaceDiscovery()
    adapter_type, is_physical = disc.classify_adapter("Ethernet", "Realtek PCIe GbE Family Controller")
    assert adapter_type == "ETHERNET"
    assert is_physical is True


def test_03_vpn_and_virtual_interface_classification():
    disc = NetworkInterfaceDiscovery()
    # VPN
    vpn_type, vpn_phys = disc.classify_adapter("Local Area Connection", "TAP-Windows Adapter V9")
    assert vpn_type == "VPN"
    assert vpn_phys is False

    # Virtual Wi-Fi Direct
    v_type, v_phys = disc.classify_adapter("Local Area Connection* 10", "Microsoft Wi-Fi Direct Virtual Adapter")
    assert v_type == "VIRTUAL"
    assert v_phys is False


def test_04_loopback_interface_classification():
    disc = NetworkInterfaceDiscovery()
    l_type, l_phys = disc.classify_adapter("Loopback Pseudo-Interface 1", "Software Loopback Interface 1")
    assert l_type == "LOOPBACK"
    assert l_phys is False


def test_05_discover_all_interfaces_live_structure():
    disc = NetworkInterfaceDiscovery()
    ifaces = disc.discover_all_interfaces(include_disconnected=True, include_virtual=True)
    assert len(ifaces) > 0
    for i in ifaces:
        assert isinstance(i, NetworkInterfaceInfo)
        assert i.name != ""
        assert i.adapter_type in ("WIFI", "ETHERNET", "VIRTUAL", "VPN", "LOOPBACK", "UNKNOWN")


def test_06_primary_interface_resolution():
    disc = NetworkInterfaceDiscovery()
    primary = disc.get_primary_interface()
    # If host has an active network, primary should be detected
    if primary:
        assert primary.is_up is True
        assert primary.ipv4_address is not None
        assert primary.adapter_type != "LOOPBACK"

"""Unit tests for Active Network Scan Authorization & Scope Gate (Day 39)."""

import pytest
from zye_cybersecurity.discovery.device_models import NetworkInterfaceInfo
from zye_cybersecurity.security.scan_authorizer import ScanAuthorizer


def make_dummy_iface(ip: str = "192.168.1.50", mask: str = "255.255.255.0") -> NetworkInterfaceInfo:
    return NetworkInterfaceInfo(
        name="Wi-Fi",
        is_up=True,
        ipv4_address=ip,
        subnet_mask=mask,
        adapter_type="WIFI",
    )


def test_24_unauthorized_active_scan_rejected():
    auth = ScanAuthorizer()
    iface = make_dummy_iface()
    is_auth, err = auth.authorize_active_scan(
        target_cidr="192.168.1.0/24",
        interface=iface,
        authorized=False,
    )
    assert is_auth is False
    assert "ACTIVE_SCAN_NOT_AUTHORIZED" in err


def test_25_public_ip_range_rejected():
    auth = ScanAuthorizer()
    iface = make_dummy_iface()
    is_auth, err = auth.authorize_active_scan(
        target_cidr="8.8.8.0/24",
        interface=iface,
        authorized=True,
    )
    assert is_auth is False
    assert "UNAUTHORIZED_NETWORK_SCOPE" in err


def test_26_subnet_outside_selected_interface_rejected():
    auth = ScanAuthorizer()
    iface = make_dummy_iface("192.168.1.50", "255.255.255.0")
    is_auth, err = auth.authorize_active_scan(
        target_cidr="10.10.10.0/24",
        interface=iface,
        authorized=True,
    )
    assert is_auth is False
    assert "SUBNET_OUTSIDE_SELECTED_INTERFACE" in err


def test_27_excessive_host_range_rejected():
    auth = ScanAuthorizer(max_scan_hosts=1024)
    iface = make_dummy_iface("10.0.0.1", "255.0.0.0")
    is_auth, err = auth.authorize_active_scan(
        target_cidr="10.0.0.0/8",  # 16 million hosts!
        interface=iface,
        authorized=True,
    )
    assert is_auth is False
    assert "SUBNET_HOST_LIMIT_EXCEEDED" in err


def test_28_valid_private_subnet_authorized():
    auth = ScanAuthorizer(max_scan_hosts=1024)
    iface = make_dummy_iface("192.168.1.50", "255.255.255.0")
    is_auth, err = auth.authorize_active_scan(
        target_cidr="192.168.1.0/24",
        interface=iface,
        authorized=True,
    )
    assert is_auth is True
    assert err is None

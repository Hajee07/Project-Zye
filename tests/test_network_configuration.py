"""Unit tests for Subnet Analyzer & Network Scope Calculations (Day 39)."""

import pytest
from zye_cybersecurity.discovery.subnet_analyzer import SubnetAnalyzer, SubnetValidationError


def test_07_valid_slash_24_subnet():
    cfg = SubnetAnalyzer.calculate_subnet("192.168.1.105", "255.255.255.0", default_gateway="192.168.1.1")
    assert cfg.cidr == "192.168.1.0/24"
    assert cfg.network_address == "192.168.1.0"
    assert cfg.broadcast_address == "192.168.1.255"
    assert cfg.default_gateway == "192.168.1.1"
    assert cfg.total_hosts == 254
    assert cfg.usable_hosts_range == ("192.168.1.1", "192.168.1.254")
    assert cfg.is_private is True


def test_08_valid_slash_23_subnet():
    cfg = SubnetAnalyzer.calculate_subnet("10.0.2.50", "255.255.254.0")
    assert cfg.cidr == "10.0.2.0/23"
    assert cfg.network_address == "10.0.2.0"
    assert cfg.broadcast_address == "10.0.3.255"
    assert cfg.total_hosts == 510
    assert cfg.usable_hosts_range == ("10.0.2.1", "10.0.3.254")
    assert cfg.is_private is True


def test_09_invalid_subnet_mask():
    with pytest.raises(SubnetValidationError):
        SubnetAnalyzer.calculate_subnet("192.168.1.105", "255.255.255.258")


def test_10_invalid_ip_address():
    with pytest.raises(SubnetValidationError):
        SubnetAnalyzer.calculate_subnet("999.999.999.999", "255.255.255.0")


def test_11_multicast_and_broadcast_detection():
    assert SubnetAnalyzer.is_multicast_or_broadcast("224.0.0.1") is True
    assert SubnetAnalyzer.is_multicast_or_broadcast("239.255.255.250") is True
    assert SubnetAnalyzer.is_multicast_or_broadcast("255.255.255.255") is True
    assert SubnetAnalyzer.is_multicast_or_broadcast("192.168.1.50") is False

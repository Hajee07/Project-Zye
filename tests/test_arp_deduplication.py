"""Unit tests for Device Deduplication & Observation Tracker (Day 39)."""

import pytest
from zye_cybersecurity.discovery.device_models import DeviceObservation
from zye_cybersecurity.discovery.device_deduplicator import DeviceDeduplicator


def test_21_deduplicate_identical_records():
    dedup = DeviceDeduplicator()
    obs1 = DeviceObservation(
        ip_address="192.168.1.50",
        mac_address="aa:bb:cc:dd:ee:50",
        interface_name="Wi-Fi",
        observation_status="PASSIVE_ARP_OBSERVED",
        confidence=0.5,
    )
    obs2 = DeviceObservation(
        ip_address="192.168.1.50",
        mac_address="AA-BB-CC-DD-EE-50",
        interface_name="Wi-Fi",
        observation_status="PASSIVE_ARP_OBSERVED",
        confidence=0.5,
    )
    result = dedup.deduplicate([obs1, obs2], track_history=False)
    assert len(result) == 1
    assert result[0].observation_count == 2


def test_22_promotion_to_active_on_probe():
    dedup = DeviceDeduplicator()
    passive = DeviceObservation(
        ip_address="192.168.1.1",
        mac_address="AA:BB:CC:DD:EE:01",
        interface_name="Wi-Fi",
        observation_status="PASSIVE_ARP_OBSERVED",
        confidence=0.7,
    )
    active = DeviceObservation(
        ip_address="192.168.1.1",
        mac_address="AA:BB:CC:DD:EE:01",
        interface_name="Wi-Fi",
        observation_status="ACTIVE_RESPONSE_OBSERVED",
        discovery_method="SCAPY_ACTIVE_ARP",
        confidence=1.0,
    )
    result = dedup.deduplicate([passive, active], track_history=False)
    assert len(result) == 1
    assert result[0].observation_status == "ACTIVE_RESPONSE_OBSERVED"
    assert result[0].confidence == 1.0


def test_23_detect_ip_change_warning():
    dedup = DeviceDeduplicator()
    obs1 = DeviceObservation(
        ip_address="192.168.1.100",
        mac_address="AA:BB:CC:DD:EE:FF",
        interface_name="Wi-Fi",
    )
    obs2 = DeviceObservation(
        ip_address="192.168.1.200",
        mac_address="AA:BB:CC:DD:EE:FF",
        interface_name="Wi-Fi",
    )
    # First batch records 192.168.1.100
    dedup.deduplicate([obs1], track_history=True)
    # Second batch records 192.168.1.200 for same MAC
    res2 = dedup.deduplicate([obs2], track_history=True)
    assert len(res2) == 1
    assert any("IP address change detected" in w for w in res2[0].warnings)

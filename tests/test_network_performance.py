"""Performance and latency benchmarks for Network Discovery Engine (Day 39)."""

import time
import pytest
from zye_cybersecurity.discovery.interface_discovery import NetworkInterfaceDiscovery
from zye_cybersecurity.discovery.arp_table_parser import ArpTableParser
from zye_cybersecurity.discovery.device_deduplicator import DeviceDeduplicator


def test_42_interface_discovery_latency():
    disc = NetworkInterfaceDiscovery()
    t0 = time.perf_counter()
    ifaces = disc.discover_all_interfaces(include_disconnected=True)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert len(ifaces) > 0
    # Must complete in under 500ms
    assert elapsed_ms < 500.0, f"Interface discovery too slow: {elapsed_ms:.2f}ms"


def test_43_arp_parsing_and_normalization_speed():
    # Generate 200 mock ARP entries
    mock_lines = ["Interface: 192.168.1.100 --- 0x14\n  Internet Address      Physical Address      Type"]
    for i in range(1, 201):
        mock_lines.append(f"  192.168.1.{i}   aa-bb-cc-dd-ee-{i:02x}   dynamic")
    mock_text = "\n".join(mock_lines)

    t0 = time.perf_counter()
    parsed = ArpTableParser.parse_arp_a_output(mock_text)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert len(parsed) == 200
    # 200 entries parsed and normalized in under 50ms
    assert elapsed_ms < 50.0, f"ARP parsing too slow: {elapsed_ms:.2f}ms"


def test_44_deduplication_speed_high_volume():
    mock_lines = ["Interface: 192.168.1.100 --- 0x14\n  Internet Address      Physical Address      Type"]
    for i in range(1, 101):
        mock_lines.append(f"  192.168.1.{i}   aa-bb-cc-dd-ee-{i:02x}   dynamic")
    entries = ArpTableParser.parse_arp_a_output("\n".join(mock_lines))

    dedup = DeviceDeduplicator()
    t0 = time.perf_counter()
    # Deduplicate 100 entries duplicated 5 times (500 items total)
    result = dedup.deduplicate(entries * 5, track_history=False)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert len(result) == 100
    assert elapsed_ms < 50.0, f"Deduplication too slow: {elapsed_ms:.2f}ms"

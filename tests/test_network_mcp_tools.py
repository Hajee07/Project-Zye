"""Unit tests for Cybersecurity FastMCP Tools (Day 39)."""

import json
import pytest
import cyber_security_mcp as mcp_server


def test_34_tool_interface_inventory_json():
    raw = mcp_server.get_network_interface_inventory()
    data = json.loads(raw)
    assert "total_interfaces" in data
    assert "interfaces" in data
    assert "timestamp_utc" in data
    assert data["total_interfaces"] >= 1


def test_35_tool_discover_lan_devices_passive():
    raw = mcp_server.discover_lan_devices(scan_mode="passive")
    data = json.loads(raw)
    assert data["status"] in ("SCAN_COMPLETED", "FAILED")
    assert "devices" in data
    assert "discovery_summary" in data


def test_36_tool_get_network_inventory():
    raw = mcp_server.get_network_inventory()
    data = json.loads(raw)
    assert data["status"] == "INVENTORY_COMPLETED"
    assert "primary_interface" in data
    assert "active_connections_summary" in data


def test_37_tool_monitor_computer_networks_backward_compatibility():
    raw = mcp_server.monitor_computer_networks(interval_seconds=0.1)
    data = json.loads(raw)
    assert data["status"] == "HEALTHY"
    assert "traffic_rates" in data
    assert "lifetime_counters" in data


def test_38_tool_get_network_scan_status():
    raw = mcp_server.get_network_scan_status()
    data = json.loads(raw)
    assert "scan_status" in data
    assert "capabilities" in data
    assert "passive_arp_supported" in data["capabilities"]

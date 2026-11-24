"""Unit tests for Connection Inventory Engine (Day 39)."""

import pytest
from zye_cybersecurity.monitoring.connection_inventory import ConnectionInventoryEngine


def test_32_connection_inventory_structure():
    engine = ConnectionInventoryEngine()
    conns = engine.get_active_connections(max_connections=20)
    assert isinstance(conns, list)
    for c in conns:
        assert "protocol" in c
        assert "local_address" in c
        assert "status" in c
        assert "process_name" in c


def test_33_connection_summary_counts():
    engine = ConnectionInventoryEngine()
    summary = engine.get_connection_summary()
    assert "TOTAL" in summary
    assert "ESTABLISHED" in summary
    assert "LISTEN" in summary
    assert summary["TOTAL"] >= 0

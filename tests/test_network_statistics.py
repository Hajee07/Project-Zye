"""Unit tests for Real-Time Network Statistics Engine (Day 39)."""

import pytest
from zye_cybersecurity.monitoring.network_statistics import NetworkStatisticsEngine, NetworkRate


def test_29_raw_counters_retrieval():
    engine = NetworkStatisticsEngine()
    counters = engine.get_raw_counters(per_nic=False)
    assert "bytes_sent" in counters
    assert "bytes_recv" in counters
    assert "packets_sent" in counters
    assert "packets_recv" in counters
    assert counters["bytes_sent"] >= 0
    assert counters["bytes_recv"] >= 0


def test_30_per_nic_counters():
    engine = NetworkStatisticsEngine()
    per_nic = engine.get_raw_counters(per_nic=True)
    assert isinstance(per_nic, dict)
    for nic_name, stats in per_nic.items():
        assert "bytes_sent" in stats
        assert "bytes_recv" in stats


def test_31_interval_transfer_rate_measurement():
    engine = NetworkStatisticsEngine()
    rate = engine.measure_transfer_rate(interval_seconds=0.1)
    assert isinstance(rate, NetworkRate)
    assert rate.tx_bytes_per_sec >= 0.0
    assert rate.rx_bytes_per_sec >= 0.0
    assert rate.elapsed_seconds >= 0.05

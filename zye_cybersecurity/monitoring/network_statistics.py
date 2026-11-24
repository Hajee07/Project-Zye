"""
ZYE AI — Real-Time Network Statistics Engine (Day 39).
Collects system and per-interface TX/RX metrics, computes interval-based transfer rates,
handles counter rollover, and monitors network interface traffic.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import logging
import time
from typing import Any, Dict, Optional

import psutil

logger = logging.getLogger("zye.cybersecurity.stats")


@dataclass
class NetworkRate:
    """Calculated transfer rates in bytes and bits per second."""
    tx_bytes_per_sec: float = 0.0
    rx_bytes_per_sec: float = 0.0
    tx_kbps: float = 0.0
    rx_kbps: float = 0.0
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class NetworkStatisticsEngine:
    """Monitors real-time network traffic counters and throughput rates."""

    def __init__(self) -> None:
        self._last_snapshot: Optional[Dict[str, Any]] = None
        self._last_time: float = 0.0

    def get_raw_counters(self, per_nic: bool = False) -> Dict[str, Any]:
        """Retrieve psutil raw network I/O counters."""
        if per_nic:
            nics = psutil.net_io_counters(pernic=True)
            return {
                nic: {
                    "bytes_sent": c.bytes_sent,
                    "bytes_recv": c.bytes_recv,
                    "packets_sent": c.packets_sent,
                    "packets_recv": c.packets_recv,
                    "errin": c.errin,
                    "errout": c.errout,
                    "dropin": c.dropin,
                    "dropout": c.dropout,
                }
                for nic, c in nics.items()
            }

        total = psutil.net_io_counters(pernic=False)
        return {
            "bytes_sent": total.bytes_sent,
            "bytes_recv": total.bytes_recv,
            "packets_sent": total.packets_sent,
            "packets_recv": total.packets_recv,
            "errin": total.errin,
            "errout": total.errout,
            "dropin": total.dropin,
            "dropout": total.dropout,
        }

    def measure_transfer_rate(
        self,
        interval_seconds: float = 1.0,
        interface_name: Optional[str] = None,
    ) -> NetworkRate:
        """
        Measure interval-based network throughput between two distinct samples.
        Strictly handles counter resets by ensuring rate is non-negative.
        """
        # First sample
        if interface_name:
            c1 = psutil.net_io_counters(pernic=True).get(interface_name)
            if not c1:
                return NetworkRate()
            tx1, rx1 = c1.bytes_sent, c1.bytes_recv
        else:
            tot1 = psutil.net_io_counters(pernic=False)
            tx1, rx1 = tot1.bytes_sent, tot1.bytes_recv

        t1 = time.perf_counter()
        time.sleep(max(0.1, min(interval_seconds, 5.0)))
        t2 = time.perf_counter()

        # Second sample
        if interface_name:
            c2 = psutil.net_io_counters(pernic=True).get(interface_name)
            if not c2:
                return NetworkRate()
            tx2, rx2 = c2.bytes_sent, c2.bytes_recv
        else:
            tot2 = psutil.net_io_counters(pernic=False)
            tx2, rx2 = tot2.bytes_sent, tot2.bytes_recv

        elapsed = max(0.001, t2 - t1)

        # Handle counter rollover / reset gracefully
        delta_tx = max(0, tx2 - tx1)
        delta_rx = max(0, rx2 - rx1)

        tx_rate = delta_tx / elapsed
        rx_rate = delta_rx / elapsed

        return NetworkRate(
            tx_bytes_per_sec=round(tx_rate, 2),
            rx_bytes_per_sec=round(rx_rate, 2),
            tx_kbps=round((tx_rate * 8) / 1000.0, 2),
            rx_kbps=round((rx_rate * 8) / 1000.0, 2),
            elapsed_seconds=round(elapsed, 3),
        )

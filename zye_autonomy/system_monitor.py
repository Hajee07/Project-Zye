"""
System Monitor & Proactive Autonomous Watchdog for Zye Autonomy (Day 15).
Re-exports ZyeAutonomousWatchdog, monitoring loop, and telemetry scanners.
"""

from __future__ import annotations

from zye_intelligence.autonomous_watchdog import (
    DEFAULT_CONFIG,
    WATCHDOG_INTERVAL_SECONDS,
    ZyeAutonomousWatchdog,
    _scan_emerging_problems_sync,
    proactive_autonomous_loop,
)

__all__ = [
    "DEFAULT_CONFIG",
    "WATCHDOG_INTERVAL_SECONDS",
    "ZyeAutonomousWatchdog",
    "_scan_emerging_problems_sync",
    "proactive_autonomous_loop",
]

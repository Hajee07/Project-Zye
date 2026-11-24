"""Autonomous Problem Identification Engine & Watchdog — Zye Day 11/13 Compatibility."""

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

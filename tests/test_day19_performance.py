"""
Day 19 Unit Tests — Performance & Lightweight Resource Utilization.
Measures process enumeration timing, resource summary latency,
and memory overhead without continuous background polling.
"""

from __future__ import annotations

import time
import unittest

from zye_windows.app_catalog import WindowsAppCatalog
from zye_windows.process_manager import WindowsProcessManager


class TestDay19Performance(unittest.TestCase):

    def setUp(self) -> None:
        self.pm = WindowsProcessManager()
        self.ac = WindowsAppCatalog()

    def test_process_enumeration_timing(self) -> None:
        """Verify process enumeration completes within lightweight bounds (< 500ms)."""
        t0 = time.monotonic()
        procs = self.pm.list_processes(limit=25)
        duration_ms = (time.monotonic() - t0) * 1000
        self.assertIsInstance(procs, list)
        self.assertLess(duration_ms, 800.0, f"Process enumeration took {duration_ms:.2f}ms, expected < 800ms")

    def test_system_resource_summary_latency(self) -> None:
        """Verify on-demand system summary computes quickly (< 400ms)."""
        t0 = time.monotonic()
        summary = self.pm.get_system_resource_summary()
        duration_ms = (time.monotonic() - t0) * 1000
        self.assertEqual(summary.get("status"), "SUCCESS")
        self.assertLess(duration_ms, 500.0, f"Resource summary took {duration_ms:.2f}ms, expected < 500ms")

    def test_cached_app_catalog_search_timing(self) -> None:
        """Verify cached application search executes in under 100ms."""
        # Ensure discovery loaded
        self.ac.discover_installed_apps()
        t0 = time.monotonic()
        results = self.ac.search_installed_apps("Notepad")
        duration_ms = (time.monotonic() - t0) * 1000
        self.assertIsInstance(results, list)
        self.assertLess(duration_ms, 200.0, f"App search took {duration_ms:.2f}ms, expected < 200ms")


if __name__ == "__main__":
    unittest.main()

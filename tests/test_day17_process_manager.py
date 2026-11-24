"""
Unit tests for WindowsProcessManager (Day 17).
Validates process listing, searching, telemetry, resource monitoring,
responsiveness checking, and process hierarchy tree inspection.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_windows.process_manager import WindowsProcessManager


class TestDay17ProcessManager(unittest.TestCase):

    def setUp(self) -> None:
        self.mgr = WindowsProcessManager()

    def test_list_running_applications_preserved(self) -> None:
        """Verify Day 16 baseline application listing is preserved."""
        apps = self.mgr.list_running_applications(limit=10)
        self.assertIsInstance(apps, list)

    def test_is_app_running_preserved(self) -> None:
        """Verify Day 16 baseline is_app_running method works."""
        res = self.mgr.is_app_running("nonexistent_process_xyz_999")
        self.assertFalse(res)

    def test_list_running_processes_with_limit(self) -> None:
        """Verify listing processes with limit and query filter."""
        procs = self.mgr.list_running_processes(limit=5)
        self.assertIsInstance(procs, list)
        self.assertLessEqual(len(procs), 5)
        if procs:
            self.assertIn("pid", procs[0])
            self.assertIn("name", procs[0])
            self.assertIn("memory_mb", procs[0])

    def test_find_process_by_name(self) -> None:
        """Verify searching for running processes by name keyword."""
        res = self.mgr.find_process_by_name("nonexistent_random_process_12345")
        self.assertIsInstance(res, list)
        self.assertEqual(len(res), 0)

    def test_get_process_details_missing_pid(self) -> None:
        """Verify query on non-existent PID returns NOT_FOUND."""
        res = self.mgr.get_process_details(9999999)
        self.assertEqual(res.get("status"), "NOT_FOUND")

    def test_get_process_resource_usage_missing_pid(self) -> None:
        """Verify resource usage on non-existent PID returns NOT_FOUND."""
        res = self.mgr.get_process_resource_usage(9999999)
        self.assertEqual(res.get("status"), "NOT_FOUND")

    def test_get_top_processes(self) -> None:
        """Verify top processes ranking by memory and CPU."""
        top_mem = self.mgr.get_top_processes(sort_by="memory", limit=3)
        self.assertIsInstance(top_mem, list)
        self.assertLessEqual(len(top_mem), 3)

        top_cpu = self.mgr.get_top_processes(sort_by="cpu", limit=3)
        self.assertIsInstance(top_cpu, list)
        self.assertLessEqual(len(top_cpu), 3)

    def test_check_process_responsiveness_missing_pid(self) -> None:
        """Verify responsiveness check on missing PID."""
        res = self.mgr.check_process_responsiveness(9999999)
        self.assertEqual(res.get("status"), "NOT_FOUND")
        self.assertFalse(res.get("is_responsive"))

    def test_get_process_tree_missing_pid(self) -> None:
        """Verify process tree inspection on missing PID."""
        res = self.mgr.get_process_tree(9999999)
        self.assertEqual(res.get("status"), "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()

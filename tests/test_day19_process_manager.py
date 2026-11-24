"""
Day 19 Unit Tests — Advanced Windows Process Manager.
Verifies process enumeration, filtering, details, parent/child relationships,
resource summary statistics, safe startup, and graceful termination.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from zye_windows.process_manager import WindowsProcessManager


class TestDay19ProcessManager(unittest.TestCase):

    def setUp(self) -> None:
        self.pm = WindowsProcessManager()

    def test_list_processes_structure(self) -> None:
        """Verify list_processes returns bounded list of process records."""
        procs = self.pm.list_processes(limit=10)
        self.assertIsInstance(procs, list)
        self.assertTrue(len(procs) <= 10)
        if procs:
            p = procs[0]
            self.assertIn("pid", p)
            self.assertIn("name", p)
            self.assertIn("memory_mb", p)
            self.assertIn("is_protected", p)

    def test_find_process_by_name(self) -> None:
        """Verify find_process_by_name matches running executable."""
        # Current python process is running
        results = self.pm.find_process_by_name("python")
        self.assertIsInstance(results, list)
        self.assertTrue(any("python" in r.get("name", "").lower() for r in results))

    def test_get_process_details_current(self) -> None:
        """Verify get_process_details fetches telemetry for current process."""
        my_pid = os.getpid()
        details = self.pm.get_process_details(my_pid)
        self.assertEqual(details.get("status"), "SUCCESS")
        self.assertEqual(details.get("pid"), my_pid)
        self.assertTrue("python" in details.get("name", "").lower())
        self.assertTrue(details.get("memory_mb", 0) > 0)
        self.assertIn("create_time", details)

    def test_get_process_tree_current(self) -> None:
        """Verify get_process_tree inspects parent and children."""
        my_pid = os.getpid()
        tree = self.pm.get_process_tree(my_pid)
        self.assertEqual(tree.get("status"), "SUCCESS")
        self.assertEqual(tree.get("pid"), my_pid)
        self.assertIn("children", tree)

    def test_get_process_children(self) -> None:
        """Verify get_process_children returns list of child processes."""
        my_pid = os.getpid()
        children = self.pm.get_process_children(my_pid)
        self.assertIsInstance(children, list)

    def test_get_system_resource_summary(self) -> None:
        """Verify get_system_resource_summary computes CPU, RAM, and top processes on-demand."""
        summary = self.pm.get_system_resource_summary()
        self.assertEqual(summary.get("status"), "SUCCESS")
        self.assertIn("cpu_percent", summary)
        self.assertIn("ram_total_mb", summary)
        self.assertIn("ram_available_mb", summary)
        self.assertIn("ram_used_mb", summary)
        self.assertIn("top_memory_processes", summary)
        self.assertIn("top_cpu_processes", summary)
        self.assertTrue(summary.get("active_processes_count", 0) > 0)

    @patch("subprocess.Popen")
    def test_start_application_process_safe(self, mock_popen) -> None:
        """Verify start_application_process invokes subprocess without shell=True."""
        mock_proc = MagicMock()
        mock_proc.pid = 99999
        mock_popen.return_value = mock_proc

        res = self.pm.start_application_process("notepad.exe", args=["test.txt"])
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertEqual(res.get("pid"), 99999)
        mock_popen.assert_called_once_with(["notepad.exe", "test.txt"], shell=False)

    def test_start_application_process_rejects_metacharacters(self) -> None:
        """Verify start_application_process rejects commands containing shell metacharacters."""
        res_pipe = self.pm.start_application_process("notepad.exe | calc.exe")
        self.assertEqual(res_pipe.get("status"), "REJECTED")

        res_semi = self.pm.start_application_process("notepad.exe; rm -rf /")
        self.assertEqual(res_semi.get("status"), "REJECTED")

    def test_verify_process_status_current(self) -> None:
        """Verify verify_process_status correctly reports running state for current PID."""
        my_pid = os.getpid()
        res = self.pm.verify_process_status(my_pid)
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertTrue(res.get("is_running"))

    def test_verify_process_status_non_existent(self) -> None:
        """Verify verify_process_status returns NOT_FOUND for non-existent PID."""
        res = self.pm.verify_process_status(9999999)
        self.assertEqual(res.get("status"), "NOT_FOUND")
        self.assertFalse(res.get("is_running"))


if __name__ == "__main__":
    unittest.main()

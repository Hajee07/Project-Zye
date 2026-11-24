"""
Unit tests for Windows Process Management Security & Protection Gates (Day 17).
Verifies protected OS blacklist filtering, PID reuse detection, and mandatory
two-stage confirmation interlocks. NEVER terminates real host processes.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_windows.process_manager import WindowsProcessManager


class TestDay17ProcessSecurity(unittest.TestCase):

    def setUp(self) -> None:
        self.mgr = WindowsProcessManager()

    def test_protected_process_blacklist_contents(self) -> None:
        """Verify protected processes blacklist contains critical Windows services."""
        protected = self.mgr.PROTECTED_PROCESSES
        self.assertIn("csrss.exe", protected)
        self.assertIn("explorer.exe", protected)
        self.assertIn("services.exe", protected)
        self.assertIn("lsass.exe", protected)
        self.assertIn("wininit.exe", protected)
        self.assertIn("dwm.exe", protected)

    def test_is_protected_process_matching(self) -> None:
        """Verify is_protected_process catches exact and path-qualified names."""
        self.assertTrue(self.mgr.is_protected_process("csrss.exe"))
        self.assertTrue(self.mgr.is_protected_process("C:\\Windows\\System32\\csrss.exe"))
        self.assertTrue(self.mgr.is_protected_process("EXPLORER.EXE"))
        self.assertFalse(self.mgr.is_protected_process("notepad.exe"))
        self.assertFalse(self.mgr.is_protected_process("custom_script.exe"))

    @patch("psutil.Process")
    def test_termination_of_protected_process_blocked(self, mock_proc_cls: MagicMock) -> None:
        """Verify termination of protected process is immediately rejected."""
        mock_p = MagicMock()
        mock_p.name.return_value = "csrss.exe"
        mock_proc_cls.return_value = mock_p

        res = self.mgr.request_process_termination(pid=1000, confirmed=True)
        self.assertEqual(res.get("status"), "PROTECTED_PROCESS")
        self.assertFalse(res.get("allowed"))
        mock_p.kill.assert_not_called()

        # Test terminate_process also blocks it
        term_res = self.mgr.terminate_process(pid=1000, confirmed=True)
        self.assertEqual(term_res.get("status"), "PROTECTED_PROCESS")
        mock_p.kill.assert_not_called()

    @patch("psutil.Process")
    def test_unconfirmed_termination_requires_confirmation(self, mock_proc_cls: MagicMock) -> None:
        """Verify unconfirmed termination requires explicit user confirmation."""
        mock_p = MagicMock()
        mock_p.name.return_value = "notepad.exe"
        mock_proc_cls.return_value = mock_p

        res = self.mgr.request_process_termination(pid=2000, confirmed=False)
        self.assertEqual(res.get("status"), "CONFIRMATION_REQUIRED")
        self.assertTrue(res.get("requires_confirmation"))
        mock_p.kill.assert_not_called()

        term_res = self.mgr.terminate_process(pid=2000, confirmed=False)
        self.assertEqual(term_res.get("status"), "CONFIRMATION_REQUIRED")
        mock_p.kill.assert_not_called()

    @patch("psutil.Process")
    def test_pid_reuse_detection(self, mock_proc_cls: MagicMock) -> None:
        """Verify PID reuse detection triggers when actual process name differs from expected."""
        mock_p = MagicMock()
        mock_p.name.return_value = "calculator.exe"
        mock_proc_cls.return_value = mock_p

        res = self.mgr.request_process_termination(pid=3000, confirmed=True, expected_name="notepad.exe")
        self.assertEqual(res.get("status"), "PID_REUSE_DETECTED")
        self.assertFalse(res.get("allowed"))
        mock_p.kill.assert_not_called()

    @patch("psutil.Process")
    def test_confirmed_non_protected_termination_success(self, mock_proc_cls: MagicMock) -> None:
        """Verify confirmed termination of non-protected process succeeds."""
        mock_p = MagicMock()
        mock_p.name.return_value = "test_worker.exe"
        mock_proc_cls.return_value = mock_p

        term_res = self.mgr.terminate_process(pid=4000, confirmed=True, expected_name="test_worker.exe")
        self.assertEqual(term_res.get("status"), "SUCCESS")
        self.assertTrue(term_res.get("terminated"))
        mock_p.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()

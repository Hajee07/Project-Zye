"""
Day 19 Unit Tests — Windows Process Security & Protected Gates.
Verifies protected process blacklist enforcement, PID reuse mitigation,
stale PID rejection, confirmation barriers, and arbitrary command shielding.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_windows.process_manager import WindowsProcessManager


class TestDay19ProcessSecurity(unittest.TestCase):

    def setUp(self) -> None:
        self.pm = WindowsProcessManager()

    def test_protected_process_blacklist(self) -> None:
        """Verify protected processes are properly flagged by is_protected_process."""
        protected_list = ["csrss.exe", "smss.exe", "services.exe", "lsass.exe", "explorer.exe", "dwm.exe"]
        for p in protected_list:
            self.assertTrue(self.pm.is_protected_process(p), f"Expected {p} to be protected")

        unprotected_list = ["notepad.exe", "chrome.exe", "vlc.exe", "spotify.exe"]
        for u in unprotected_list:
            self.assertFalse(self.pm.is_protected_process(u), f"Expected {u} to be unprotected")

    @patch("psutil.Process")
    def test_protected_process_termination_blocked(self, mock_proc_cls) -> None:
        """Verify termination of protected process is strictly rejected."""
        mock_proc = MagicMock()
        mock_proc.name.return_value = "csrss.exe"
        mock_proc_cls.return_value = mock_proc

        req = self.pm.request_process_termination(pid=100)
        self.assertEqual(req.get("status"), "PROTECTED_PROCESS")
        self.assertFalse(req.get("allowed"))

        # Even with confirmed=True and force=True, must be rejected
        res = self.pm.terminate_process(pid=100, force=True, confirmed=True)
        self.assertEqual(res.get("status"), "PROTECTED_PROCESS")
        mock_proc.kill.assert_not_called()
        mock_proc.terminate.assert_not_called()

    @patch("psutil.Process")
    def test_pid_reuse_detection(self, mock_proc_cls) -> None:
        """Verify PID reuse is detected when expected_name does not match actual process."""
        mock_proc = MagicMock()
        mock_proc.name.return_value = "malicious_tool.exe"
        mock_proc_cls.return_value = mock_proc

        req = self.pm.request_process_termination(pid=1234, expected_name="notepad.exe")
        self.assertEqual(req.get("status"), "PID_REUSE_DETECTED")
        self.assertFalse(req.get("allowed"))

    def test_stale_pid_termination_handled(self) -> None:
        """Verify termination of already exited PID returns graceful NOT_FOUND or SUCCESS."""
        # Non-existent PID
        res = self.pm.terminate_process(pid=9999999, confirmed=True)
        self.assertIn(res.get("status"), ("NOT_FOUND", "SUCCESS"))

    @patch("psutil.Process")
    def test_force_termination_requires_explicit_confirmation(self, mock_proc_cls) -> None:
        """Verify force=True requires explicit confirmed=True."""
        mock_proc = MagicMock()
        mock_proc.name.return_value = "test_worker.exe"
        mock_proc_cls.return_value = mock_proc

        # Call with force=True but confirmed=False
        res = self.pm.terminate_process(pid=5555, force=True, confirmed=False)
        self.assertEqual(res.get("status"), "CONFIRMATION_REQUIRED")
        self.assertTrue(res.get("requires_confirmation"))
        mock_proc.kill.assert_not_called()

    def test_arbitrary_shell_command_injection_rejected(self) -> None:
        """Verify commands with subshell, piping, or chaining are rejected at launch."""
        bad_commands = [
            "notepad.exe & calc.exe",
            "cmd.exe /c whoami",
            "powershell.exe -Command (Get-Process)",
            "app.exe `evil`",
            "app.exe $(calc)",
        ]
        for cmd in bad_commands:
            res = self.pm.start_application_process(cmd)
            self.assertEqual(res.get("status"), "REJECTED", f"Expected command '{cmd}' to be rejected")


if __name__ == "__main__":
    unittest.main()

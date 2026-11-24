"""
Day 18 Unit Tests — Safe Recycle Bin Management Engine.
Verifies two-stage Recycle Bin inspection, preview metadata,
mandatory confirmation barrier (confirmed=False blocks execution), and mock execution.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_windows.recycle_bin_manager import WindowsRecycleBinManager


class TestDay18RecycleBin(unittest.TestCase):

    def setUp(self) -> None:
        self.rbm = WindowsRecycleBinManager()

    def test_preview_recycle_bin(self) -> None:
        """Verify previewing Recycle Bin returns non-destructive item metadata."""
        preview = self.rbm.preview_recycle_bin()
        self.assertIn(preview["status"], ("SUCCESS", "WARN"))
        self.assertIn("item_count", preview)
        self.assertIn("total_size_mb", preview)

    def test_unconfirmed_empty_recycle_bin_blocked(self) -> None:
        """Verify calling empty_recycle_bin with confirmed=False blocks execution with CONFIRMATION_REQUIRED."""
        res = self.rbm.empty_recycle_bin(confirmed=False)
        self.assertEqual(res["status"], "CONFIRMATION_REQUIRED")
        self.assertEqual(res["risk_level"], "CRITICAL_RISK")
        self.assertIn("confirmed=True", res["message"])
        self.assertIn("tanglish_message", res)
        self.assertFalse(res["verified"])

    @patch("ctypes.windll.shell32.SHEmptyRecycleBinW")
    def test_confirmed_empty_recycle_bin(self, mock_empty: MagicMock) -> None:
        """Verify calling empty_recycle_bin with confirmed=True dispatches Win32 cleanup."""
        mock_empty.return_value = 0
        res = self.rbm.empty_recycle_bin(confirmed=True)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["verified"])
        mock_empty.assert_called_once()


if __name__ == "__main__":
    unittest.main()

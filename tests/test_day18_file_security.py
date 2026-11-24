"""
Day 18 Unit Tests — File Search Security & Executable Shielding.
Verifies path traversal rejection ('..', '/', '\\'), and blocks automatic execution
of dangerous binaries (.exe, .bat, .cmd, .ps1, .vbs, .msi).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zye_windows.file_search import WindowsFileSearch


class TestDay18FileSecurity(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

        (self.base_path / "Downloads").mkdir()
        # Create executable scripts
        (self.base_path / "Downloads" / "setup.exe").write_text("binary", encoding="utf-8")
        (self.base_path / "Downloads" / "script.bat").write_text("@echo off", encoding="utf-8")

        self.fs = WindowsFileSearch()
        self.fs.home = self.base_path

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_path_traversal_rejection(self) -> None:
        """Verify queries with traversal tokens '..' or slashes are rejected immediately."""
        res_dots = self.fs.find_and_open_local_file("../../windows/system32/cmd")
        self.assertEqual(res_dots["status"], "REJECTED")

        res_slash = self.fs.find_and_open_local_file("subfolder/file.txt")
        self.assertEqual(res_slash["status"], "REJECTED")

        res_backslash = self.fs.find_and_open_local_file("subfolder\\file.txt")
        self.assertEqual(res_backslash["status"], "REJECTED")

    def test_executable_file_launch_blocked(self) -> None:
        """Verify opening an executable file (.exe, .bat) is blocked with EXECUTABLE_BLOCKED."""
        res_exe = self.fs.find_and_open_local_file("setup.exe", open_file=True)
        self.assertEqual(res_exe["status"], "EXECUTABLE_BLOCKED")
        self.assertTrue(res_exe["is_executable"])
        self.assertIn("Explicit authorization is required", res_exe["message"])

        res_bat = self.fs.find_and_open_local_file("script.bat", open_file=True)
        self.assertEqual(res_bat["status"], "EXECUTABLE_BLOCKED")
        self.assertTrue(res_bat["is_executable"])


if __name__ == "__main__":
    unittest.main()

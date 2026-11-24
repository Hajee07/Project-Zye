"""
Unit tests for Day 13 Real-Time System Preflight Engine.
Tests zye_intelligence.preflight: ZyeSystemPreflight, _preflight_system_check,
non-invasive lock inspection, and hardware telemetry handling.
"""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from zye_intelligence.preflight import (
    ZyeSystemPreflight,
    _is_windows_file_locked,
    _preflight_system_check,
)


class TestDay13Preflight(unittest.TestCase):
    def setUp(self) -> None:
        self.preflight = ZyeSystemPreflight()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = pathlib.Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_01_ram_telemetry(self) -> None:
        """Test RAM telemetry collection."""
        mem = self.preflight.inspect_memory()
        self.assertIn("percent", mem)
        self.assertIn("available_gb", mem)
        self.assertIsInstance(mem["percent"], float)
        self.assertGreaterEqual(mem["percent"], 0.0)

    def test_02_disk_telemetry(self) -> None:
        """Test disk usage telemetry collection."""
        disk = self.preflight.inspect_storage()
        self.assertIn("percent", disk)
        self.assertIn("free_gb", disk)
        self.assertIsInstance(disk["percent"], float)

    def test_03_cpu_telemetry(self) -> None:
        """Test CPU load percentage inspection."""
        cpu = self.preflight.inspect_cpu(interval=0.01)
        self.assertIn("percent", cpu)
        self.assertIsInstance(cpu["percent"], float)

    def test_04_battery_available(self) -> None:
        """Test battery telemetry when sensor is available."""
        mock_batt = type("Battery", (), {"percent": 75.0, "power_plugged": True, "secsleft": 3600})()
        with patch("psutil.sensors_battery", return_value=mock_batt):
            batt = self.preflight.inspect_battery()
            self.assertTrue(batt["available"])
            self.assertEqual(batt["percent"], 75.0)
            self.assertTrue(batt["power_plugged"])
            self.assertFalse(batt["battery_powered"])

    def test_05_battery_unavailable(self) -> None:
        """Test battery telemetry when sensor is unavailable (desktop/VM)."""
        with patch("psutil.sensors_battery", return_value=None):
            batt = self.preflight.inspect_battery()
            self.assertFalse(batt["available"])
            self.assertIsNone(batt["percent"])
            self.assertIsNone(batt["power_plugged"])

    def test_06_existing_target(self) -> None:
        """Test diagnostics on an existing target file."""
        sample_file = self.temp_path / "sample.txt"
        sample_file.write_text("Hello Zye AI", encoding="utf-8")

        res = self.preflight.inspect_target_paths([str(sample_file)])
        self.assertEqual(len(res), 1)
        diag = res[0]
        self.assertTrue(diag["exists"])
        self.assertEqual(diag["target_type"], "file")
        self.assertTrue(diag["readable"])
        self.assertTrue(diag["writable"])
        self.assertGreater(diag["size_bytes"], 0)

    def test_07_missing_target(self) -> None:
        """Test diagnostics on a non-existent target file."""
        missing = self.temp_path / "nonexistent.dat"
        res = self.preflight.inspect_target_paths([str(missing)])
        self.assertEqual(len(res), 1)
        diag = res[0]
        self.assertFalse(diag["exists"])
        self.assertEqual(diag["target_type"], "missing")
        self.assertEqual(diag["diagnostic_status"], "MISSING")

    def test_08_file_permission_denied(self) -> None:
        """Test handling of permission denied errors during target inspection."""
        with patch("os.access", return_value=False):
            sample_file = self.temp_path / "protected.txt"
            sample_file.write_text("protected content", encoding="utf-8")
            res = self.preflight.inspect_target_paths([str(sample_file)])
            diag = res[0]
            self.assertFalse(diag["readable"])

    def test_09_file_lock_unknown(self) -> None:
        """Test that file lock status returns UNKNOWN on accessible files non-invasively."""
        sample = self.temp_path / "test_lock.txt"
        sample.write_text("lock test", encoding="utf-8")
        status = _is_windows_file_locked(sample)
        self.assertIn(status, ("UNKNOWN", "LOCKED"))

    def test_10_non_invasive_diagnostics(self) -> None:
        """Verify that preflight inspection never modifies existing file or creates new file."""
        target = self.temp_path / "untouched.txt"
        target.write_text("Initial content", encoding="utf-8")
        mtime_before = target.stat().st_mtime
        size_before = target.stat().st_size

        self.preflight.generate_preflight_report([str(target)])

        mtime_after = target.stat().st_mtime
        size_after = target.stat().st_size
        self.assertEqual(mtime_before, mtime_after)
        self.assertEqual(size_before, size_after)

    def test_11_invalid_target(self) -> None:
        """Test preflight with empty or malformed target strings."""
        res = self.preflight.inspect_target_paths([""])
        self.assertEqual(len(res), 1)
        self.assertFalse(res[0]["exists"])

    def test_12_large_file_metadata(self) -> None:
        """Test file size calculation in MB for larger target files."""
        large = self.temp_path / "large.bin"
        with open(large, "wb") as f:
            f.seek(1024 * 1024 * 2)  # 2 MB sparse file
            f.write(b"\0")
        res = self.preflight.inspect_target_paths([str(large)])
        diag = res[0]
        self.assertGreaterEqual(diag["file_size_mb"], 2.0)

    def test_13_telemetry_exception_handling(self) -> None:
        """Test preflight resilience when psutil calls throw unexpected exceptions."""
        with patch("psutil.virtual_memory", side_effect=RuntimeError("WMI error")):
            mem = self.preflight.inspect_memory()
            self.assertFalse(mem["available"])
            self.assertIn("error", mem)

        report = _preflight_system_check([])
        self.assertIn("system_status", report)


if __name__ == "__main__":
    unittest.main()

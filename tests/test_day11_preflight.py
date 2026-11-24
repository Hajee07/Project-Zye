"""Unit tests for Zye Day 11 Live System Preflight Engine."""

import os
import pathlib
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from zye_autonomy.preflight import ZyeSystemPreflight


class TestZyeSystemPreflight(unittest.TestCase):
    def setUp(self):
        self.preflight = ZyeSystemPreflight()

    def test_01_ram_collection(self):
        res = self.preflight.inspect_memory()
        self.assertTrue(res.get("available"))
        self.assertIn("total_gb", res)
        self.assertIn("percent", res)
        self.assertGreater(res["total_gb"], 0.0)

    def test_02_disk_collection(self):
        res = self.preflight.inspect_storage()
        self.assertTrue(res.get("available"))
        self.assertIn("free_gb", res)
        self.assertIn("percent", res)
        self.assertGreater(res["total_gb"], 0.0)

    def test_03_cpu_collection(self):
        res = self.preflight.inspect_cpu(interval=0.05)
        self.assertTrue(res.get("available"))
        self.assertIn("percent", res)
        self.assertGreaterEqual(res["logical_cores"], 1)

    def test_04_battery_unavailable(self):
        with patch("psutil.sensors_battery", return_value=None):
            res = self.preflight.inspect_battery()
            self.assertFalse(res["available"])
            self.assertIsNone(res["percent"])
            self.assertIn("No battery sensor", res.get("note", ""))

    def test_05_missing_target_path(self):
        results = self.preflight.inspect_target_paths(["nonexistent_dir/dummy_file.txt"])
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["exists"])
        self.assertEqual(results[0]["lock_status"], "UNKNOWN")

    def test_06_existing_target_path(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"Hello Zye Test")
            tmp_path = tmp.name

        try:
            results = self.preflight.inspect_target_paths([tmp_path])
            self.assertEqual(len(results), 1)
            self.assertTrue(results[0]["exists"])
            self.assertTrue(results[0]["is_file"])
            self.assertFalse(results[0]["is_dir"])
            self.assertEqual(results[0]["size_bytes"], len(b"Hello Zye Test"))
            self.assertEqual(results[0]["lock_status"], "UNKNOWN")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_07_directory_target(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            results = self.preflight.inspect_target_paths([tmpdir])
            self.assertEqual(len(results), 1)
            self.assertTrue(results[0]["exists"])
            self.assertTrue(results[0]["is_dir"])
            self.assertFalse(results[0]["is_file"])

    def test_08_file_metadata(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"Data 12345")
            tmp_path = tmp.name

        try:
            results = self.preflight.inspect_target_paths([tmp_path])
            self.assertIn("modified_at", results[0])
            self.assertTrue(results[0]["readable"])
            self.assertTrue(results[0]["writable"])
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_09_access_denied_handling(self):
        with patch("pathlib.Path.resolve", side_effect=PermissionError("Access denied")):
            results = self.preflight.inspect_target_paths(["restricted/path"])
            self.assertEqual(len(results), 1)
            self.assertIn("Permission denied", results[0].get("error", ""))
            self.assertEqual(results[0]["lock_status"], "UNKNOWN")

    def test_10_unknown_file_lock_state(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            results = self.preflight.inspect_target_paths([tmp_path])
            self.assertEqual(results[0]["lock_status"], "UNKNOWN")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_11_missing_drive(self):
        # Inspect an imaginary invalid drive on Windows
        res = self.preflight.inspect_storage("Z:\\NonExistentDriveXYZ")
        # Preflight falls back or returns drive error cleanly without crash
        self.assertIn("available", res)

    def test_12_malformed_target_input(self):
        results = self.preflight.inspect_target_paths(["\0bad_null_byte_path"])
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["exists"])
        self.assertEqual(results[0]["lock_status"], "UNKNOWN")

    def test_13_generate_preflight_report_structure(self):
        rep = self.preflight.generate_preflight_report(["main.py"])
        self.assertIn("system_status", rep)
        self.assertIn("free_ram_gb", rep)
        self.assertIn("ram_used_pct", rep)
        self.assertIn("free_disk_gb", rep)
        self.assertIn("disk_used_pct", rep)
        self.assertIn("cpu_load_pct", rep)
        self.assertIn("battery_percent", rep)
        self.assertIn("target_diagnostics", rep)
        self.assertIn("warnings", rep)
        self.assertIn("unknowns", rep)
        self.assertIn("timestamp", rep)


if __name__ == "__main__":
    unittest.main()

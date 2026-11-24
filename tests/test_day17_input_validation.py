"""
Unit tests for Input Validation Engine (Day 17).
Validates Pydantic schemas and functional validators across process IDs, application names,
file paths, volume percentages, brightness levels, search queries, and scroll amounts.
"""

from __future__ import annotations

from pathlib import Path
import unittest

from zye_reliability.input_validator import (
    validate_app_name,
    validate_brightness,
    validate_path,
    validate_pid,
    validate_scroll_amount,
    validate_search_query,
    validate_volume,
)


class TestDay17InputValidation(unittest.TestCase):

    def test_validate_pid_valid(self) -> None:
        """Verify valid PID integers pass."""
        for val in [1, 100, 1234, 65535, "5000"]:
            ok, pid = validate_pid(val)
            self.assertTrue(ok)
            self.assertEqual(pid, int(val))

    def test_validate_pid_invalid(self) -> None:
        """Verify invalid PID boundaries and types fail."""
        for val in [0, -1, -500, 65536, 100000, "not_a_number", None]:
            ok, err = validate_pid(val)
            self.assertFalse(ok)
            self.assertIn("Invalid PID", err)

    def test_validate_app_name_valid(self) -> None:
        """Verify valid application names pass and are stripped."""
        ok, name = validate_app_name("  notepad.exe  ")
        self.assertTrue(ok)
        self.assertEqual(name, "notepad.exe")

    def test_validate_app_name_invalid(self) -> None:
        """Verify empty, whitespace-only, and control character app names fail."""
        for val in ["", "   ", "app\x00name", "app\nname", 12345, None]:
            ok, err = validate_app_name(val)
            self.assertFalse(ok)

    def test_validate_path_security(self) -> None:
        """Verify path traversal outside project root and UNC paths are rejected."""
        root = Path(__file__).resolve().parent.parent

        # Safe relative path inside project
        ok, res_path = validate_path("zye_config.toml", project_root=root)
        self.assertTrue(ok)

        # Null bytes blocked
        ok_null, _ = validate_path("bad\x00file.txt", project_root=root)
        self.assertFalse(ok_null)

        # UNC paths blocked
        ok_unc, _ = validate_path("\\\\server\\share\\file.txt", project_root=root)
        self.assertFalse(ok_unc)

        # Path traversal escaping root blocked
        ok_trav, _ = validate_path("../../../../../../../../../Windows/System32/cmd.exe", project_root=root)
        self.assertFalse(ok_trav)

    def test_validate_volume(self) -> None:
        """Verify volume boundary validation (0..100)."""
        ok_min, val_min = validate_volume(0)
        self.assertTrue(ok_min)
        self.assertEqual(val_min, 0)

        ok_max, val_max = validate_volume(100)
        self.assertTrue(ok_max)
        self.assertEqual(val_max, 100)

        ok_mid, val_mid = validate_volume("50")
        self.assertTrue(ok_mid)
        self.assertEqual(val_mid, 50)

        self.assertFalse(validate_volume(-1)[0])
        self.assertFalse(validate_volume(101)[0])
        self.assertFalse(validate_volume("invalid")[0])

    def test_validate_brightness(self) -> None:
        """Verify brightness boundary validation (0..100)."""
        self.assertTrue(validate_brightness(0)[0])
        self.assertTrue(validate_brightness(100)[0])
        self.assertFalse(validate_brightness(-5)[0])
        self.assertFalse(validate_brightness(105)[0])

    def test_validate_search_query(self) -> None:
        """Verify search query validation."""
        ok, q = validate_search_query("  find report  ")
        self.assertTrue(ok)
        self.assertEqual(q, "find report")

        self.assertFalse(validate_search_query("   ")[0])
        self.assertFalse(validate_search_query("test\x00query")[0])
        self.assertFalse(validate_search_query(123)[0])

    def test_validate_scroll_amount(self) -> None:
        """Verify scroll amount boundary validation (1..50)."""
        self.assertTrue(validate_scroll_amount(1)[0])
        self.assertTrue(validate_scroll_amount(50)[0])
        self.assertFalse(validate_scroll_amount(0)[0])
        self.assertFalse(validate_scroll_amount(51)[0])
        self.assertFalse(validate_scroll_amount(-1)[0])


if __name__ == "__main__":
    unittest.main()

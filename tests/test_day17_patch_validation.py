"""
Unit tests for Patch Validation & Diff Preview Engine (Day 17).
Verifies single-occurrence snippet replacement, diff generation, AST syntax gates,
protected framework file immutability, and affected function identification.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zye_repair.backup_manager import ZyeBackupManager
from zye_repair.patch_manager import CRITICAL_PROTECTED_FILES, ZyePatchManager


class TestDay17PatchValidation(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "zye_config.toml").write_text("# config\n", encoding="utf-8")
        self.backup_mgr = ZyeBackupManager(project_root=self.root)
        self.patch_mgr = ZyePatchManager(project_root=self.root, backup_manager=self.backup_mgr)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_protected_files_cannot_be_patched(self) -> None:
        """Verify critical framework files are rejected from patching."""
        for name in ["zye_guard.py", "doctor.py", "self_repair_mcp.py", ".env"]:
            p = self.root / name
            p.write_text("x = 1\n", encoding="utf-8")
            res = self.patch_mgr.preview_patch(filename=name, old_snippet="x = 1", new_snippet="x = 2")
            self.assertEqual(res.get("status"), "ERROR")
            self.assertEqual(res.get("code"), "PROTECTED_FILE")

    def test_preview_patch_success(self) -> None:
        """Verify successful diff preview with AST and compile verification."""
        target = self.root / "sample_module.py"
        target.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")

        res = self.patch_mgr.preview_patch(
            filename="sample_module.py",
            old_snippet="return a - b",
            new_snippet="return a + b",
            reason="Fix subtraction bug in add()",
        )
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertEqual(res.get("ast_validation"), "PASS")
        self.assertEqual(res.get("compile_validation"), "PASS")
        self.assertIn("-    return a - b", res.get("diff", ""))
        self.assertIn("+    return a + b", res.get("diff", ""))

    def test_preview_patch_ambiguous_replacement(self) -> None:
        """Verify snippet occurring multiple times is rejected as ambiguous."""
        target = self.root / "repeat_module.py"
        target.write_text("val = 10\nprint(val)\nval = 10\n", encoding="utf-8")

        res = self.patch_mgr.preview_patch(
            filename="repeat_module.py",
            old_snippet="val = 10",
            new_snippet="val = 20",
        )
        self.assertEqual(res.get("status"), "ERROR")
        self.assertEqual(res.get("code"), "AMBIGUOUS_REPLACEMENT")

    def test_preview_patch_syntax_error_rejected(self) -> None:
        """Verify proposing invalid Python syntax fails AST validation."""
        target = self.root / "syntax_module.py"
        target.write_text("x = 1\n", encoding="utf-8")

        res = self.patch_mgr.preview_patch(
            filename="syntax_module.py",
            old_snippet="x = 1",
            new_snippet="def broken(\n",
        )
        self.assertEqual(res.get("status"), "ERROR")
        self.assertEqual(res.get("code"), "AST_VALIDATION_FAILED")

    def test_get_affected_functions(self) -> None:
        """Verify identifying function containing the targeted snippet."""
        code = (
            "def calculate_total(price, tax):\n"
            "    subtotal = price\n"
            "    return subtotal + tax\n"
            "\n"
            "def unrelated():\n"
            "    return True\n"
        )
        affected = self.patch_mgr.get_affected_functions(code, "subtotal = price")
        self.assertIn("calculate_total", affected)
        self.assertNotIn("unrelated", affected)


if __name__ == "__main__":
    unittest.main()

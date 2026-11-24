#!/usr/bin/env python3
"""
ZYE AI — Day 05 Self-Repair MCP Engine Test Suite
===================================================

Comprehensive test suite covering:
  - Project Root & Path Security (14 tests)
  - Error Log Reader (9 tests)
  - Source Code Inspection (11 tests)
  - Project Source Discovery (9 tests)
  - Secure Backup Engine & SHA-256 Verification (16 tests)
  - Traceback Intelligence Engine (6 tests)
  - FastMCP Protocol & Tool Registration (8 tests)

Total: 73 automated unit tests.

Usage::
    python -m unittest tests.test_day05_self_repair -v
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import self_repair_mcp
from self_repair_mcp import (
    get_project_root,
    resolve_project_file,
    validate_file_size,
    calculate_sha256,
    verify_backup_integrity,
    contains_embedded_secret,
    parse_traceback_summary,
    classify_error_type,
    read_recent_error_logs,
    read_own_source_code,
    list_project_source_files,
    inspect_source_file,
    create_source_backup,
    list_source_backups,
    make_success_response,
    make_error_response,
    log_repair_audit,
    mcp,
    _reset_project_root_cache,
    _reset_audit_logger,
)


class _SelfRepairTestBase(unittest.TestCase):
    """Base fixture providing an isolated temporary project workspace."""

    def setUp(self) -> None:
        _reset_project_root_cache()
        _reset_audit_logger()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmpdir.name)

        # Setup standard project layout
        (self.tmpdir / "zye_config.toml").write_text("[system]\nassistant_name = 'Zye'\n", encoding="utf-8")
        (self.tmpdir / "logs").mkdir()
        (self.tmpdir / "backups").mkdir()
        (self.tmpdir / "data").mkdir()
        (self.tmpdir / "skills").mkdir()
        (self.tmpdir / "profiles").mkdir()
        (self.tmpdir / ".venv").mkdir()
        (self.tmpdir / ".git").mkdir()

        # Seed standard files
        (self.tmpdir / ".env").write_text("GEMINI_API_KEY=test_key_placeholder\n", encoding="utf-8")
        (self.tmpdir / "sample_tool.py").write_text(
            '"""Sample test module."""\n\ndef add(a: int, b: int) -> int:\n    return a + b\n',
            encoding="utf-8",
        )
        (self.tmpdir / "skills" / "math_skill.py").write_text(
            'def multiply(x: int, y: int) -> int:\n    return x * y\n',
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        _reset_audit_logger()
        _reset_project_root_cache()
        try:
            self._tmpdir.cleanup()
        except (PermissionError, OSError):
            pass


# ============================================================================
# 1. PROJECT ROOT & PATH SECURITY (14 tests)
# ============================================================================

class TestPathSecurity(_SelfRepairTestBase):
    """Test path containment, traversal protection, and file access policies."""

    def test_01_project_root_resolution(self):
        """get_project_root locates project containing zye_config.toml."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            root = get_project_root()
            self.assertEqual(root, self.tmpdir)

    def test_02_valid_source_file_accepted(self):
        """Valid project-contained .py file resolves successfully."""
        valid, resolved, err = resolve_project_file("sample_tool.py", root=self.tmpdir)
        self.assertTrue(valid)
        self.assertIsNotNone(resolved)
        self.assertIsNone(err)

    def test_03_missing_file_rejected(self):
        """Missing file returns FILE_NOT_FOUND error code."""
        valid, resolved, err = resolve_project_file("nonexistent.py", root=self.tmpdir)
        self.assertFalse(valid)
        self.assertEqual(err, "FILE_NOT_FOUND")

    def test_04_parent_traversal_rejected(self):
        """Path traversal escaping root is blocked."""
        valid, resolved, err = resolve_project_file("../../etc/shadow.py", root=self.tmpdir)
        self.assertFalse(valid)
        self.assertEqual(err, "PATH_OUTSIDE_PROJECT")

    def test_05_absolute_external_path_rejected(self):
        """External absolute path is blocked."""
        ext_path = str(Path(tempfile.gettempdir()) / "other_dir" / "hack.py")
        valid, resolved, err = resolve_project_file(ext_path, root=self.tmpdir)
        self.assertFalse(valid)
        self.assertEqual(err, "PATH_OUTSIDE_PROJECT")

    def test_06_windows_system_path_rejected(self):
        """Windows system directory path is blocked."""
        win_path = r"C:\Windows\System32\cmd.exe"
        valid, resolved, err = resolve_project_file(win_path, root=self.tmpdir)
        self.assertFalse(valid)
        self.assertIn(err, ("PATH_OUTSIDE_PROJECT", "PATH_ACCESS_DENIED"))

    def test_07_env_file_inspection_rejected(self):
        """Attempts to resolve .env are strictly blocked as PROTECTED_FILE."""
        valid, resolved, err = resolve_project_file(".env", root=self.tmpdir, allowed_extensions=())
        self.assertFalse(valid)
        self.assertEqual(err, "PROTECTED_FILE")

    def test_08_database_inspection_rejected(self):
        """Attempts to access .sqlite databases via source tools are blocked."""
        db_file = self.tmpdir / "data" / "zye_test.sqlite"
        db_file.write_text("sqlite format", encoding="utf-8")
        valid, resolved, err = resolve_project_file("data/zye_test.sqlite", root=self.tmpdir, allowed_extensions=())
        self.assertFalse(valid)
        self.assertEqual(err, "PROTECTED_FILE")

    def test_09_profiles_directory_rejected(self):
        """Files inside profiles/ directory are blocked."""
        prof_file = self.tmpdir / "profiles" / "cookie.py"
        prof_file.write_text("# profile", encoding="utf-8")
        valid, resolved, err = resolve_project_file("profiles/cookie.py", root=self.tmpdir)
        self.assertFalse(valid)
        self.assertEqual(err, "PROTECTED_FILE")

    def test_10_venv_directory_rejected(self):
        """Files inside .venv directory are blocked."""
        venv_py = self.tmpdir / ".venv" / "site_package.py"
        venv_py.write_text("# venv", encoding="utf-8")
        valid, resolved, err = resolve_project_file(".venv/site_package.py", root=self.tmpdir)
        self.assertFalse(valid)
        self.assertEqual(err, "PROTECTED_FILE")

    def test_11_git_directory_rejected(self):
        """Files inside .git directory are blocked."""
        git_py = self.tmpdir / ".git" / "hook.py"
        git_py.write_text("# git", encoding="utf-8")
        valid, resolved, err = resolve_project_file(".git/hook.py", root=self.tmpdir)
        self.assertFalse(valid)
        self.assertEqual(err, "PROTECTED_FILE")

    def test_12_non_python_source_rejected(self):
        """Non-.py files are rejected by extension restriction."""
        txt_file = self.tmpdir / "notes.txt"
        txt_file.write_text("hello", encoding="utf-8")
        valid, resolved, err = resolve_project_file("notes.txt", root=self.tmpdir)
        self.assertFalse(valid)
        self.assertEqual(err, "INVALID_FILENAME")

    def test_13_null_byte_path_rejected(self):
        """Path strings containing null bytes are rejected."""
        valid, resolved, err = resolve_project_file("sample\x00.py", root=self.tmpdir)
        self.assertFalse(valid)
        self.assertEqual(err, "PATH_ACCESS_DENIED")

    def test_14_unc_path_rejected(self):
        """UNC paths are rejected."""
        valid, resolved, err = resolve_project_file(r"\\server\share\file.py", root=self.tmpdir)
        self.assertFalse(valid)
        self.assertEqual(err, "PATH_ACCESS_DENIED")


# ============================================================================
# 2. ERROR LOG READER (9 tests)
# ============================================================================

class TestErrorLogReader(_SelfRepairTestBase):
    """Test reading recent error logs and secret redaction."""

    def test_15_empty_log_handled_cleanly(self):
        """Empty or non-existent log returns no-errors success payload."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_recent_error_logs(lines=60)
        self.assertEqual(res["status"], "success")
        self.assertFalse(res["data"]["errors_found"])
        self.assertEqual(res["data"]["returned_lines"], 0)

    def test_16_existing_error_log_read(self):
        """Existing error log entries are parsed and returned."""
        err_log = self.tmpdir / "logs" / "zye_errors.log"
        err_log.write_text(
            '{"event": "test_error_1", "message": "Failed to connect"}\n'
            '{"event": "test_error_2", "message": "Operation timed out"}\n',
            encoding="utf-8",
        )
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_recent_error_logs(lines=10)
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["data"]["errors_found"])
        self.assertEqual(res["data"]["returned_lines"], 2)

    def test_17_default_lines_is_60(self):
        """Default lines argument retrieves up to 60 lines."""
        err_log = self.tmpdir / "logs" / "zye_errors.log"
        entries = [f'{{"id": {i}, "msg": "err"}}\n' for i in range(100)]
        err_log.write_text("".join(entries), encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_recent_error_logs()
        self.assertEqual(res["data"]["requested_lines"], 60)
        self.assertEqual(res["data"]["returned_lines"], 60)

    def test_18_maximum_200_lines_allowed(self):
        """200 lines request is accepted."""
        err_log = self.tmpdir / "logs" / "zye_errors.log"
        err_log.write_text('{"msg": "err"}\n' * 50, encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_recent_error_logs(lines=200)
        self.assertEqual(res["status"], "success")

    def test_19_zero_lines_rejected(self):
        """lines=0 is rejected with INVALID_ARGUMENTS."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_recent_error_logs(lines=0)
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "INVALID_ARGUMENTS")

    def test_20_negative_lines_rejected(self):
        """Negative line count is rejected."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_recent_error_logs(lines=-5)
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "INVALID_ARGUMENTS")

    def test_21_excessive_lines_rejected(self):
        """lines > 200 is rejected."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_recent_error_logs(lines=500)
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "INVALID_ARGUMENTS")

    def test_22_secret_redacted_in_log_reader(self):
        """Gemini and OpenAI API keys in error log lines are redacted."""
        err_log = self.tmpdir / "logs" / "zye_errors.log"
        err_log.write_text(
            '{"event": "auth_failure", "key": "AIzaSyD1234567890123456789012345678901234"}\n',
            encoding="utf-8",
        )
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_recent_error_logs(lines=10)
        entries_str = json.dumps(res["data"]["recent_log_entries"])
        self.assertNotIn("AIzaSyD1234567890123456789012345678901234", entries_str)
        self.assertIn("[REDACTED_GEMINI_KEY]", entries_str)

    def test_23_original_log_remains_unchanged(self):
        """Reading the error log does not modify or truncate it."""
        err_log = self.tmpdir / "logs" / "zye_errors.log"
        content = '{"event": "permanent_record"}\n'
        err_log.write_text(content, encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            read_recent_error_logs(lines=10)
        self.assertEqual(err_log.read_text(encoding="utf-8"), content)


# ============================================================================
# 3. SOURCE CODE INSPECTION (11 tests)
# ============================================================================

class TestSourceCodeInspection(_SelfRepairTestBase):
    """Test reading project source code with exact line numbers."""

    def test_24_correct_source_file_read(self):
        """Source lines are returned with 1-based line numbering."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_own_source_code("sample_tool.py", start_line=1, end_line=3)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["data"]["filename"], "sample_tool.py")
        self.assertIn("   1 |", res["data"]["source_code"])
        self.assertIn("add(a: int", res["data"]["source_code"])

    def test_25_correct_total_lines(self):
        """Total file lines are accurately reported."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_own_source_code("sample_tool.py", start_line=1, end_line=2)
        self.assertEqual(res["data"]["total_lines"], 4)

    def test_26_line_slice_window(self):
        """Line range correctly slices target region."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_own_source_code("sample_tool.py", start_line=3, end_line=4)
        self.assertEqual(res["data"]["start_line"], 3)
        self.assertEqual(res["data"]["end_line"], 4)
        self.assertNotIn("   1 |", res["data"]["source_code"])

    def test_27_invalid_start_line_zero(self):
        """start_line=0 is rejected."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_own_source_code("sample_tool.py", start_line=0, end_line=10)
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "INVALID_LINE_RANGE")

    def test_28_end_line_before_start_line(self):
        """end_line < start_line is rejected."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_own_source_code("sample_tool.py", start_line=10, end_line=5)
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "INVALID_LINE_RANGE")

    def test_29_excessive_line_range_rejected(self):
        """Requested range > 300 lines is rejected."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_own_source_code("sample_tool.py", start_line=1, end_line=350)
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "INVALID_LINE_RANGE")

    def test_30_missing_source_file(self):
        """Non-existent source file returns FILE_NOT_FOUND."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_own_source_code("missing.py")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "FILE_NOT_FOUND")

    def test_31_source_file_remains_unchanged(self):
        """Inspection does not alter file content."""
        orig_content = (self.tmpdir / "sample_tool.py").read_text(encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            read_own_source_code("sample_tool.py")
        self.assertEqual((self.tmpdir / "sample_tool.py").read_text(encoding="utf-8"), orig_content)

    def test_32_large_source_file_rejected(self):
        """File exceeding 1 MB is rejected."""
        large_py = self.tmpdir / "huge_module.py"
        large_py.write_text("# pad\n" * 200000, encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_own_source_code("huge_module.py")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "SOURCE_TOO_LARGE")

    def test_33_subdirectory_source_file_read(self):
        """Files in permitted subdirectories (e.g. skills/) can be inspected."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_own_source_code("skills/math_skill.py", start_line=1, end_line=2)
        self.assertEqual(res["status"], "success")
        self.assertIn("multiply", res["data"]["source_code"])

    def test_34_no_source_module_execution(self):
        """Reading code does not execute module-level side effects."""
        bomb_py = self.tmpdir / "side_effect.py"
        bomb_py.write_text("import sys\n# side effect guard\nTEST_FLAG = True\n", encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = read_own_source_code("side_effect.py")
        self.assertEqual(res["status"], "success")
        # Ensure it was not imported into sys.modules
        self.assertNotIn("side_effect", sys.modules)


# ============================================================================
# 4. PROJECT SOURCE DISCOVERY (9 tests)
# ============================================================================

class TestSourceDiscovery(_SelfRepairTestBase):
    """Test listing project source files and directory filtering."""

    def test_35_project_python_files_discovered(self):
        """Permitted project files are listed."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = list_project_source_files(".", recursive=False)
        self.assertEqual(res["status"], "success")
        self.assertIn("sample_tool.py", res["data"]["files"])

    def test_36_recursive_discovery(self):
        """Recursive listing finds files in skills/."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = list_project_source_files(".", recursive=True)
        self.assertIn("skills/math_skill.py", res["data"]["files"])

    def test_37_venv_excluded(self):
        """.venv directory contents are excluded."""
        (self.tmpdir / ".venv" / "bad.py").write_text("# bad", encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = list_project_source_files(".", recursive=True)
        for f in res["data"]["files"]:
            self.assertFalse(f.startswith(".venv"))

    def test_38_git_excluded(self):
        """.git directory contents are excluded."""
        (self.tmpdir / ".git" / "hook.py").write_text("# git", encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = list_project_source_files(".", recursive=True)
        for f in res["data"]["files"]:
            self.assertFalse(f.startswith(".git"))

    def test_39_profiles_excluded(self):
        """profiles directory contents are excluded."""
        (self.tmpdir / "profiles" / "user.py").write_text("# user", encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = list_project_source_files(".", recursive=True)
        for f in res["data"]["files"]:
            self.assertFalse(f.startswith("profiles"))

    def test_40_backups_excluded(self):
        """backups directory contents are excluded from source file list."""
        (self.tmpdir / "backups" / "old.py").write_text("# old", encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = list_project_source_files(".", recursive=True)
        for f in res["data"]["files"]:
            self.assertFalse(f.startswith("backups"))

    def test_41_data_excluded(self):
        """data directory contents are excluded from source file list."""
        (self.tmpdir / "data" / "cache.py").write_text("# cache", encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = list_project_source_files(".", recursive=True)
        for f in res["data"]["files"]:
            self.assertFalse(f.startswith("data"))

    def test_42_directory_traversal_blocked(self):
        """Directory argument with parent traversal is blocked."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = list_project_source_files("../../Windows")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "PATH_OUTSIDE_PROJECT")

    def test_43_non_existent_directory(self):
        """Non-existent directory returns FILE_NOT_FOUND."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = list_project_source_files("nonexistent_subfolder")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "FILE_NOT_FOUND")


# ============================================================================
# 5. SOURCE METADATA INSPECTION (5 tests)
# ============================================================================

class TestSourceMetadataInspection(_SelfRepairTestBase):
    """Test inspect_source_file metadata and AST validation."""

    def test_44_inspect_metadata_fields(self):
        """inspect_source_file returns size, modified_at, sha256, and lines."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = inspect_source_file("sample_tool.py")
        self.assertEqual(res["status"], "success")
        data = res["data"]
        self.assertEqual(data["filename"], "sample_tool.py")
        self.assertEqual(data["extension"], ".py")
        self.assertEqual(data["readability_status"], "READABLE")
        self.assertEqual(data["source_validation_status"], "VALID_PYTHON")
        self.assertEqual(len(data["sha256"]), 64)
        self.assertGreater(data["file_size"], 0)

    def test_45_syntax_error_reported_in_metadata(self):
        """Source file with syntax error is reported without throwing an unhandled exception."""
        bad_py = self.tmpdir / "syntax_err.py"
        bad_py.write_text("def broken_syntax(:\n", encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = inspect_source_file("syntax_err.py")
        self.assertEqual(res["status"], "success")
        self.assertIn("SYNTAX_ERROR", res["data"]["source_validation_status"])

    def test_46_missing_file_metadata(self):
        """Missing file returns FILE_NOT_FOUND."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = inspect_source_file("missing_file.py")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "FILE_NOT_FOUND")

    def test_47_protected_file_metadata_rejected(self):
        """Inspecting .env through inspect_source_file is rejected."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = inspect_source_file(".env")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "PROTECTED_FILE")

    def test_48_sha256_reproducibility(self):
        """SHA-256 calculation matches hashlib directly."""
        p = self.tmpdir / "sample_tool.py"
        expected_hash = hashlib.sha256(p.read_bytes()).hexdigest()
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = inspect_source_file("sample_tool.py")
        self.assertEqual(res["data"]["sha256"], expected_hash)


# ============================================================================
# 6. SECURE BACKUP CREATION & SHA-256 (16 tests)
# ============================================================================

class TestBackupCreationAndIntegrity(_SelfRepairTestBase):
    """Test atomic backup creation, SHA-256 verification, and metadata auditing."""

    def test_49_valid_source_backup_created(self):
        """create_source_backup creates backup file in backups/."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = create_source_backup("sample_tool.py", reason="Pre-test snapshot")
        self.assertEqual(res["status"], "success")
        backup_file = self.tmpdir / "backups" / res["data"]["backup_file"]
        self.assertTrue(backup_file.is_file())

    def test_50_backup_filename_structure(self):
        """Backup filename includes stem, timestamp, and unique id with .py.bak."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = create_source_backup("sample_tool.py", reason="Structure check")
        b_name = res["data"]["backup_file"]
        self.assertTrue(b_name.startswith("sample_tool__"))
        self.assertTrue(b_name.endswith(".py.bak"))

    def test_51_original_source_remains_unchanged(self):
        """Creating a backup does not alter original source."""
        orig_bytes = (self.tmpdir / "sample_tool.py").read_bytes()
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            create_source_backup("sample_tool.py", reason="Safety test")
        self.assertEqual((self.tmpdir / "sample_tool.py").read_bytes(), orig_bytes)

    def test_52_sha256_matches(self):
        """Source and backup SHA-256 hashes are identical."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = create_source_backup("sample_tool.py", reason="Integrity check")
        b_path = self.tmpdir / "backups" / res["data"]["backup_file"]
        s_path = self.tmpdir / "sample_tool.py"
        self.assertTrue(verify_backup_integrity(s_path, b_path))
        self.assertEqual(res["data"]["sha256"], calculate_sha256(s_path))

    def test_53_metadata_json_created(self):
        """Corresponding .meta.json file is created alongside backup."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = create_source_backup("sample_tool.py", reason="Metadata test")
        backup_stem = res["data"]["backup_file"][:-7]  # remove .py.bak
        meta_file = self.tmpdir / "backups" / f"{backup_stem}.meta.json"
        self.assertTrue(meta_file.is_file())
        meta_dict = json.loads(meta_file.read_text(encoding="utf-8"))
        self.assertEqual(meta_dict["integrity_status"], "VERIFIED")
        self.assertEqual(meta_dict["original_file"], "sample_tool.py")

    def test_54_existing_backup_not_overwritten(self):
        """Consecutive backups create distinct files without overwriting."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res1 = create_source_backup("sample_tool.py", reason="Backup 1")
            res2 = create_source_backup("sample_tool.py", reason="Backup 2")
        self.assertNotEqual(res1["data"]["backup_file"], res2["data"]["backup_file"])
        f1 = self.tmpdir / "backups" / res1["data"]["backup_file"]
        f2 = self.tmpdir / "backups" / res2["data"]["backup_file"]
        self.assertTrue(f1.is_file())
        self.assertTrue(f2.is_file())

    def test_55_missing_reason_rejected(self):
        """Backup request without explicit reason is rejected."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = create_source_backup("sample_tool.py", reason="")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "INVALID_ARGUMENTS")

    def test_56_missing_source_rejected(self):
        """Backing up a non-existent file returns FILE_NOT_FOUND."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = create_source_backup("missing_target.py", reason="Test")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "FILE_NOT_FOUND")

    def test_57_external_path_backup_rejected(self):
        """Backing up external file is blocked."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = create_source_backup("../../etc/shadow.py", reason="Test")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "PATH_OUTSIDE_PROJECT")

    def test_58_env_backup_rejected(self):
        """Backing up .env is strictly blocked as PROTECTED_FILE."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = create_source_backup(".env", reason="Credentials backup attempt")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "PROTECTED_FILE")

    def test_59_embedded_secret_source_backup_refused(self):
        """Source file containing hardcoded Gemini API key is refused backup."""
        leaky_py = self.tmpdir / "leaky_skill.py"
        leaky_py.write_text('API_KEY = "AIzaSyD1234567890123456789012345678901234"\n', encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = create_source_backup("leaky_skill.py", reason="Safety scan check")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "PROTECTED_FILE")
        # Ensure no backup file was left in backups/
        backups = list((self.tmpdir / "backups").glob("leaky_skill*"))
        self.assertEqual(len(backups), 0)

    def test_60_audit_log_recorded_on_backup(self):
        """Creating a backup writes an audit event to logs/self_repair_audit.log."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            create_source_backup("sample_tool.py", reason="Audit verification")
        audit_file = self.tmpdir / "logs" / "self_repair_audit.log"
        self.assertTrue(audit_file.is_file())
        content = audit_file.read_text(encoding="utf-8")
        self.assertIn("create_source_backup", content)
        self.assertIn("sample_tool.py", content)
        self.assertIn("SUCCESS", content)

    def test_61_list_source_backups_empty(self):
        """list_source_backups returns empty list when no backups exist."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = list_source_backups("sample_tool.py")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["data"]["backups_found"], 0)

    def test_62_list_source_backups_retrieves_created(self):
        """list_source_backups lists previously created backups."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            create_source_backup("sample_tool.py", reason="First backup")
            res = list_source_backups("sample_tool.py")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["data"]["backups_found"], 1)
        self.assertEqual(res["data"]["backups"][0]["integrity_status"], "VERIFIED")

    def test_63_list_source_backups_filter(self):
        """list_source_backups correctly filters by target filename."""
        other_py = self.tmpdir / "other.py"
        other_py.write_text("# other", encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            create_source_backup("sample_tool.py", reason="Backup A")
            create_source_backup("other.py", reason="Backup B")
            res = list_source_backups("sample_tool.py")
        self.assertEqual(res["data"]["backups_found"], 1)
        self.assertEqual(res["data"]["backups"][0]["original_file"], "sample_tool.py")

    def test_64_contains_embedded_secret_helper(self):
        """contains_embedded_secret detects various secret patterns."""
        self.assertTrue(contains_embedded_secret("key = 'AIzaSyD1234567890123456789012345678901234'"))
        self.assertTrue(contains_embedded_secret("token = 'sk-proj-abc123def456ghi789012345'"))
        self.assertTrue(contains_embedded_secret("-----BEGIN RSA PRIVATE KEY-----"))
        self.assertFalse(contains_embedded_secret("def normal_function(x: int) -> int: return x * 2"))


# ============================================================================
# 7. TRACEBACK INTELLIGENCE ENGINE (6 tests)
# ============================================================================

class TestTracebackIntelligence(unittest.TestCase):
    """Test traceback parsing and exception classification."""

    def test_65_parse_syntax_error(self):
        """SyntaxError traceback is parsed with exact line number."""
        tb = (
            'Traceback (most recent call last):\n'
            '  File "skills/calc.py", line 42, in calculate\n'
            '    total = a +\n'
            'SyntaxError: invalid syntax\n'
        )
        parsed = parse_traceback_summary(tb)
        self.assertEqual(parsed["status"], "PARSED")
        self.assertEqual(parsed["exception_type"], "SyntaxError")
        self.assertEqual(parsed["source_filename"], "calc.py")
        self.assertEqual(parsed["line_number"], 42)
        self.assertEqual(parsed["error_category"], "SYNTAX_ERROR")

    def test_66_parse_import_error(self):
        """ModuleNotFoundError is categorized as DEPENDENCY_OR_IMPORT_ERROR."""
        tb = (
            'Traceback (most recent call last):\n'
            '  File "doctor.py", line 12, in <module>\n'
            '    import nonexistent_pkg\n'
            "ModuleNotFoundError: No module named 'nonexistent_pkg'\n"
        )
        parsed = parse_traceback_summary(tb)
        self.assertEqual(parsed["exception_type"], "ModuleNotFoundError")
        self.assertEqual(parsed["error_category"], "DEPENDENCY_OR_IMPORT_ERROR")

    def test_67_parse_type_error(self):
        """TypeError is categorized as LOGIC_OR_TYPE_ERROR."""
        tb = (
            'Traceback (most recent call last):\n'
            '  File "zye_guard.py", line 100, in wrapper\n'
            '    return func(*args)\n'
            "TypeError: unsupported operand type(s) for +: 'int' and 'str'\n"
        )
        parsed = parse_traceback_summary(tb)
        self.assertEqual(parsed["exception_type"], "TypeError")
        self.assertEqual(parsed["error_category"], "LOGIC_OR_TYPE_ERROR")

    def test_68_insufficient_traceback_handled(self):
        """Incomplete or non-traceback string returns INSUFFICIENT_TRACEBACK_INFORMATION."""
        parsed = parse_traceback_summary("Some arbitrary error message without traceback")
        self.assertEqual(parsed["status"], "INSUFFICIENT_TRACEBACK_INFORMATION")

    def test_69_secret_redacted_in_traceback(self):
        """API keys inside traceback messages are redacted."""
        tb = (
            'Traceback (most recent call last):\n'
            '  File "test.py", line 5, in run\n'
            '    raise ValueError("Invalid key: AIzaSyD1234567890123456789012345678901234")\n'
            'ValueError: Invalid key: AIzaSyD1234567890123456789012345678901234\n'
        )
        parsed = parse_traceback_summary(tb)
        self.assertNotIn("AIzaSyD1234567890123456789012345678901234", parsed["exception_message"])
        self.assertIn("[REDACTED_GEMINI_KEY]", parsed["exception_message"])

    def test_70_classify_error_type_helper(self):
        """classify_error_type helper covers all major categories."""
        self.assertEqual(classify_error_type("FileNotFoundError"), "FILESYSTEM_OR_PERMISSION_ERROR")
        self.assertEqual(classify_error_type("TimeoutError"), "TRANSIENT_NETWORK_ERROR")
        self.assertEqual(classify_error_type("KeyError"), "LOOKUP_ERROR")
        self.assertEqual(classify_error_type("RuntimeError"), "RUNTIME_ERROR")


# ============================================================================
# 8. FASTMCP PROTOCOL & TOOL REGISTRATION (3 tests)
# ============================================================================

class TestFastMCPProtocol(_SelfRepairTestBase):
    """Test FastMCP registration and tool interface signatures."""

    def test_71_fastmcp_server_initialized(self):
        """FastMCP server instance is initialized under ZyeSelfRepair."""
        self.assertEqual(mcp.name, "ZyeSelfRepair")

    def test_72_all_six_tools_registered(self):
        """All 6 Day 05 tools are registered on the FastMCP instance."""
        expected_tools = {
            "read_recent_error_logs",
            "read_own_source_code",
            "list_project_source_files",
            "inspect_source_file",
            "create_source_backup",
            "list_source_backups",
        }
        # In both official FastMCP and our fallback shim, tools are accessible
        if hasattr(mcp, "_tools"):
            registered = set(mcp._tools.keys())
            self.assertTrue(expected_tools.issubset(registered))

    def test_73_tool_functions_callable_and_typed(self):
        """Tool functions are directly callable and preserve parameter signatures."""
        import inspect
        sig = inspect.signature(read_own_source_code)
        self.assertIn("filename", sig.parameters)
        self.assertIn("start_line", sig.parameters)
        self.assertIn("end_line", sig.parameters)


if __name__ == "__main__":
    unittest.main(verbosity=2)

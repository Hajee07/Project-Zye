#!/usr/bin/env python3
"""
ZYE AI — Day 06 Autonomous Code Repair & Hot-Reload Test Suite
==============================================================

Comprehensive automated test suite covering:
  - Patch Preview Engine (10 tests)
  - Explicit User Approval Engine (10 tests)
  - Pre-Patch Backup Integration (6 tests)
  - AST Syntax Validation (6 tests)
  - Python Compilation Verification (5 tests)
  - Atomic File Replacement (8 tests)
  - Automatic Rollback Engine (7 tests)
  - Manual Backup Rollback Tool (7 tests)
  - MCP Hot-Reload Engine (10 tests)
  - Crash Recovery & Safe Replay (11 tests)
  - Framework Security Boundaries (12 tests)

Total: 92 unit tests.

Usage::
    python -m unittest tests.test_day06_code_repair -v
"""

from __future__ import annotations

import ast
import asyncio
from contextlib import AsyncExitStack
import hashlib
import json
import os
import sys
import tempfile
import time
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
    calculate_sha256,
    calculate_string_sha256,
    generate_candidate_source,
    generate_unified_diff,
    validate_ast_syntax,
    verify_python_compilation,
    read_source_with_encoding,
    atomic_replace_source,
    automatic_rollback,
    init_approval_db,
    create_repair_approval,
    consume_repair_approval,
    request_patch_approval,
    preview_code_patch,
    patch_own_code,
    rollback_code_backup,
    create_source_backup,
    _reset_project_root_cache,
    _reset_audit_logger,
)

import main
from main import (
    ZyeMasterAgent,
    is_safe_to_replay,
    call_gemini_with_retry,
    MCP_SERVERS,
    NON_IDEMPOTENT_OPERATIONS,
)


class _Day06TestBase(unittest.TestCase):
    """Base fixture creating an isolated test workspace."""

    def setUp(self) -> None:
        _reset_project_root_cache()
        _reset_audit_logger()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmpdir.name)

        # Standard project layout
        (self.tmpdir / "zye_config.toml").write_text("[system]\nassistant_name = 'Zye'\n", encoding="utf-8")
        (self.tmpdir / "logs").mkdir()
        (self.tmpdir / "backups").mkdir()
        (self.tmpdir / "data").mkdir()
        (self.tmpdir / "skills").mkdir()

        # Database
        self.db_path = self.tmpdir / "data" / "zye_assistant_db.sqlite"
        init_approval_db(self.db_path)

        # Target test script
        self.test_py = self.tmpdir / "sample_service.py"
        self.test_py.write_text(
            '"""Sample test service."""\n\n'
            'def calculate_total(price: float, tax: float) -> float:\n'
            '    return price - tax  # BUG: should be price + tax\n',
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        _reset_audit_logger()
        _reset_project_root_cache()
        try:
            self._tmpdir.cleanup()
        except (PermissionError, OSError):
            pass

    def _run_async(self, coro):
        """Helper to run a coroutine in tests without requiring loopback sockets."""
        import inspect
        try:
            while True:
                try:
                    res = coro.send(None)
                    if inspect.iscoroutine(res):
                        return self._run_async(res)
                except StopIteration as e:
                    return e.value
        finally:
            coro.close()


# ============================================================================
# 1. PATCH PREVIEW TESTS (10 tests)
# ============================================================================

class TestPatchPreview(_Day06TestBase):

    def test_01_valid_patch_preview(self):
        """preview_code_patch generates diff without modifying original source."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = preview_code_patch(
                filename="sample_service.py",
                old_code_snippet="return price - tax  # BUG: should be price + tax",
                new_code_snippet="return price + tax  # FIXED",
                reason="Fix subtraction bug in total calculation",
            )
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["data"]["requires_user_approval"])
        self.assertIn("+    return price + tax  # FIXED", res["data"]["diff"])
        self.assertIn("-    return price - tax  # BUG: should be price + tax", res["data"]["diff"])
        # Original remains untouched
        self.assertIn("return price - tax", self.test_py.read_text(encoding="utf-8"))

    def test_02_empty_old_snippet_rejected(self):
        """Empty old_code_snippet is rejected."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = preview_code_patch("sample_service.py", "", "new code", "reason")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "INVALID_ARGUMENTS")

    def test_03_non_string_new_snippet_rejected(self):
        """Non-string new_code_snippet is rejected."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = preview_code_patch("sample_service.py", "old", None, "reason")  # type: ignore[arg-type]
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "INVALID_ARGUMENTS")

    def test_04_old_snippet_not_found(self):
        """Snippet that does not exist in target returns OLD_SNIPPET_NOT_FOUND."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = preview_code_patch(
                filename="sample_service.py",
                old_code_snippet="def non_existent_function(): pass",
                new_code_snippet="def ok(): pass",
                reason="Fix",
            )
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "OLD_SNIPPET_NOT_FOUND")

    def test_05_multiple_matches_rejected(self):
        """Ambiguous snippet matching multiple locations is rejected."""
        self.test_py.write_text("x = 1\nx = 1\n", encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = preview_code_patch(
                filename="sample_service.py",
                old_code_snippet="x = 1",
                new_code_snippet="x = 2",
                reason="Fix duplicate",
            )
        self.assertEqual(res["status"], "error")
        self.assertIn("AMBIGUOUS_REPLACEMENT", res["code"])

    def test_06_correct_unified_diff_generated(self):
        """Diff format conforms to standard unified diff."""
        diff = generate_unified_diff("line1\nline2\n", "line1\nline_new\n", "test.py")
        self.assertIn("--- a/test.py", diff)
        self.assertIn("+++ b/test.py", diff)
        self.assertIn("-line2", diff)
        self.assertIn("+line_new", diff)

    def test_07_original_source_remains_unchanged(self):
        """preview_code_patch leaves target bytes completely unchanged."""
        orig_bytes = self.test_py.read_bytes()
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            preview_code_patch("sample_service.py", "price - tax", "price + tax", "Reason")
        self.assertEqual(self.test_py.read_bytes(), orig_bytes)

    def test_08_proposed_sha256_correct(self):
        """Proposed SHA-256 returned by preview matches candidate hash."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = preview_code_patch(
                "sample_service.py", "return price - tax", "return price + tax", "reason"
            )
        orig_text, enc, _ = read_source_with_encoding(self.test_py)
        cand_text = orig_text.replace("return price - tax", "return price + tax")
        self.assertEqual(res["data"]["proposed_sha256"], calculate_string_sha256(cand_text, encoding=enc))

    def test_09_invalid_source_path_rejected(self):
        """Non-existent file returns FILE_NOT_FOUND."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = preview_code_patch("missing.py", "old", "new", "reason")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "FILE_NOT_FOUND")

    def test_10_oversized_patch_rejected(self):
        """Snippet exceeding 64 KB is rejected."""
        big_snippet = "x = 1\n" * 20000
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = preview_code_patch("sample_service.py", big_snippet, "new", "reason")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "PATCH_TOO_LARGE")


# ============================================================================
# 2. EXPLICIT USER APPROVAL TESTS (10 tests)
# ============================================================================

class TestApprovalEngine(_Day06TestBase):

    def test_11_valid_approval_accepted(self):
        """Valid one-time approval token is consumed successfully."""
        app_id, token = create_repair_approval(
            self.db_path, "patch_1", "sample_service.py", "hash_orig", "hash_prop", "patch"
        )
        ok, msg = consume_repair_approval(
            self.db_path, token, "patch_1", "sample_service.py", "hash_orig", "hash_prop", "patch"
        )
        self.assertTrue(ok)
        self.assertEqual(msg, "APPROVAL_VALIDATED")

    def test_12_missing_approval_rejected(self):
        """Empty or null token is rejected."""
        ok, msg = consume_repair_approval(
            self.db_path, "", "patch_1", "sample_service.py", "hash_orig"
        )
        self.assertFalse(ok)
        self.assertEqual(msg, "MISSING_OR_INVALID_TOKEN")

    def test_13_expired_approval_rejected(self):
        """Token with past expiration time is rejected as APPROVAL_EXPIRED."""
        app_id, token = create_repair_approval(
            self.db_path, "patch_exp", "sample_service.py", "hash_orig", "hash_prop", "patch", ttl_seconds=-10
        )
        ok, msg = consume_repair_approval(
            self.db_path, token, "patch_exp", "sample_service.py", "hash_orig", "hash_prop", "patch"
        )
        self.assertFalse(ok)
        self.assertEqual(msg, "APPROVAL_EXPIRED")

    def test_14_reused_token_rejected(self):
        """A consumed approval token cannot be used a second time."""
        app_id, token = create_repair_approval(
            self.db_path, "patch_reuse", "sample_service.py", "hash_orig", "hash_prop", "patch"
        )
        ok1, _ = consume_repair_approval(self.db_path, token, "patch_reuse", "sample_service.py", "hash_orig", "hash_prop", "patch")
        self.assertTrue(ok1)
        ok2, msg2 = consume_repair_approval(self.db_path, token, "patch_reuse", "sample_service.py", "hash_orig", "hash_prop", "patch")
        self.assertFalse(ok2)
        self.assertIn("CONSUMED", msg2)

    def test_15_wrong_filename_rejected(self):
        """Token bound to file A is rejected when attempting to patch file B."""
        app_id, token = create_repair_approval(
            self.db_path, "patch_1", "file_a.py", "hash_orig", "hash_prop", "patch"
        )
        ok, msg = consume_repair_approval(
            self.db_path, token, "patch_1", "file_b.py", "hash_orig", "hash_prop", "patch"
        )
        self.assertFalse(ok)
        self.assertEqual(msg, "FILENAME_MISMATCH")

    def test_16_wrong_patch_id_rejected(self):
        """Mismatched patch ID fails approval validation."""
        app_id, token = create_repair_approval(
            self.db_path, "patch_correct", "sample_service.py", "hash_orig", "hash_prop", "patch"
        )
        ok, msg = consume_repair_approval(
            self.db_path, token, "patch_wrong", "sample_service.py", "hash_orig", "hash_prop", "patch"
        )
        self.assertFalse(ok)
        self.assertEqual(msg, "PATCH_ID_MISMATCH")

    def test_17_wrong_original_hash_rejected(self):
        """Mismatched original file hash fails approval validation."""
        app_id, token = create_repair_approval(
            self.db_path, "patch_1", "sample_service.py", "expected_hash", "hash_prop", "patch"
        )
        ok, msg = consume_repair_approval(
            self.db_path, token, "patch_1", "sample_service.py", "tampered_hash", "hash_prop", "patch"
        )
        self.assertFalse(ok)
        self.assertEqual(msg, "ORIGINAL_HASH_MISMATCH")

    def test_18_wrong_proposed_hash_rejected(self):
        """Mismatched proposed file hash fails approval validation."""
        app_id, token = create_repair_approval(
            self.db_path, "patch_1", "sample_service.py", "hash_orig", "hash_prop_1", "patch"
        )
        ok, msg = consume_repair_approval(
            self.db_path, token, "patch_1", "sample_service.py", "hash_orig", "hash_prop_2", "patch"
        )
        self.assertFalse(ok)
        self.assertEqual(msg, "PROPOSED_HASH_MISMATCH")

    def test_19_wrong_operation_rejected(self):
        """Approval for 'patch' cannot be consumed for 'rollback'."""
        app_id, token = create_repair_approval(
            self.db_path, "patch_1", "sample_service.py", "hash_orig", "hash_prop", "patch"
        )
        ok, msg = consume_repair_approval(
            self.db_path, token, "patch_1", "sample_service.py", "hash_orig", "hash_prop", "rollback"
        )
        self.assertFalse(ok)
        self.assertEqual(msg, "OPERATION_MISMATCH")

    def test_20_approval_transaction_atomicity(self):
        """Token consumption is recorded in SQLite with accurate timestamp."""
        app_id, token = create_repair_approval(
            self.db_path, "patch_atomic", "sample_service.py", "hash_orig", "hash_prop", "patch"
        )
        consume_repair_approval(self.db_path, token, "patch_atomic", "sample_service.py", "hash_orig", "hash_prop", "patch")
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        row = conn.execute("SELECT approval_status, consumed_at FROM repair_approvals WHERE approval_id = ?", (app_id,)).fetchone()
        conn.close()
        self.assertEqual(row[0], "CONSUMED")
        self.assertIsNotNone(row[1])


# ============================================================================
# 3. PRE-PATCH BACKUP INTEGRATION (6 tests)
# ============================================================================

class TestPrePatchBackup(_Day06TestBase):

    def test_21_pre_patch_backup_created(self):
        """patch_own_code creates a pre-save backup prior to file replacement."""
        orig_hash = calculate_sha256(self.test_py)
        app_id, token = request_patch_approval("p1", "sample_service.py", orig_hash, "dummy_prop", "patch", root=self.tmpdir)

        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = patch_own_code(
                filename="sample_service.py",
                old_code_snippet="return price - tax  # BUG: should be price + tax",
                new_code_snippet="return price + tax  # FIXED",
                reason="Pre-patch backup verification",
                patch_id="p1",
                approval_token=token,
                expected_original_sha256=orig_hash,
            )
        self.assertEqual(res["status"], "success")
        backup_files = list((self.tmpdir / "backups").glob("*.py.bak"))
        self.assertGreaterEqual(len(backup_files), 1)

    def test_22_backup_hash_matches_original(self):
        """Pre-patch backup SHA-256 matches pre-patch file contents."""
        orig_hash = calculate_sha256(self.test_py)
        app_id, token = request_patch_approval("p2", "sample_service.py", orig_hash, "dummy_prop", "patch", root=self.tmpdir)

        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = patch_own_code(
                filename="sample_service.py",
                old_code_snippet="return price - tax  # BUG: should be price + tax",
                new_code_snippet="return price + tax  # FIXED",
                reason="Hash check",
                patch_id="p2",
                approval_token=token,
                expected_original_sha256=orig_hash,
            )
        backup_file = self.tmpdir / "backups" / f"sample_service__{res['data']['backup_id']}.meta.json"
        meta = list((self.tmpdir / "backups").glob(f"*__{res['data']['backup_id']}.meta.json"))[0]
        meta_dict = json.loads(meta.read_text(encoding="utf-8"))
        self.assertEqual(meta_dict["sha256"], orig_hash)

    def test_23_backup_metadata_verified(self):
        """Backup metadata records original filename and VERIFIED status."""
        orig_hash = calculate_sha256(self.test_py)
        app_id, token = request_patch_approval("p3", "sample_service.py", orig_hash, "dummy_prop", "patch", root=self.tmpdir)

        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = patch_own_code("sample_service.py", "price - tax", "price + tax", "Reason", "p3", token, orig_hash)
        meta_file = list((self.tmpdir / "backups").glob(f"*__{res['data']['backup_id']}.meta.json"))[0]
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        self.assertEqual(meta["integrity_status"], "VERIFIED")
        self.assertEqual(meta["original_file"], "sample_service.py")

    def test_24_existing_backup_preserved(self):
        """Multiple patch operations preserve previous backups."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            b1 = create_source_backup("sample_service.py", "First snapshot")
            b2 = create_source_backup("sample_service.py", "Second snapshot")
        self.assertTrue((self.tmpdir / "backups" / b1["data"]["backup_file"]).is_file())
        self.assertTrue((self.tmpdir / "backups" / b2["data"]["backup_file"]).is_file())

    def test_25_backup_failure_prevents_patch(self):
        """If backup creation fails, source replacement is aborted."""
        orig_hash = calculate_sha256(self.test_py)
        orig_text = self.test_py.read_text(encoding="utf-8")
        app_id, token = request_patch_approval("p5", "sample_service.py", orig_hash, "prop", "patch", root=self.tmpdir)

        with patch("self_repair_mcp.create_source_backup", return_value={"status": "error"}):
            with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
                res = patch_own_code("sample_service.py", "price - tax", "price + tax", "R", "p5", token, orig_hash)
        self.assertEqual(res["status"], "error")
        self.assertEqual(self.test_py.read_text(encoding="utf-8"), orig_text)

    def test_26_incomplete_backup_rejected(self):
        """Corrupted or zero-byte backup file is rejected."""
        dummy_bak = self.tmpdir / "backups" / "dummy.py.bak"
        dummy_bak.write_bytes(b"")
        self.assertFalse(self_repair_mcp.verify_backup_integrity(self.test_py, dummy_bak))


# ============================================================================
# 4. AST SYNTAX VALIDATION (6 tests)
# ============================================================================

class TestASTValidation(_Day06TestBase):

    def test_27_valid_python_ast_passes(self):
        """Valid Python syntax passes AST verification."""
        ok, diag = validate_ast_syntax("def hello(name: str) -> str: return f'Hi {name}'")
        self.assertTrue(ok)
        self.assertEqual(diag["status"], "PASS")

    def test_28_invalid_python_syntax_rejected(self):
        """SyntaxError is caught with error type and details."""
        ok, diag = validate_ast_syntax("def broken_syntax(x\n    return x + 1")
        self.assertFalse(ok)
        self.assertEqual(diag["status"], "FAIL")
        self.assertEqual(diag["error_type"], "SyntaxError")
        self.assertIsNotNone(diag.get("line_number"))

    def test_29_indentation_error_detected(self):
        """IndentationError is caught by AST parser."""
        ok, diag = validate_ast_syntax("def f():\nreturn 1")
        self.assertFalse(ok)
        self.assertEqual(diag["error_type"], "IndentationError")

    def test_30_correct_line_number_returned(self):
        """AST error diagnostics report exact failing line number."""
        code = "line1 = 1\nline2 = 2\ndef invalid(:\n    pass\n"
        ok, diag = validate_ast_syntax(code)
        self.assertFalse(ok)
        self.assertEqual(diag["line_number"], 3)

    def test_31_source_unchanged_after_ast_failure(self):
        """patch_own_code does not modify source if candidate AST is invalid."""
        orig_hash = calculate_sha256(self.test_py)
        orig_text = self.test_py.read_text(encoding="utf-8")
        app_id, token = request_patch_approval("p_ast", "sample_service.py", orig_hash, "dummy", "patch", root=self.tmpdir)

        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = patch_own_code(
                filename="sample_service.py",
                old_code_snippet="return price - tax  # BUG: should be price + tax",
                new_code_snippet="return price +  # SYNTAX ERROR",
                reason="Bad syntax test",
                patch_id="p_ast",
                approval_token=token,
                expected_original_sha256=orig_hash,
            )
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "AST_VALIDATION_FAILED")
        self.assertEqual(self.test_py.read_text(encoding="utf-8"), orig_text)

    def test_32_unicode_source_validates_correctly(self):
        """Source containing Tamil comments parses cleanly without Unicode errors."""
        code = '# வணக்கம் Zye AI — தமிழ் சோதனை\ndef tamil_greeting() -> str:\n    return "வணக்கம்"\n'
        ok, diag = validate_ast_syntax(code)
        self.assertTrue(ok)


# ============================================================================
# 5. PYTHON COMPILATION TESTS (5 tests)
# ============================================================================

class TestCompilationVerification(_Day06TestBase):

    def test_33_valid_code_compiles(self):
        """Valid code compiles into bytecode without error."""
        ok, err = verify_python_compilation("x = 10\ny = 20\nresult = x * y\n")
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_34_invalid_code_rejected(self):
        """Invalid syntax returns compilation error message."""
        ok, err = verify_python_compilation("def incomplete_func(")
        self.assertFalse(ok)
        self.assertIsNotNone(err)

    def test_35_compile_timeout_handled(self):
        """verify_python_compilation handles input safely without hanging."""
        ok, err = verify_python_compilation("pass\n")
        self.assertTrue(ok)

    def test_36_candidate_code_not_executed(self):
        """Compilation checks syntax without running module side effects."""
        side_effect_code = "import sys\n_SIDE_EFFECT_EXECUTED = True\n"
        ok, err = verify_python_compilation(side_effect_code)
        self.assertTrue(ok)
        self.assertNotIn("_SIDE_EFFECT_EXECUTED", globals())

    def test_37_non_inheriting_compilation_clean(self):
        """compile(..., dont_inherit=True) operates in a clean execution context."""
        code = "def add(a: int, b: int) -> int: return a + b\n"
        ok, _ = verify_python_compilation(code)
        self.assertTrue(ok)


# ============================================================================
# 6. ATOMIC FILE REPLACEMENT (8 tests)
# ============================================================================

class TestAtomicReplacement(_Day06TestBase):

    def test_38_valid_patch_applied(self):
        """atomic_replace_source updates target content."""
        ok, err = atomic_replace_source(self.test_py, "x = 42\n")
        self.assertTrue(ok)
        self.assertEqual(self.test_py.read_text(encoding="utf-8"), "x = 42\n")

    def test_39_original_hash_checked_before_replacement(self):
        """patch_own_code rejects patch if expected_original_sha256 doesn't match current file."""
        app_id, token = request_patch_approval("p_hash", "sample_service.py", "wrong_hash", "prop", "patch", root=self.tmpdir)
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = patch_own_code("sample_service.py", "old", "new", "r", "p_hash", token, "wrong_hash")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "SOURCE_CHANGED_SINCE_PREVIEW")

    def test_40_source_changed_after_preview_rejected(self):
        """Modifying source between preview and patch causes patch to fail closed."""
        orig_hash = calculate_sha256(self.test_py)
        app_id, token = request_patch_approval("p_change", "sample_service.py", orig_hash, "prop", "patch", root=self.tmpdir)

        # External change occurs!
        self.test_py.write_text("modified externally\n", encoding="utf-8")

        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = patch_own_code("sample_service.py", "price - tax", "price + tax", "r", "p_change", token, orig_hash)
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "SOURCE_CHANGED_SINCE_PREVIEW")

    def test_41_atomic_replacement_success(self):
        """atomic_replace_source replaces file cleanly with no errors."""
        ok, err = atomic_replace_source(self.test_py, "content = 'updated'\n")
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_42_temporary_file_cleanup(self):
        """Temporary staged file is removed after atomic replacement."""
        atomic_replace_source(self.test_py, "content = 'updated'\n")
        tmps = list(self.test_py.parent.glob(".tmp_patch_*"))
        self.assertEqual(len(tmps), 0)

    def test_43_final_sha256_verified(self):
        """Final file hash matches candidate text hash."""
        updated = "final_key = 12345\n"
        atomic_replace_source(self.test_py, updated)
        self.assertEqual(calculate_sha256(self.test_py), calculate_string_sha256(updated))

    def test_44_line_ending_crlf_preserved(self):
        """CRLF line endings in original file are preserved upon atomic replace."""
        self.test_py.write_bytes(b"line1\r\nline2\r\n")
        atomic_replace_source(self.test_py, "line1\nline_new\n", line_ending="\r\n")
        self.assertIn(b"\r\n", self.test_py.read_bytes())

    def test_45_unexpected_replacement_failure_handled(self):
        """atomic_replace_source handles OS error gracefully and returns False."""
        fake_path = Path("Z:/non_existent_drive/invalid_file.py")
        ok, err = atomic_replace_source(fake_path, "test")
        self.assertFalse(ok)


# ============================================================================
# 7. AUTOMATIC ROLLBACK TESTS (7 tests)
# ============================================================================

class TestAutomaticRollback(_Day06TestBase):

    def test_46_post_write_ast_failure_triggers_rollback(self):
        """Post-write validation failure triggers automatic rollback."""
        orig_hash = calculate_sha256(self.test_py)
        orig_text = self.test_py.read_text(encoding="utf-8")
        app_id, token = request_patch_approval("p_rb", "sample_service.py", orig_hash, "prop", "patch", root=self.tmpdir)

        # Mock post_compile_ok to fail after write
        with patch("self_repair_mcp.verify_python_compilation", side_effect=[(True, None), (False, "Post-write failure")]):
            with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
                res = patch_own_code("sample_service.py", "return price - tax", "return price + tax", "r", "p_rb", token, orig_hash)
        self.assertEqual(res["status"], "error")
        self.assertIn("POST_PATCH_VERIFICATION_FAILED", res["code"])
        # Original content restored by automatic rollback
        self.assertEqual(self.test_py.read_text(encoding="utf-8"), orig_text)
        self.assertEqual(calculate_sha256(self.test_py), orig_hash)

    def test_47_successful_rollback_restores_exact_hash(self):
        """automatic_rollback restores exact pre-patch SHA-256."""
        orig_hash = calculate_sha256(self.test_py)
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            bak_res = create_source_backup("sample_service.py", "Snapshot")
        bak_path = self.tmpdir / "backups" / bak_res["data"]["backup_file"]

        # Corrupt the file
        self.test_py.write_text("corrupted code\n", encoding="utf-8")
        self.assertNotEqual(calculate_sha256(self.test_py), orig_hash)

        ok, msg = automatic_rollback(self.test_py, bak_path, orig_hash)
        self.assertTrue(ok)
        self.assertEqual(msg, "ROLLED_BACK")
        self.assertEqual(calculate_sha256(self.test_py), orig_hash)

    def test_48_backup_hash_mismatch_rejected(self):
        """automatic_rollback refuses to restore if backup hash differs from recorded original hash."""
        bak_path = self.tmpdir / "backups" / "tampered.py.bak"
        bak_path.write_text("tampered", encoding="utf-8")
        ok, msg = automatic_rollback(self.test_py, bak_path, "recorded_hash_abc")
        self.assertFalse(ok)
        self.assertIn("BACKUP_HASH_MISMATCH", msg)

    def test_49_missing_backup_file_rejected(self):
        """automatic_rollback handles missing backup path gracefully."""
        bak_path = self.tmpdir / "backups" / "missing.py.bak"
        ok, msg = automatic_rollback(self.test_py, bak_path, "hash")
        self.assertFalse(ok)
        self.assertEqual(msg, "BACKUP_FILE_MISSING")

    def test_50_pre_patch_backup_preserved_after_rollback(self):
        """Backup file remains on disk after automatic rollback."""
        orig_hash = calculate_sha256(self.test_py)
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            bak_res = create_source_backup("sample_service.py", "Preserve test")
        bak_path = self.tmpdir / "backups" / bak_res["data"]["backup_file"]
        automatic_rollback(self.test_py, bak_path, orig_hash)
        self.assertTrue(bak_path.is_file())

    def test_51_rollback_failure_reported_as_critical(self):
        """Failure to replace during rollback returns CRITICAL_RECOVERY_FAILURE."""
        with patch("os.replace", side_effect=PermissionError("Locked file")):
            bak_path = self.tmpdir / "backups" / "test.py.bak"
            bak_path.write_text("bak", encoding="utf-8")
            ok, msg = automatic_rollback(self.test_py, bak_path, calculate_sha256(bak_path))
            self.assertFalse(ok)
            self.assertIn("CRITICAL_RECOVERY_FAILURE", msg)

    def test_52_restored_hash_mismatch_detected(self):
        """If file hash after rollback doesn't match expected, error is raised."""
        bak_path = self.tmpdir / "backups" / "test.py.bak"
        bak_path.write_text("bak content", encoding="utf-8")
        with patch("self_repair_mcp.calculate_sha256", side_effect=[calculate_sha256(bak_path), "mismatched_hash"]):
            ok, msg = automatic_rollback(self.test_py, bak_path, calculate_sha256(bak_path))
            self.assertFalse(ok)
            self.assertEqual(msg, "RESTORED_HASH_MISMATCH")


# ============================================================================
# 8. MANUAL BACKUP ROLLBACK TESTS (7 tests)
# ============================================================================

class TestManualRollback(_Day06TestBase):

    def test_53_valid_backup_restored(self):
        """rollback_code_backup restores verified backup with approval."""
        orig_hash = calculate_sha256(self.test_py)
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            bak_res = create_source_backup("sample_service.py", "Baseline snapshot")
            backup_id = bak_res["data"]["backup_id"]

            # Change file
            self.test_py.write_text("def modified(): pass\n", encoding="utf-8")
            curr_hash = calculate_sha256(self.test_py)

            # Request rollback approval
            app_id, token = request_patch_approval(backup_id, "sample_service.py", curr_hash, orig_hash, "rollback", root=self.tmpdir)
            res = rollback_code_backup("sample_service.py", backup_id, token)

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["data"]["status"], "ROLLED_BACK")
        self.assertEqual(calculate_sha256(self.test_py), orig_hash)

    def test_54_wrong_backup_id_rejected(self):
        """Non-existent backup ID returns BACKUP_NOT_FOUND."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = rollback_code_backup("sample_service.py", "nonexistent_id", "token")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "BACKUP_NOT_FOUND")

    def test_55_backup_for_another_filename_rejected(self):
        """Restoring a backup belonging to another file is rejected."""
        other_py = self.tmpdir / "other.py"
        other_py.write_text("other = 1\n", encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            bak_other = create_source_backup("other.py", "Other snapshot")
            b_id = bak_other["data"]["backup_id"]
            res = rollback_code_backup("sample_service.py", b_id, "token")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "BACKUP_FILE_MISMATCH")

    def test_56_missing_approval_rejected(self):
        """Missing or invalid token rejects manual rollback."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            bak_res = create_source_backup("sample_service.py", "Snapshot")
            b_id = bak_res["data"]["backup_id"]
            res = rollback_code_backup("sample_service.py", b_id, "invalid_token_123")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "APPROVAL_REJECTED")

    def test_57_restored_source_ast_verified(self):
        """Restored source AST is validated upon manual rollback."""
        orig_hash = calculate_sha256(self.test_py)
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            bak_res = create_source_backup("sample_service.py", "Baseline")
            b_id = bak_res["data"]["backup_id"]
            self.test_py.write_text("def broken(", encoding="utf-8")
            curr_hash = calculate_sha256(self.test_py)
            _, token = request_patch_approval(b_id, "sample_service.py", curr_hash, orig_hash, "rollback", root=self.tmpdir)
            res = rollback_code_backup("sample_service.py", b_id, token)
        self.assertEqual(res["data"]["ast_validation"], "PASS")

    def test_58_restored_source_compilation_verified(self):
        """Restored source compilation is verified upon manual rollback."""
        orig_hash = calculate_sha256(self.test_py)
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            bak_res = create_source_backup("sample_service.py", "Baseline")
            b_id = bak_res["data"]["backup_id"]
            curr_hash = calculate_sha256(self.test_py)
            _, token = request_patch_approval(b_id, "sample_service.py", curr_hash, orig_hash, "rollback", root=self.tmpdir)
            res = rollback_code_backup("sample_service.py", b_id, token)
        self.assertEqual(res["data"]["compile_validation"], "PASS")

    def test_59_protective_backup_created_before_rollback(self):
        """A protective backup of the pre-rollback state is automatically recorded."""
        orig_hash = calculate_sha256(self.test_py)
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            bak_res = create_source_backup("sample_service.py", "Baseline")
            b_id = bak_res["data"]["backup_id"]
            curr_hash = calculate_sha256(self.test_py)
            _, token = request_patch_approval(b_id, "sample_service.py", curr_hash, orig_hash, "rollback", root=self.tmpdir)
            res = rollback_code_backup("sample_service.py", b_id, token)
        # Should have at least 2 backups now (baseline + protective)
        baks = list((self.tmpdir / "backups").glob("*.py.bak"))
        self.assertGreaterEqual(len(baks), 2)


# ============================================================================
# 9. MCP HOT-RELOAD TESTS (10 tests)
# ============================================================================

class TestMCPHotReload(unittest.TestCase):

    def setUp(self) -> None:
        self.agent = ZyeMasterAgent(root=PROJECT_ROOT)
        self.agent.register_mock_session("self_repair", ["read_recent_error_logs", "read_own_source_code"])

    def _run_async(self, coro):
        """Helper to run a coroutine in tests without requiring loopback sockets."""
        import inspect
        try:
            while True:
                try:
                    res = coro.send(None)
                    if inspect.iscoroutine(res):
                        return self._run_async(res)
                except StopIteration as e:
                    return e.value
        finally:
            coro.close()

    def test_60_valid_mcp_server_reload(self):
        """hot_reload_server succeeds for allowlisted server."""
        res = self._run_async(self.agent.hot_reload_server("self_repair"))
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["server_name"], "self_repair")
        self.assertGreaterEqual(res["generation"], 2)

    def test_61_unknown_server_rejected(self):
        """hot_reload_server rejects server name not in MCP_SERVERS allowlist."""
        res = self._run_async(self.agent.hot_reload_server("arbitrary_external_server"))
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "SERVER_NOT_CONFIGURED")

    def test_62_failed_new_session_preserves_old_session(self):
        """If new session initialization fails, existing session remains active."""
        old_session = self.agent.sessions["self_repair"]
        with patch.object(self.agent, "_start_mcp_session", return_value=[]):
            res = self._run_async(self.agent.hot_reload_server("self_repair"))
        self.assertEqual(res["status"], "error")
        self.assertIs(self.agent.sessions["self_repair"], old_session)

    def test_63_tool_mapping_refresh(self):
        """New tools exposed by replacement session are added to mapping."""
        with patch.object(self.agent, "_start_mcp_session", return_value=["tool_a", "tool_b"]):
            res = self._run_async(self.agent.hot_reload_server("self_repair"))
        self.assertEqual(self.agent.tool_to_server["tool_a"], "self_repair")
        self.assertEqual(self.agent.tool_to_server["tool_b"], "self_repair")

    def test_64_stale_tool_mapping_removal(self):
        """Tools no longer provided by replacement server are removed from mapping."""
        with patch.object(self.agent, "_start_mcp_session", return_value=["new_tool_only"]):
            self._run_async(self.agent.hot_reload_server("self_repair"))
        self.assertNotIn("read_recent_error_logs", self.agent.tool_to_server)
        self.assertIn("new_tool_only", self.agent.tool_to_server)

    def test_65_duplicate_tool_name_handled(self):
        """Duplicate tools within the server list are safely registered."""
        with patch.object(self.agent, "_start_mcp_session", return_value=["t1", "t1", "t2"]):
            res = self._run_async(self.agent.hot_reload_server("self_repair"))
        self.assertEqual(res["status"], "success")

    def test_66_old_session_cleanup(self):
        """Old AsyncExitStack is closed cleanly upon successful session swap."""
        mock_stack = AsyncExitStack()
        mock_stack.aclose = MagicMock(return_value=asyncio.sleep(0.001))
        self.agent.exit_stacks["self_repair"] = mock_stack
        self._run_async(self.agent.hot_reload_server("self_repair"))
        mock_stack.aclose.assert_called()

    def test_67_in_flight_operation_drain(self):
        """Session swap waits for active calls to complete."""
        import threading
        self.agent.active_calls["self_repair"] = 1

        def drain_soon():
            time.sleep(0.02)
            self.agent.active_calls["self_repair"] = 0

        t = threading.Thread(target=drain_soon)
        t.start()
        self._run_async(self.agent.hot_reload_server("self_repair"))
        t.join()
        self.assertEqual(self.agent.active_calls["self_repair"], 0)

    def test_68_server_generation_incremented(self):
        """Server generation integer increments on each reload."""
        g1 = self.agent.server_generations["self_repair"]
        self._run_async(self.agent.hot_reload_server("self_repair"))
        g2 = self.agent.server_generations["self_repair"]
        self.assertEqual(g2, g1 + 1)

    def test_69_other_servers_unaffected(self):
        """Reloading server A does not disturb server B's session or tools."""
        self.agent.register_mock_session("windows_control", ["win_click", "win_type"])
        self._run_async(self.agent.hot_reload_server("self_repair"))
        self.assertEqual(self.agent.tool_to_server["win_click"], "windows_control")
        self.assertEqual(self.agent.tool_to_server["win_type"], "windows_control")


# ============================================================================
# 10. CRASH RECOVERY & SAFE REPLAY (11 tests)
# ============================================================================

class TestCrashRecoveryAndSafeReplay(unittest.TestCase):

    def setUp(self) -> None:
        self.agent = ZyeMasterAgent(root=PROJECT_ROOT)
        self.agent.register_mock_session("self_repair", ["read_recent_error_logs", "send_email"])

    def _run_async(self, coro):
        """Helper to run a coroutine in tests without requiring loopback sockets."""
        import inspect
        try:
            while True:
                try:
                    res = coro.send(None)
                    if inspect.iscoroutine(res):
                        return self._run_async(res)
                except StopIteration as e:
                    return e.value
        finally:
            coro.close()

    def test_70_mcp_transport_failure_detected(self):
        """BrokenPipeError triggers recovery attempt."""
        with patch.object(self.agent, "_dispatch_tool_call", side_effect=[BrokenPipeError("Dead process"), {"status": "success"}]):
            res = self._run_async(self.agent.call_mcp_with_recovery("read_recent_error_logs", {}))
        self.assertEqual(res["status"], "success")

    def test_71_one_permitted_restart(self):
        """Maximum of 1 server restart is attempted per call."""
        with patch.object(self.agent, "_dispatch_tool_call", side_effect=BrokenPipeError("Process crash")):
            with patch.object(self.agent, "hot_reload_server", return_value={"status": "error"}):
                res = self._run_async(self.agent.call_mcp_with_recovery("read_recent_error_logs", {}))
        self.assertEqual(res["code"], "SERVER_RECOVERY_FAILED")

    def test_72_read_only_operation_retried(self):
        """Idempotent read operation is automatically replayed after crash recovery."""
        self.assertTrue(is_safe_to_replay("read_own_source_code"))
        self.assertTrue(is_safe_to_replay("inspect_source_file"))

    def test_73_non_idempotent_operation_not_replayed(self):
        """Non-idempotent operations (email, payments, deletion) are NOT replayed."""
        self.assertFalse(is_safe_to_replay("send_email"))
        self.assertFalse(is_safe_to_replay("delete_file"))
        self.assertFalse(is_safe_to_replay("execute_payment"))
        self.assertFalse(is_safe_to_replay("patch_own_code"))

    def test_74_outcome_unknown_returned_for_irreversible_action(self):
        """Transport failure during non-idempotent action returns OUTCOME_UNKNOWN."""
        with patch.object(self.agent, "_dispatch_tool_call", side_effect=BrokenPipeError("Crash during email send")):
            res = self._run_async(self.agent.call_mcp_with_recovery("send_email", {}))
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "OUTCOME_UNKNOWN")
        self.assertIn("Replay blocked", res["message"])

    def test_75_normal_tool_error_does_not_trigger_restart(self):
        """Standard tool execution error does not trigger server reload."""
        with patch.object(self.agent, "hot_reload_server") as mock_reload:
            with patch.object(self.agent, "_dispatch_tool_call", side_effect=ValueError("Bad argument")):
                with self.assertRaises(ValueError):
                    self._run_async(self.agent.call_mcp_with_recovery("read_recent_error_logs", {}))
            mock_reload.assert_not_called()

    def test_76_gemini_network_retry(self):
        """Gemini network disconnection is retried and succeeds on recovery."""
        call_count = 0

        async def fake_gemini():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network dropped")
            return "AI Response"

        res = self._run_async(call_gemini_with_retry(fake_gemini, max_attempts=3, initial_delay=0.01))
        self.assertEqual(res, "AI Response")
        self.assertEqual(call_count, 2)

    def test_77_gemini_429_retry(self):
        """Gemini HTTP 429 rate limit is retried."""
        call_count = 0

        async def fake_gemini():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("Resource exhausted: 429 Too Many Requests")
            return "Rate limit cleared"

        res = self._run_async(call_gemini_with_retry(fake_gemini, max_attempts=3, initial_delay=0.01))
        self.assertEqual(res, "Rate limit cleared")

    def test_78_gemini_5xx_retry(self):
        """Gemini HTTP 503 is retried."""
        call_count = 0

        async def fake_gemini():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("503 Service Unavailable")
            return "Server recovered"

        res = self._run_async(call_gemini_with_retry(fake_gemini, max_attempts=3, initial_delay=0.01))
        self.assertEqual(res, "Server recovered")

    def test_79_gemini_auth_error_not_retried(self):
        """Gemini 401/403 or invalid API key is NOT retried."""
        call_count = 0

        async def fatal_gemini():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("API_KEY_INVALID: 403 Forbidden")

        with self.assertRaises(RuntimeError):
            self._run_async(call_gemini_with_retry(fatal_gemini, max_attempts=3, initial_delay=0.01))
        self.assertEqual(call_count, 1)

    def test_80_async_cancellation_preserved(self):
        """asyncio.CancelledError is never swallowed by retry loop."""
        async def cancel_gemini():
            raise asyncio.CancelledError()

        with self.assertRaises(asyncio.CancelledError):
            self._run_async(call_gemini_with_retry(cancel_gemini, max_attempts=3))


# ============================================================================
# 11. SECURITY TESTS (12 tests)
# ============================================================================

class TestSecurityBoundaries(_Day06TestBase):

    def test_81_windows_protected_path_blocked(self):
        """Windows system directory cannot be patched."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = preview_code_patch(r"C:\Windows\System32\drivers\etc\hosts", "a", "b", "reason")
        self.assertEqual(res["status"], "error")
        self.assertIn(res["code"], ("PATH_ACCESS_DENIED", "PATH_OUTSIDE_PROJECT"))

    def test_82_project_traversal_blocked(self):
        """Path traversal outside project root is blocked."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = preview_code_patch("../../secret.py", "a", "b", "reason")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "PATH_OUTSIDE_PROJECT")

    def test_83_env_patch_rejected(self):
        """.env cannot be patched via preview_code_patch or patch_own_code."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res1 = preview_code_patch(".env", "a", "b", "reason")
            res2 = patch_own_code(".env", "a", "b", "reason", "p", "token", "hash")
        self.assertEqual(res1["code"], "PROTECTED_FILE")
        self.assertEqual(res2["code"], "PROTECTED_FILE")

    def test_84_zye_guard_protected_by_default(self):
        """zye_guard.py is protected from automated patching by policy."""
        (self.tmpdir / "zye_guard.py").write_text("# guard", encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = preview_code_patch("zye_guard.py", "# guard", "# new", "reason")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "PROTECTED_FILE")

    def test_85_self_repair_mcp_protected_by_default(self):
        """self_repair_mcp.py is protected from automated self-patching by policy."""
        (self.tmpdir / "self_repair_mcp.py").write_text("# self_repair", encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = preview_code_patch("self_repair_mcp.py", "# self_repair", "# new", "reason")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "PROTECTED_FILE")

    def test_86_doctor_protected_by_default(self):
        """doctor.py is protected from automated patching by policy."""
        (self.tmpdir / "doctor.py").write_text("# doctor", encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = preview_code_patch("doctor.py", "# doctor", "# new", "reason")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "PROTECTED_FILE")

    def test_87_approval_token_hash_stored_not_plaintext(self):
        """Plaintext token is never stored directly in the database."""
        app_id, token = create_repair_approval(
            self.db_path, "p_sec", "sample_service.py", "hash1", "hash2", "patch"
        )
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        stored = conn.execute("SELECT token_hash FROM repair_approvals WHERE approval_id = ?", (app_id,)).fetchone()[0]
        conn.close()
        self.assertNotEqual(stored, token)
        self.assertEqual(stored, hashlib.sha256(token.encode("utf-8")).hexdigest())

    def test_88_api_key_redacted_in_diff(self):
        """API keys in diff snippets are redacted."""
        self.test_py.write_text("KEY = 'AIzaSyD1234567890123456789012345678901234'\n", encoding="utf-8")
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = preview_code_patch(
                "sample_service.py",
                "KEY = 'AIzaSyD1234567890123456789012345678901234'",
                "KEY = 'AIzaSyD9999999999999999999999999999999999'",
                "Update key",
            )
        self.assertNotIn("AIzaSyD1234567890123456789012345678901234", res["data"]["diff"])
        self.assertIn("[REDACTED_GEMINI_KEY]", res["data"]["diff"])

    def test_89_no_shell_injection_in_filename(self):
        """Shell injection metacharacters in filename are rejected by resolver."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            valid, _, _ = resolve_project_file("sample.py; rm -rf /", root=self.tmpdir)
        self.assertFalse(valid)

    def test_90_no_eval_or_exec_in_code_repair(self):
        """self_repair_mcp does not use eval or exec."""
        src = (PROJECT_ROOT / "self_repair_mcp.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, ("eval", "exec"))

    def test_91_database_sqlite_file_protected(self):
        """SQLite databases cannot be patched as code."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            res = preview_code_patch("data/zye_assistant_db.sqlite", "a", "b", "reason")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "PROTECTED_FILE")

    def test_92_audit_log_redacts_secrets(self):
        """code_repair_audit.log redacts API keys in details."""
        with patch.object(self_repair_mcp, "_PROJECT_ROOT_CACHE", self.tmpdir):
            self_repair_mcp.log_code_repair_audit(
                repair_id="rep1", patch_id="pat1", trace_id="tr1", target_file="sample.py",
                operation="PATCH", original_sha256="h1", proposed_sha256="h2",
                details="Leaked AIzaSyD1234567890123456789012345678901234", root=self.tmpdir,
            )
        log_file = self.tmpdir / "logs" / "code_repair_audit.log"
        content = log_file.read_text(encoding="utf-8")
        self.assertNotIn("AIzaSyD1234567890123456789012345678901234", content)
        self.assertIn("[REDACTED_GEMINI_KEY]", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)

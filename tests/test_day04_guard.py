#!/usr/bin/env python3
"""
ZYE AI — Day 04 Guard Engine Test Suite
=========================================

66 automated unit tests covering:

  - Decorator basics (10)
  - File validation (6)
  - Path security (15)
  - Retry engine (14)
  - Error telemetry (10)
  - Structured errors (6)
  - MCP compatibility (5)

Usage::

    python -m unittest tests.test_day04_guard -v
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure the project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import zye_guard
from zye_guard import (
    zye_safe_skill,
    get_project_root,
    resolve_safe_path,
    validate_safe_path,
    validate_required_path,
    validate_allowed_root,
    validate_path_components,
    is_path_within_root,
    is_protected_windows_path,
    validate_function_arguments,
    build_error_response,
    GuardErrorResponse,
    PathValidationResult,
    redact_secrets,
    log_bug_traceback,
    log_security_alert,
    _reset_project_root_cache,
    _reset_guard_logger,
)


class _GuardTestBase(unittest.TestCase):
    """Common setup/teardown for guard tests."""

    def setUp(self):
        _reset_project_root_cache()
        _reset_guard_logger()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmpdir.name)
        # Create a fake project root with zye_config.toml
        (self.tmpdir / "zye_config.toml").write_text("[system]\nassistant_name = 'Zye'\n")
        (self.tmpdir / "logs").mkdir()
        (self.tmpdir / "data").mkdir()

    def tearDown(self):
        _reset_guard_logger()
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
                        self._run_async(res)
                except StopIteration as e:
                    return e.value
        finally:
            coro.close()


# ============================================================================
# 1. DECORATOR BASICS (10 tests)
# ============================================================================

class TestDecoratorBasics(_GuardTestBase):
    """Test that @zye_safe_skill preserves function metadata and handles sync/async."""

    def test_01_sync_function_executes(self):
        """Sync decorated function returns expected value."""
        @zye_safe_skill()
        def greet(name: str) -> str:
            return f"Hello, {name}"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = greet("Zye")
        self.assertEqual(result, "Hello, Zye")

    def test_02_async_function_executes(self):
        """Async decorated function returns expected value."""
        @zye_safe_skill()
        async def greet_async(name: str) -> str:
            return f"Hello, {name}"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = self._run_async(greet_async("Zye"))
        self.assertEqual(result, "Hello, Zye")

    def test_03_preserves_function_name(self):
        """functools.wraps preserves __name__."""
        @zye_safe_skill()
        def my_skill():
            pass
        self.assertEqual(my_skill.__name__, "my_skill")

    def test_04_preserves_docstring(self):
        """functools.wraps preserves __doc__."""
        @zye_safe_skill()
        def my_skill():
            """My doc."""
            pass
        self.assertEqual(my_skill.__doc__, "My doc.")

    def test_05_preserves_module(self):
        """functools.wraps preserves __module__."""
        @zye_safe_skill()
        def my_skill():
            pass
        self.assertEqual(my_skill.__module__, __name__)

    def test_06_preserves_wrapped(self):
        """functools.wraps sets __wrapped__."""
        def original():
            pass
        decorated = zye_safe_skill()(original)
        self.assertIs(decorated.__wrapped__, original)

    def test_07_non_callable_raises_type_error(self):
        """Decorating a non-callable raises TypeError."""
        with self.assertRaises(TypeError):
            zye_safe_skill()(42)

    def test_08_default_retry_safe_is_false(self):
        """Default retry_safe is False — no retries on error."""
        call_count = 0

        @zye_safe_skill()
        def fail_once():
            nonlocal call_count
            call_count += 1
            raise ValueError("boom")

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = fail_once()
        self.assertEqual(call_count, 1)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "error")

    def test_09_returns_value_not_dict_on_success(self):
        """Successful execution returns the original return value, not a dict."""
        @zye_safe_skill()
        def add(a: int, b: int) -> int:
            return a + b

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = add(2, 3)
        self.assertEqual(result, 5)

    def test_10_handles_no_arguments(self):
        """Decorated function with no arguments works."""
        @zye_safe_skill()
        def get_version() -> str:
            return "1.0"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = get_version()
        self.assertEqual(result, "1.0")


# ============================================================================
# 2. FILE VALIDATION (6 tests)
# ============================================================================

class TestFileValidation(_GuardTestBase):
    """Test require_files parameter validation."""

    def test_11_required_file_exists(self):
        """Passes when required file exists."""
        (self.tmpdir / "config.txt").write_text("x")

        @zye_safe_skill(require_files=["config.txt"])
        def read_config():
            return "ok"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = read_config()
        self.assertEqual(result, "ok")

    def test_12_required_file_missing(self):
        """Returns error when required file is missing."""
        @zye_safe_skill(require_files=["missing.txt"])
        def read_config():
            return "ok"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = read_config()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["code"], "REQUIRED_FILE_MISSING")

    def test_13_multiple_required_files_all_exist(self):
        """Passes when all required files exist."""
        (self.tmpdir / "a.txt").write_text("a")
        (self.tmpdir / "b.txt").write_text("b")

        @zye_safe_skill(require_files=["a.txt", "b.txt"])
        def read_all():
            return "ok"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = read_all()
        self.assertEqual(result, "ok")

    def test_14_multiple_required_files_one_missing(self):
        """Returns error when any required file is missing."""
        (self.tmpdir / "a.txt").write_text("a")

        @zye_safe_skill(require_files=["a.txt", "not_here.txt"])
        def read_all():
            return "ok"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = read_all()
        self.assertEqual(result["code"], "REQUIRED_FILE_MISSING")

    def test_15_required_file_with_subdirectory(self):
        """Supports subdirectory paths in require_files."""
        sub = self.tmpdir / "data"
        sub.mkdir(exist_ok=True)
        (sub / "db.sqlite").write_text("db")

        @zye_safe_skill(require_files=["data/db.sqlite"])
        def use_db():
            return "connected"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = use_db()
        self.assertEqual(result, "connected")

    def test_16_async_required_file_missing(self):
        """Async function returns error when required file is missing."""
        @zye_safe_skill(require_files=["nope.txt"])
        async def read_async():
            return "ok"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = self._run_async(read_async())
        self.assertEqual(result["code"], "REQUIRED_FILE_MISSING")


# ============================================================================
# 3. PATH SECURITY (15 tests)
# ============================================================================

class TestPathSecurity(_GuardTestBase):
    """Test path validation, traversal protection, and Windows path security."""

    def test_17_valid_relative_path(self):
        """Relative path inside root is valid."""
        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = resolve_safe_path("data/test.txt", self.tmpdir)
        self.assertTrue(result.valid)

    def test_18_traversal_blocked(self):
        """Path with .. that escapes root is blocked."""
        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = resolve_safe_path("../../etc/passwd", self.tmpdir)
        self.assertFalse(result.valid)
        self.assertIn("escapes project root", result.violation)

    def test_19_null_byte_blocked(self):
        """Path with null byte is blocked."""
        result = validate_path_components("file\x00.txt")
        self.assertFalse(result.valid)
        self.assertIn("null byte", result.violation)

    def test_20_unc_path_blocked(self):
        """UNC paths are blocked."""
        result = validate_path_components("\\\\server\\share\\file.txt")
        self.assertFalse(result.valid)
        self.assertIn("UNC", result.violation)

    def test_21_device_path_blocked(self):
        """Device paths (\\\\?\\) are blocked."""
        result = validate_path_components("\\\\?\\C:\\Windows\\system.ini")
        self.assertFalse(result.valid)

    def test_22_alternate_data_stream_blocked(self):
        """NTFS Alternate Data Stream in filename is blocked."""
        result = validate_path_components("file.txt:hidden_stream")
        self.assertFalse(result.valid)
        self.assertIn("Alternate Data Stream", result.violation)

    def test_23_reserved_name_con_blocked(self):
        """Reserved device name CON is blocked."""
        result = validate_path_components("CON")
        self.assertFalse(result.valid)
        self.assertIn("Reserved device name", result.violation)

    def test_24_reserved_name_lpt1_blocked(self):
        """Reserved device name LPT1 is blocked."""
        result = validate_path_components("LPT1.txt")
        self.assertFalse(result.valid)

    def test_25_reserved_name_nul_blocked(self):
        """Reserved device name NUL is blocked."""
        result = validate_path_components("NUL")
        self.assertFalse(result.valid)

    def test_26_normal_filename_passes(self):
        """Normal filename passes all component checks."""
        result = validate_path_components("data/my_file.txt")
        self.assertTrue(result.valid)

    def test_27_drive_letter_colon_allowed(self):
        """Drive letter colon (C:) is not flagged as ADS."""
        result = validate_path_components("C:\\Users\\test.txt")
        self.assertTrue(result.valid)

    def test_28_is_path_within_root_true(self):
        """is_path_within_root returns True for contained path."""
        child = self.tmpdir / "data" / "file.txt"
        self.assertTrue(is_path_within_root(child, self.tmpdir))

    def test_29_is_path_within_root_false(self):
        """is_path_within_root returns False for external path."""
        external = Path(tempfile.gettempdir()) / "other_project" / "file.txt"
        self.assertFalse(is_path_within_root(external, self.tmpdir))

    def test_30_protected_windows_path_detected(self):
        """is_protected_windows_path detects C:\\Windows."""
        windir = os.environ.get("WINDIR", r"C:\Windows")
        target = Path(windir) / "System32" / "test.dll"
        self.assertTrue(is_protected_windows_path(target))

    def test_31_project_path_not_protected(self):
        """Project path is not flagged as protected."""
        target = self.tmpdir / "data" / "test.txt"
        self.assertFalse(is_protected_windows_path(target))


# ============================================================================
# 3b. PATH PARAM VALIDATION IN DECORATOR (continued path security)
# ============================================================================

class TestPathParamValidation(_GuardTestBase):
    """Test path_params and allowed_roots in the decorator."""

    def test_32_path_param_inside_root(self):
        """path_params validation passes for safe path."""
        (self.tmpdir / "data" / "input.txt").write_text("hello")

        @zye_safe_skill(path_params=["filepath"])
        def read_file(filepath: str) -> str:
            return "read"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = read_file("data/input.txt")
        self.assertEqual(result, "read")

    def test_33_path_param_traversal_blocked(self):
        """path_params blocks traversal paths."""
        @zye_safe_skill(path_params=["filepath"])
        def read_file(filepath: str) -> str:
            return "read"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = read_file("../../etc/shadow")
        self.assertEqual(result["code"], "PATH_SECURITY_VIOLATION")

    def test_34_allowed_roots_enforced(self):
        """allowed_roots restricts access to specific subdirectories."""
        (self.tmpdir / "logs" / "test.log").write_text("log")

        @zye_safe_skill(path_params=["filepath"], allowed_roots=["data"])
        def read_file(filepath: str) -> str:
            return "read"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = read_file("logs/test.log")
        self.assertEqual(result["code"], "PATH_SECURITY_VIOLATION")

    def test_35_allowed_roots_permits_valid(self):
        """allowed_roots allows access within permitted directory."""
        (self.tmpdir / "data" / "input.txt").write_text("x")

        @zye_safe_skill(path_params=["filepath"], allowed_roots=["data"])
        def read_file(filepath: str) -> str:
            return "ok"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = read_file("data/input.txt")
        self.assertEqual(result, "ok")

    def test_36_validate_allowed_root_function(self):
        """validate_allowed_root returns valid for path in allowed root."""
        (self.tmpdir / "data" / "file.txt").write_text("x")
        result = validate_allowed_root("data/file.txt", ["data"], self.tmpdir)
        self.assertTrue(result.valid)

    def test_37_validate_allowed_root_rejects(self):
        """validate_allowed_root returns invalid for path outside allowed root."""
        result = validate_allowed_root("logs/test.log", ["data"], self.tmpdir)
        self.assertFalse(result.valid)


# ============================================================================
# 4. RETRY ENGINE (14 tests)
# ============================================================================

class TestRetryEngine(_GuardTestBase):
    """Test retry behavior with retry_safe, backoff, and exception types."""

    def test_38_no_retry_by_default(self):
        """With retry_safe=False (default), function is called only once."""
        call_count = 0

        @zye_safe_skill()
        def fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = fail()
        self.assertEqual(call_count, 1)
        self.assertEqual(result["status"], "error")

    def test_39_retry_on_connection_error(self):
        """retry_safe=True retries on ConnectionError."""
        call_count = 0

        @zye_safe_skill(retry_safe=True, max_retries=2, retry_base_delay=0.01)
        def fail():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("network down")

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = fail()
        self.assertEqual(call_count, 3)  # 1 initial + 2 retries

    def test_40_retry_on_timeout_error(self):
        """retry_safe=True retries on TimeoutError."""
        call_count = 0

        @zye_safe_skill(retry_safe=True, max_retries=1, retry_base_delay=0.01)
        def fail():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("timed out")

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = fail()
        self.assertEqual(call_count, 2)

    def test_41_no_retry_on_value_error(self):
        """ValueError is not retried even with retry_safe=True."""
        call_count = 0

        @zye_safe_skill(retry_safe=True, max_retries=3, retry_base_delay=0.01)
        def fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("bad value")

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = fail()
        self.assertEqual(call_count, 1)

    def test_42_custom_retryable_exceptions(self):
        """Custom retryable_exceptions tuple is honored."""
        call_count = 0

        @zye_safe_skill(
            retry_safe=True,
            max_retries=2,
            retry_base_delay=0.01,
            retryable_exceptions=(ValueError,),
        )
        def fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("now retryable")

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = fail()
        self.assertEqual(call_count, 3)

    def test_43_retry_succeeds_on_second_try(self):
        """Function that succeeds on retry returns the value."""
        call_count = 0

        @zye_safe_skill(retry_safe=True, max_retries=3, retry_base_delay=0.01)
        def sometimes_fail():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("transient")
            return "success"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = sometimes_fail()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 2)

    def test_44_retry_response_includes_attempt(self):
        """Error response after retries includes attempt count."""
        @zye_safe_skill(retry_safe=True, max_retries=2, retry_base_delay=0.01)
        def fail():
            raise ConnectionError("fail")

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = fail()
        self.assertEqual(result["attempt"], 2)
        self.assertEqual(result["max_retries"], 2)
        self.assertTrue(result["retryable"])

    def test_45_exponential_backoff_delay(self):
        """Verify backoff delay calculation."""
        from zye_guard import _compute_delay
        self.assertAlmostEqual(_compute_delay(0, 0.8, 30.0), 0.8)
        self.assertAlmostEqual(_compute_delay(1, 0.8, 30.0), 1.6)
        self.assertAlmostEqual(_compute_delay(2, 0.8, 30.0), 3.2)
        self.assertAlmostEqual(_compute_delay(5, 0.8, 30.0), 25.6)
        self.assertAlmostEqual(_compute_delay(6, 0.8, 30.0), 30.0)  # capped

    def test_46_async_retry_on_connection_error(self):
        """Async function retries on ConnectionError."""
        call_count = 0

        @zye_safe_skill(retry_safe=True, max_retries=2, retry_base_delay=0.01)
        async def fail():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("network down")

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = self._run_async(fail())
        self.assertEqual(call_count, 3)

    def test_47_async_cancelled_error_not_swallowed(self):
        """asyncio.CancelledError is re-raised, never swallowed."""
        @zye_safe_skill(retry_safe=True, max_retries=3)
        async def cancel_me():
            raise asyncio.CancelledError()

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            with self.assertRaises(asyncio.CancelledError):
                self._run_async(cancel_me())

    def test_48_async_retry_succeeds(self):
        """Async function that recovers on retry returns the value."""
        call_count = 0

        @zye_safe_skill(retry_safe=True, max_retries=3, retry_base_delay=0.01)
        async def sometimes_fail():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("transient")
            return "async_success"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = self._run_async(sometimes_fail())
        self.assertEqual(result, "async_success")

    def test_49_should_retry_logic(self):
        """_should_retry returns correct booleans."""
        from zye_guard import _should_retry, DEFAULT_RETRYABLE_EXCEPTIONS
        # retry_safe=False → always False
        self.assertFalse(_should_retry(ConnectionError(), False, DEFAULT_RETRYABLE_EXCEPTIONS, 0, 3))
        # retry_safe=True, retryable exception, within limit → True
        self.assertTrue(_should_retry(ConnectionError(), True, DEFAULT_RETRYABLE_EXCEPTIONS, 0, 3))
        # attempt >= max → False
        self.assertFalse(_should_retry(ConnectionError(), True, DEFAULT_RETRYABLE_EXCEPTIONS, 3, 3))
        # Non-retryable exception → False
        self.assertFalse(_should_retry(ValueError(), True, DEFAULT_RETRYABLE_EXCEPTIONS, 0, 3))

    def test_50_max_retries_zero(self):
        """retry_safe=True with max_retries=0 → no retries."""
        call_count = 0

        @zye_safe_skill(retry_safe=True, max_retries=0, retry_base_delay=0.01)
        def fail():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("fail")

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = fail()
        self.assertEqual(call_count, 1)

    def test_51_os_error_retried(self):
        """OSError is retried with retry_safe=True."""
        call_count = 0

        @zye_safe_skill(retry_safe=True, max_retries=1, retry_base_delay=0.01)
        def fail():
            nonlocal call_count
            call_count += 1
            raise OSError("disk error")

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = fail()
        self.assertEqual(call_count, 2)


# ============================================================================
# 5. ERROR TELEMETRY (10 tests)
# ============================================================================

class TestErrorTelemetry(_GuardTestBase):
    """Test traceback logging and security alert logging."""

    def test_52_error_logged_to_file(self):
        """Exceptions are logged to logs/zye_errors.log."""
        err_log = self.tmpdir / "logs" / "zye_errors.log"

        @zye_safe_skill()
        def fail():
            raise RuntimeError("test crash")

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            fail()

        # Force flush
        _reset_guard_logger()
        content = err_log.read_text(encoding="utf-8")
        self.assertIn("test crash", content)
        self.assertIn("guard_traceback", content)

    def test_53_trace_id_in_log(self):
        """Log entry contains a trace_id."""
        err_log = self.tmpdir / "logs" / "zye_errors.log"

        @zye_safe_skill()
        def fail():
            raise RuntimeError("traceid check")

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = fail()

        _reset_guard_logger()
        content = err_log.read_text(encoding="utf-8")
        self.assertIn("trace_id", content)

    def test_54_secret_redacted_in_log(self):
        """API keys in exceptions are redacted in logs."""
        err_log = self.tmpdir / "logs" / "zye_errors.log"

        @zye_safe_skill()
        def fail():
            raise RuntimeError("Key is AIzaSyD1234567890123456789012345678901234")

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            fail()

        _reset_guard_logger()
        content = err_log.read_text(encoding="utf-8")
        self.assertNotIn("AIzaSyD1234567890123456789012345678901234", content)
        self.assertIn("REDACTED_GEMINI_KEY", content)

    def test_55_log_bug_traceback_function(self):
        """log_bug_traceback writes directly."""
        err_log = self.tmpdir / "logs" / "zye_errors.log"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            try:
                raise ValueError("direct log test")
            except ValueError as exc:
                log_bug_traceback("test_func", "abc123", exc, attempt=0)

        _reset_guard_logger()
        content = err_log.read_text(encoding="utf-8")
        self.assertIn("direct log test", content)
        self.assertIn("abc123", content)

    def test_56_security_alert_logged(self):
        """Path violations are logged to zye_security_alerts.log."""
        alert_log = self.tmpdir / "logs" / "zye_security_alerts.log"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            log_security_alert("test_func", "sec123", "Path traversal detected")

        content = alert_log.read_text(encoding="utf-8")
        self.assertIn("Path traversal detected", content)
        self.assertIn("sec123", content)

    def test_57_security_alert_on_path_violation(self):
        """@zye_safe_skill logs security alert on path violation."""
        alert_log = self.tmpdir / "logs" / "zye_security_alerts.log"

        @zye_safe_skill(path_params=["filepath"])
        def read_file(filepath: str) -> str:
            return "read"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            read_file("../../etc/shadow")

        content = alert_log.read_text(encoding="utf-8")
        self.assertIn("security_violation", content)

    def test_58_error_response_has_trace_id(self):
        """Error response dict includes trace_id."""
        @zye_safe_skill()
        def fail():
            raise RuntimeError("boom")

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = fail()
        self.assertIn("trace_id", result)
        self.assertEqual(len(result["trace_id"]), 12)

    def test_59_multiple_errors_logged_sequentially(self):
        """Multiple errors accumulate in the log file."""
        err_log = self.tmpdir / "logs" / "zye_errors.log"

        @zye_safe_skill()
        def fail_a():
            raise RuntimeError("error_alpha")

        @zye_safe_skill()
        def fail_b():
            raise RuntimeError("error_beta")

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            fail_a()
            fail_b()

        _reset_guard_logger()
        content = err_log.read_text(encoding="utf-8")
        self.assertIn("error_alpha", content)
        self.assertIn("error_beta", content)

    def test_60_redact_secrets_function(self):
        """redact_secrets removes various key patterns."""
        text = "My key is AIzaSyD1234567890123456789012345678901234 and sk-proj-abc123def456ghi789"
        result = redact_secrets(text)
        self.assertNotIn("AIzaSyD", result)
        self.assertIn("REDACTED_GEMINI_KEY", result)
        self.assertIn("REDACTED_API_KEY", result)

    def test_61_redact_key_value_pattern(self):
        """redact_secrets handles key=value patterns."""
        text = "api_key=super_secret_123"
        result = redact_secrets(text)
        self.assertIn("REDACTED", result)
        self.assertNotIn("super_secret_123", result)


# ============================================================================
# 6. STRUCTURED ERRORS (6 tests)
# ============================================================================

class TestStructuredErrors(_GuardTestBase):
    """Test GuardErrorResponse and build_error_response."""

    def test_62_error_response_structure(self):
        """build_error_response returns all required fields."""
        resp = build_error_response("TEST_CODE", "Test reason")
        self.assertEqual(resp["status"], "error")
        self.assertEqual(resp["code"], "TEST_CODE")
        self.assertEqual(resp["reason"], "Test reason")
        self.assertIn("trace_id", resp)
        self.assertIn("retryable", resp)
        self.assertFalse(resp["retryable"])

    def test_63_error_response_custom_fields(self):
        """build_error_response includes custom fields."""
        resp = build_error_response(
            "CUSTOM", "detail",
            next_step="retry later",
            retryable=True,
            attempt=2,
            max_retries=3,
        )
        self.assertEqual(resp["next_step"], "retry later")
        self.assertTrue(resp["retryable"])
        self.assertEqual(resp["attempt"], 2)
        self.assertEqual(resp["max_retries"], 3)

    def test_64_guard_error_response_to_json(self):
        """GuardErrorResponse.to_json() returns valid JSON."""
        err = GuardErrorResponse(code="JSON_TEST", reason="json test")
        parsed = json.loads(err.to_json())
        self.assertEqual(parsed["code"], "JSON_TEST")

    def test_65_guard_error_response_to_dict(self):
        """GuardErrorResponse.to_dict() returns a dict."""
        err = GuardErrorResponse(code="DICT_TEST", reason="dict test")
        d = err.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["code"], "DICT_TEST")

    def test_66_invalid_arguments_response(self):
        """Missing required argument returns INVALID_ARGUMENTS error."""
        @zye_safe_skill()
        def need_name(name: str) -> str:
            return name

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = need_name()  # missing 'name'
        self.assertEqual(result["code"], "INVALID_ARGUMENTS")

    def test_67_execution_error_response(self):
        """Unhandled exception returns EXECUTION_ERROR code."""
        @zye_safe_skill()
        def crash():
            raise TypeError("unexpected type")

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = crash()
        self.assertEqual(result["code"], "EXECUTION_ERROR")
        self.assertIn("unexpected type", result["reason"])


# ============================================================================
# 7. MCP COMPATIBILITY (5 tests)
# ============================================================================

class TestMCPCompatibility(_GuardTestBase):
    """Test that @zye_safe_skill is compatible with MCP FastMCP stacking."""

    def test_68_signature_preserved_for_introspection(self):
        """inspect.signature works on the decorated function (MCP requirement)."""
        @zye_safe_skill()
        def create_file(path: str, content: str = "") -> dict:
            return {"status": "ok"}

        sig = inspect.signature(create_file)
        params = list(sig.parameters.keys())
        self.assertIn("path", params)
        self.assertIn("content", params)

    def test_69_stacked_decorators(self):
        """@zye_safe_skill works when stacked with another decorator."""
        def custom_decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper

        @custom_decorator
        @zye_safe_skill()
        def my_tool(name: str) -> str:
            return f"tool: {name}"

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = my_tool("test")
        self.assertEqual(result, "tool: test")

    def test_70_works_without_mcp_installed(self):
        """Module works even if mcp package is not installed."""
        # Simply verify the import worked (no mcp in this venv)
        self.assertTrue(callable(zye_safe_skill))

    def test_71_dict_return_for_error(self):
        """Errors return dicts (JSON-serializable for MCP)."""
        @zye_safe_skill()
        def fail():
            raise RuntimeError("mcp error test")

        with patch.object(zye_guard, '_PROJECT_ROOT_CACHE', self.tmpdir):
            result = fail()
        # Must be JSON-serializable
        serialized = json.dumps(result)
        self.assertIsInstance(json.loads(serialized), dict)

    def test_72_annotations_preserved(self):
        """Return type annotations are preserved for MCP schema generation."""
        @zye_safe_skill()
        def typed_func(x: int) -> dict[str, str]:
            return {"result": str(x)}

        # __wrapped__ should retain annotations
        self.assertIn("return", typed_func.__wrapped__.__annotations__)


# Need functools for stacked decorator test
import functools


# ============================================================================
# Runner
# ============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)

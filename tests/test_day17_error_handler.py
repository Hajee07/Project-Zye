"""
Unit tests for Error Handling & Taxonomy Engine (Day 17).
Verifies exception hierarchy, classification routines, secret redaction,
Tanglish user-friendly translations, and structured error envelopes.
"""

from __future__ import annotations

import unittest

from zye_reliability.error_handler import (
    AccessDeniedError,
    CircuitOpenError,
    InputValidationError,
    ProcessNotFoundError,
    ProtectedProcessError,
    ZyeError,
    ZyeErrorCode,
    ZyeTimeoutError,
    build_zye_error_response,
    classify_exception,
    format_user_friendly_error,
    redact_error_details,
)


class TestDay17ErrorHandler(unittest.TestCase):

    def test_zye_error_hierarchy(self) -> None:
        """Verify derived exceptions inherit from ZyeError and carry proper codes."""
        err1 = ProcessNotFoundError("PID 500 missing")
        self.assertIsInstance(err1, ZyeError)
        self.assertEqual(err1.code, ZyeErrorCode.PROCESS_NOT_FOUND)

        err2 = AccessDeniedError("No permission")
        self.assertEqual(err2.code, ZyeErrorCode.ACCESS_DENIED)

        err3 = ProtectedProcessError("csrss cannot be killed")
        self.assertEqual(err3.code, ZyeErrorCode.PROTECTED_PROCESS)

        err4 = ZyeTimeoutError("Operation timed out")
        self.assertEqual(err4.code, ZyeErrorCode.TIMEOUT)
        self.assertTrue(err4.retryable)

        err5 = CircuitOpenError("Circuit is OPEN")
        self.assertEqual(err5.code, ZyeErrorCode.CIRCUIT_OPEN)

        err6 = InputValidationError("Bad parameter")
        self.assertEqual(err6.code, ZyeErrorCode.VALIDATION_FAILED)

    def test_to_response_structure(self) -> None:
        """Verify converting ZyeError to response dictionary produces valid envelope."""
        err = ProcessNotFoundError("Target process vanished")
        resp = err.to_response()
        self.assertEqual(resp.status, "error")
        self.assertEqual(resp.code, "PROCESS_NOT_FOUND")
        self.assertIn("process kedaikala", resp.tanglish_message.lower())
        self.assertTrue(len(resp.trace_id) >= 8)

    def test_classify_exception(self) -> None:
        """Verify exception classification mapping."""
        self.assertEqual(classify_exception(ValueError("bad")), ZyeErrorCode.INVALID_INPUT)
        self.assertEqual(classify_exception(TimeoutError("timed out")), ZyeErrorCode.TIMEOUT)
        self.assertEqual(classify_exception(PermissionError("denied")), ZyeErrorCode.ACCESS_DENIED)
        self.assertEqual(classify_exception(FileNotFoundError("missing")), ZyeErrorCode.RESOURCE_UNAVAILABLE)
        self.assertEqual(classify_exception(ConnectionError("dropped")), ZyeErrorCode.RESOURCE_UNAVAILABLE)
        self.assertEqual(classify_exception(RuntimeError("oops")), ZyeErrorCode.INTERNAL_ERROR)

    def test_redact_error_details(self) -> None:
        """Verify secrets and keys are scrubbed from error messages."""
        raw = "Failed with key AIzaSyA1234567890123456789012345678901 and auth token sk-abcdef1234567890abcdef"
        sanitized = redact_error_details(raw)
        self.assertNotIn("AIzaSy", sanitized)
        self.assertNotIn("sk-abc", sanitized)
        self.assertIn("[REDACTED_GEMINI_KEY]", sanitized)
        self.assertIn("[REDACTED_API_KEY]", sanitized)

    def test_build_zye_error_response_helper(self) -> None:
        """Verify functional error response constructor."""
        resp = build_zye_error_response(
            code=ZyeErrorCode.PROTECTED_PROCESS,
            message="Cannot terminate explorer.exe with secret AIzaSyA1234567890123456789012345678901",
            retryable=False,
            next_step="Leave system processes running.",
        )
        self.assertEqual(resp["status"], "error")
        self.assertEqual(resp["code"], "PROTECTED_PROCESS")
        self.assertNotIn("AIzaSy", resp["message"])
        self.assertIn("system process", resp["tanglish_message"].lower())
        self.assertEqual(resp["next_step"], "Leave system processes running.")

    def test_format_user_friendly_error(self) -> None:
        """Verify user-friendly voice formatting returns Tanglish message."""
        resp = build_zye_error_response(
            code=ZyeErrorCode.TIMEOUT,
            message="Timed out",
        )
        voice_str = format_user_friendly_error(resp)
        self.assertIn("timeout", voice_str.lower())


if __name__ == "__main__":
    unittest.main()

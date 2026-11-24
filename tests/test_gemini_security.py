"""
Unit tests for Gemini Security Policy — Credential protection, no hardcoded secrets, no quota evasion.
"""

import os
import unittest
from gemini_error_handler import GeminiErrorHandler
from gemini_key_manager import GeminiKeyManager, mask_credential
from gemini_project_router import GeminiProjectRouter


class TestGeminiSecurity(unittest.TestCase):
    def test_01_no_raw_keys_in_masked_output(self):
        sample_keys = [
            "AIzaSyExampleKey1234567890abcdefghijk",
            "AQ.Ab8RN6ExampleTestingSecretKey123456",
        ]
        for k in sample_keys:
            masked = mask_credential(k)
            self.assertNotIn("AIzaSy", masked)
            self.assertNotIn("AQ.Ab", masked)
            self.assertTrue(masked.startswith("************"))

    def test_02_error_sanitization_removes_secrets(self):
        eh = GeminiErrorHandler()
        leaked_key = "AQ.Ab8RN6KeyInAnErrorMessage12345"
        raw_error = f"Error during call: {leaked_key} was rejected by server"
        sanitized = eh.sanitize_message(raw_error)
        self.assertNotIn(leaked_key, sanitized)
        self.assertIn("[REDACTED_API_KEY]", sanitized)

    def test_03_no_cross_project_quota_fallback(self):
        km = GeminiKeyManager(db_path=":memory:", auto_load=False)
        router = GeminiProjectRouter(key_manager=km, db_path=":memory:", allow_cross_project_fallback=False)
        self.assertFalse(router.allow_cross_project_fallback)

    def test_04_database_key_metadata_never_stores_raw_keys(self):
        from gemini_db import get_db_connection, init_gemini_database
        init_gemini_database(":memory:")
        conn = get_db_connection(":memory:")
        cursor = conn.execute("PRAGMA table_info(gemini_key_metadata);")
        columns = [row["name"] for row in cursor.fetchall()]
        # Verify no 'api_key' or 'raw_key' column exists in metadata table
        self.assertNotIn("api_key", columns)
        self.assertNotIn("raw_key", columns)
        self.assertIn("masked_key", columns)
        conn.close()


if __name__ == "__main__":
    unittest.main()

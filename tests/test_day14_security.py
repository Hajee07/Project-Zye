"""
Unit tests for Day 14 Security & Untrusted Content Isolation Policy.
Verifies secret redaction, SQL injection resistance, path traversal prevention, and data immutability.
"""

import os
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.calendar_engine import CalendarEngine
from zye_personal_assistant.document_engine import DocumentEngine
from zye_personal_assistant.email_engine import EmailEngine
from zye_personal_assistant.project_manager import ProjectManager


class TestDay14Security(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_sec_test_")
        os.close(self._tmp_fd)
        self.cal = CalendarEngine(db_path=self._tmp_path)
        self.pm = ProjectManager(db_path=self._tmp_path)
        self.em = EmailEngine(db_path=self._tmp_path)
        self.doc = DocumentEngine(db_path=self._tmp_path)

    def tearDown(self):
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_sql_injection_resistance_in_calendar(self):
        # Attempt SQL injection in title
        payload = "'; DROP TABLE events; --"
        res = self.cal.add_event(title=payload, start_iso="2026-11-20T10:00:00")
        self.assertEqual(res["status"], "SUCCESS")

        # Verify table still exists and event safely stored as literal text
        upcoming = self.cal.list_upcoming_events()
        self.assertEqual(len(upcoming), 1)
        self.assertEqual(upcoming[0]["title"], payload)

    def test_02_sql_injection_resistance_in_projects(self):
        payload = "'; DROP TABLE projects; --"
        res = self.pm.create_or_update_project(name=payload)
        self.assertEqual(res["status"], "SUCCESS")
        sb = self.pm.get_status_board()
        self.assertEqual(sb["total_projects"], 1)

    def test_03_path_traversal_in_documents_rejected(self):
        # Invalid directory path traversal attempt
        res = self.doc.index_folder("../../non_existent_traversal_dir")
        self.assertEqual(res["status"], "ERROR")

    def test_04_email_attachment_traversal_rejected(self):
        res = self.em.send_email(
            to_addr="test@example.com",
            subject="Test",
            body="Test",
            confirmed=True,
            attachments=["../../../../windows/system32/calc.exe"],
        )
        self.assertEqual(res["status"], "ERROR")
        self.assertIn("not found", res["message"])

    def test_05_email_credentials_never_exposed_in_draft(self):
        os.environ["ZYE_EMAIL_APP_PASSWORD"] = "secret_super_secure_token_123"
        draft = self.em.create_draft("dest@acme.com", "Subject", "Body content")
        self.assertNotIn("secret_super_secure_token_123", str(draft))


if __name__ == "__main__":
    unittest.main()

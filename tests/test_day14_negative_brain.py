"""
Unit tests for Day 14 Safety Gateway & Day 13 Negative Pre-Mortem Brain Integration.
Verifies failure mode analysis, confirmation gates on protected actions, and audit persistence.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from zye_personal_assistant.database import get_db_connection
from zye_personal_assistant.safety_gateway import PROTECTED_ACTION_TYPES, SafetyGateway


class TestDay14NegativeBrain(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_nb_test_")
        os.close(self._tmp_fd)

    def tearDown(self):
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_non_protected_action_authorized_immediately(self):
        sg = SafetyGateway(db_path=self._tmp_path)
        res = sg.authorize_personal_assistant_action_sync(
            action_type="SEARCH_DOCUMENTS",
            task_description="Search local file index",
            proposed_steps=["query sqlite"],
            target_resources=["doc_index"],
        )
        self.assertTrue(res["authorized"])
        self.assertEqual(res["overall_failure_risk"], "LOW")
        self.assertFalse(res["requires_user_confirmation"])

    def test_02_protected_actions_require_confirmation(self):
        sg = SafetyGateway(db_path=self._tmp_path)
        for act in ("EMAIL_SEND", "CALENDAR_DELETE", "DOC_ORGANIZE", "TASK_BULK_TIMEBLOCK"):
            res = sg.authorize_personal_assistant_action_sync(
                action_type=act,
                task_description=f"Perform {act}",
                proposed_steps=["step 1"],
                target_resources=["res_1"],
            )
            self.assertTrue(res["requires_user_confirmation"], f"{act} must require confirmation")

    def test_03_audit_history_persisted_to_sqlite(self):
        sg = SafetyGateway(db_path=self._tmp_path)
        sg.authorize_personal_assistant_action_sync(
            action_type="EMAIL_SEND",
            task_description="Send financial report",
            proposed_steps=["dispatch"],
            target_resources=["email:finance@corp.com"],
        )
        conn = get_db_connection(self._tmp_path)
        try:
            row = conn.execute("SELECT action_type, premortem_risk, authorized FROM audit_history WHERE action_type = 'EMAIL_SEND';").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["action_type"], "EMAIL_SEND")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()

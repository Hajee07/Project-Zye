"""
Unit Tests for Zye Day 20 Office Session Manager.
Tests session metadata persistence, touch operations, lookup, and cleanup.
"""

import unittest
import pathlib
import tempfile
import os

from zye_office.session_manager import OfficeSessionManager
from zye_office.models import ConnectionPolicy, SessionStatus, OfficeSessionMetadata


class TestDay20SessionManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.meta_file = pathlib.Path(self.temp_dir.name) / "test_session_metadata.json"
        self.mgr = OfficeSessionManager(metadata_file=self.meta_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_empty_sessions_initially(self):
        self.assertEqual(len(self.mgr.list_sessions()), 0)
        self.assertIsNone(self.mgr.get_active_office_session())

    def test_session_metadata_persistence(self):
        session_id = "test_sess_001"
        meta = OfficeSessionMetadata(
            session_id=session_id,
            app_name="word",
            prog_id="Word.Application",
            connection_policy=ConnectionPolicy.ATTACH_EXISTING,
            session_status=SessionStatus.ACTIVE,
        )
        self.mgr._sessions[session_id] = meta
        self.mgr._app_to_session_id["word"] = session_id
        self.mgr._save_metadata_to_disk()

        # Reload in new manager instance
        new_mgr = OfficeSessionManager(metadata_file=self.meta_file)
        loaded = new_mgr.get_session("word")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.session_id, session_id)
        # On reload from disk, previous sessions are marked DISCONNECTED
        self.assertEqual(loaded.session_status, SessionStatus.DISCONNECTED)

    def test_touch_session(self):
        session_id = "test_sess_002"
        meta = OfficeSessionMetadata(
            session_id=session_id,
            app_name="excel",
            prog_id="Excel.Application",
            session_status=SessionStatus.ACTIVE,
        )
        self.mgr._sessions[session_id] = meta
        old_time = meta.last_accessed_at
        self.mgr.touch_session(session_id)
        self.assertIsNotNone(self.mgr.get_session(session_id))

    def test_get_session_by_id_and_by_app(self):
        meta = OfficeSessionMetadata(
            session_id="sess_ppt_123",
            app_name="powerpoint",
            prog_id="PowerPoint.Application",
            session_status=SessionStatus.ACTIVE,
        )
        self.mgr._sessions["sess_ppt_123"] = meta
        self.mgr._app_to_session_id["powerpoint"] = "sess_ppt_123"

        by_id = self.mgr.get_session("sess_ppt_123")
        by_app = self.mgr.get_session("powerpoint")
        self.assertEqual(by_id, by_app)


if __name__ == "__main__":
    unittest.main()

"""
Unit tests for Day 14 Information Research Engine.
Verifies multi-angle synthesis, depth handling, source citations, and uncertainty reporting.
"""

import os
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.database import get_db_connection
from zye_personal_assistant.research_engine import ResearchEngine


class TestDay14Research(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_res_test_")
        os.close(self._tmp_fd)
        self.engine = ResearchEngine(db_path=self._tmp_path)

    def tearDown(self):
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_conduct_research_executive_brief(self):
        res = self.engine.conduct_research("PostgreSQL vs DuckDB for Analytics", depth="EXECUTIVE_BRIEF")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["depth"], "EXECUTIVE_BRIEF")
        self.assertIn("executive_summary", res)
        self.assertGreater(len(res.get("key_findings", [])), 0)
        self.assertGreater(len(res.get("source_urls", [])), 0)
        self.assertIn("uncertainties", res)

    def test_02_empty_topic_rejected(self):
        res = self.engine.conduct_research("")
        self.assertEqual(res["status"], "ERROR")
        self.assertIn("cannot be empty", res["message"])

    def test_03_sqlite_persistence(self):
        self.engine.conduct_research("Microservices Failover Patterns")
        conn = get_db_connection(self._tmp_path)
        try:
            row = conn.execute("SELECT topic, summary FROM research_history WHERE topic = 'Microservices Failover Patterns';").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["topic"], "Microservices Failover Patterns")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()

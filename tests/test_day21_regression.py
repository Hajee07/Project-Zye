"""
Day 21 Unit Tests — Phase 2 Regression Audit & Backwards Compatibility.
Verifies Days 16 through 20 core subsystems remain intact and unimpacted by Day 21 Word enhancements.
"""

from __future__ import annotations

import unittest

from zye_office.app_registry import OfficeAppRegistry
from zye_office.com_worker import STACOMWorker
from zye_office.models.office_models import OfficeAppType, OfficeSessionMetadata
from zye_office.operation_registry import OfficeOperationRegistry
from zye_office.path_validator import OfficePathValidator
from zye_orchestrator.safety_pipeline import DEFAULT_TOOL_RISK_MAP, RiskLevel


class TestDay21Regression(unittest.TestCase):

    def test_day20_sta_worker_intact(self) -> None:
        """Verify Day 20 STA worker thread is operational."""
        worker = STACOMWorker.get_instance()
        self.assertTrue(worker.is_alive())
        self.assertEqual(worker.run(lambda: "ping"), "ping")

    def test_day20_office_app_registry_intact(self) -> None:
        """Verify Day 20 registry discovers the 4 primary Office applications."""
        reg = OfficeAppRegistry()
        apps = reg.get_registered_office_apps()
        self.assertEqual(len(apps), 4)
        app_names = [a.app_name for a in apps]
        self.assertIn("word", app_names)
        self.assertIn("excel", app_names)
        self.assertIn("powerpoint", app_names)
        self.assertIn("outlook", app_names)

    def test_day20_office_models_backwards_compatible(self) -> None:
        """Verify Day 20 models remain directly importable and instantiable."""
        meta = OfficeSessionMetadata(session_id="sess_123", app_name="word", prog_id="Word.Application")
        self.assertEqual(meta.session_id, "sess_123")
        self.assertEqual(meta.app_name, "word")

    def test_day20_operation_registry_intact(self) -> None:
        """Verify Day 20 operation registry still validates standard operations."""
        oreg = OfficeOperationRegistry()
        op = oreg.get_operation("word.insert_text")
        self.assertIsNotNone(op)

    def test_day20_path_validator_shield(self) -> None:
        """Verify Day 20 path validator still blocks traversal attacks."""
        from zye_office.errors import OfficeSecurityError
        pv = OfficePathValidator()
        safe = pv.validate_path("D:\\Zye\\data\\doc.docx", allowed_extensions=[".docx"])
        self.assertTrue(safe.endswith("doc.docx"))
        with self.assertRaises(OfficeSecurityError):
            pv.validate_path("..\\..\\malicious\\payload.exe", allowed_extensions=[".docx"])

    def test_safety_pipeline_risk_map_covers_day21(self) -> None:
        """Verify safety pipeline maps all key Day 21 operations with appropriate risk levels."""
        self.assertEqual(DEFAULT_TOOL_RISK_MAP["word_inspect_document"], RiskLevel.READ_ONLY)
        self.assertEqual(DEFAULT_TOOL_RISK_MAP["word_create_document"], RiskLevel.LOW_RISK)
        self.assertEqual(DEFAULT_TOOL_RISK_MAP["word_create_table"], RiskLevel.MEDIUM_RISK)
        self.assertEqual(DEFAULT_TOOL_RISK_MAP["word_accept_all_revisions"], RiskLevel.HIGH_RISK)
        self.assertEqual(DEFAULT_TOOL_RISK_MAP["word_run_vba_macro"], RiskLevel.CRITICAL_RISK)


if __name__ == "__main__":
    unittest.main()

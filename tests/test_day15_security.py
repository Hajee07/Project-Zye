"""Day 15 Unit Tests — Safety Execution Gateway & Cryptographic Approval Tokens."""
import time
import unittest

from zye_autonomy.audit_logger import AuditLogger
from zye_orchestrator.safety_pipeline import SafetyExecutionGateway, RiskLevel


class TestSafetyGatewayInit(unittest.TestCase):
    def test_creates_instance_no_args(self):
        sg = SafetyExecutionGateway()
        self.assertIsNotNone(sg)

    def test_creates_instance_with_audit_logger(self):
        sg = SafetyExecutionGateway(audit_logger=AuditLogger())
        self.assertIsNotNone(sg)


class TestRiskClassification(unittest.TestCase):
    def setUp(self):
        self.sg = SafetyExecutionGateway()

    def test_delete_file_is_critical(self):
        self.assertEqual(self.sg.classify_risk("delete_file"), RiskLevel.CRITICAL_RISK)

    def test_delete_directory_is_critical(self):
        self.assertEqual(self.sg.classify_risk("delete_directory"), RiskLevel.CRITICAL_RISK)

    def test_overwrite_file_is_critical(self):
        self.assertEqual(self.sg.classify_risk("overwrite_file"), RiskLevel.CRITICAL_RISK)

    def test_read_logs_is_read_only(self):
        self.assertEqual(self.sg.classify_risk("read_recent_error_logs"), RiskLevel.READ_ONLY)

    def test_get_system_info_is_read_only(self):
        self.assertEqual(self.sg.classify_risk("get_system_info"), RiskLevel.READ_ONLY)

    def test_manage_emails_is_high_risk(self):
        self.assertEqual(self.sg.classify_risk("manage_emails"), RiskLevel.HIGH_RISK)

    def test_patch_own_code_is_high_risk(self):
        self.assertEqual(self.sg.classify_risk("patch_own_code"), RiskLevel.HIGH_RISK)

    def test_set_mission_mode_is_medium(self):
        self.assertEqual(self.sg.classify_risk("set_mission_mode"), RiskLevel.MEDIUM_RISK)

    def test_unknown_tool_returns_a_risk_level(self):
        result = self.sg.classify_risk("completely_unknown_tool_xyz")
        self.assertIsInstance(result, RiskLevel)


class TestApprovalTokenLifecycle(unittest.TestCase):
    def setUp(self):
        self.sg = SafetyExecutionGateway()
        self.args = ["data/test_security.tmp"]
        self.params = {"file": "test_security.tmp"}

    def test_generate_token_returns_string(self):
        tok = self.sg.generate_approval_token("audit_01", "DELETE", self.args, self.params)
        self.assertIsInstance(tok, str)
        self.assertGreater(len(tok), 0)

    def test_token_has_prefix(self):
        tok = self.sg.generate_approval_token("audit_02", "DELETE", self.args, self.params)
        self.assertTrue(tok.startswith("tok_"))

    def test_unconfirmed_token_fails_validation(self):
        tok = self.sg.generate_approval_token("audit_03", "DELETE", self.args, self.params)
        ok, msg = self.sg.validate_approval_token(tok, "DELETE", self.args, self.params)
        self.assertFalse(ok)
        self.assertIn("not been confirmed", msg.lower() if msg else "")

    def test_confirmed_token_passes_validation(self):
        tok = self.sg.generate_approval_token("audit_04", "DELETE", self.args, self.params)
        self.sg.confirm_approval_token(tok)
        ok, msg = self.sg.validate_approval_token(tok, "DELETE", self.args, self.params)
        self.assertTrue(ok, f"Confirmed token should pass: {msg}")

    def test_fingerprint_mismatch_blocked(self):
        tok = self.sg.generate_approval_token("audit_05", "DELETE", self.args, self.params)
        self.sg.confirm_approval_token(tok)
        # Different args → different fingerprint
        ok, msg = self.sg.validate_approval_token(tok, "DELETE", ["other/file.txt"], {"file": "other.txt"})
        self.assertFalse(ok, "Token with mismatched fingerprint must NOT validate")

    def test_different_tokens_are_unique(self):
        tok1 = self.sg.generate_approval_token("audit_06a", "DELETE", self.args, self.params)
        tok2 = self.sg.generate_approval_token("audit_06b", "DELETE", self.args, self.params)
        self.assertNotEqual(tok1, tok2)


class TestRiskLevelEnum(unittest.TestCase):
    def test_all_five_levels_exist(self):
        expected = {
            "READ_ONLY", "LOW_RISK", "MEDIUM_RISK", "HIGH_RISK", "CRITICAL_RISK"
        }
        actual = {lvl.value for lvl in RiskLevel}
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()

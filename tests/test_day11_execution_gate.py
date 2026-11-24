"""Unit tests for Zye Day 11 Execution Authorization Gate."""

import asyncio
import time
import unittest
from unittest.mock import AsyncMock, MagicMock

from zye_autonomy.execution_gate import ZyeExecutionGate


class TestZyeExecutionGate(unittest.TestCase):
    def setUp(self):
        self.mock_pm = MagicMock()
        # Default mock pre-mortem returns medium risk, requires_user_confirmation=False
        self.mock_pm.run_audit = AsyncMock(return_value={
            "overall_failure_risk": "MEDIUM",
            "predicted_problems": [],
            "hidden_assumptions_broken": [],
            "corrected_hardened_steps": ["step 1"],
            "requires_user_confirmation": False,
            "confirmation_reason": "",
            "residual_risks": [],
            "missing_information": [],
            "preflight_summary": {},
            "recommended_execution_strategy": "Proceed",
            "audit_timestamp": "2026-11-19T12:00:00Z",
            "model_name": "mock",
        })
        self.mock_pf = MagicMock()
        self.mock_pf.generate_preflight_report.return_value = {"system_status": "READY"}
        self.mock_mc = MagicMock()
        self.mock_mc.get_current_mission.return_value = {"mission": "NORMAL_ASSISTANT"}

        self.gate = ZyeExecutionGate(
            premortem_brain=self.mock_pm,
            preflight=self.mock_pf,
            mission_controller=self.mock_mc,
            config={"approval_ttl_seconds": 1.0},
        )

    def test_01_read_only_tool_classification(self):
        cls = self.gate.classify_tool("get_current_mission")
        self.assertEqual(cls, "READ_ONLY")
        self.assertFalse(self.gate.requires_premortem("get_current_mission"))
        self.assertFalse(self.gate.requires_confirmation("get_current_mission"))

    def test_02_modifying_tool_classification(self):
        cls = self.gate.classify_tool("patch_own_code")
        self.assertEqual(cls, "MODIFYING")
        self.assertTrue(self.gate.requires_premortem("patch_own_code"))

    def test_03_destructive_tool_classification(self):
        cls = self.gate.classify_tool("delete_file")
        self.assertEqual(cls, "DESTRUCTIVE")
        self.assertTrue(self.gate.requires_premortem("delete_file"))
        self.assertTrue(self.gate.requires_confirmation("delete_file"))

    def test_04_privileged_tool_classification(self):
        cls = self.gate.classify_tool("execute_emergency_reflex")
        self.assertEqual(cls, "PRIVILEGED")
        self.assertTrue(self.gate.requires_confirmation("execute_emergency_reflex"))

    def test_05_read_only_tool_allowed_without_premortem(self):
        async def _run():
            res = await self.gate.evaluate("get_current_mission", {})
            self.assertTrue(res["allowed"])
            self.assertFalse(res["requires_confirmation"])
            self.mock_pm.run_audit.assert_not_called()
        asyncio.run(_run())

    def test_06_premortem_enforced_for_modifying_tool(self):
        async def _run():
            res = await self.gate.evaluate("edit_file", {"path": "a.txt"})
            self.assertTrue(res["allowed"])
            self.mock_pm.run_audit.assert_called_once()
        asyncio.run(_run())

    def test_07_destructive_tool_requires_confirmation(self):
        async def _run():
            res = await self.gate.evaluate("delete_file", {"path": "important.docx"})
            self.assertFalse(res["allowed"])
            self.assertTrue(res["requires_confirmation"])
            self.assertIsNotNone(res["approval_token"])
        asyncio.run(_run())

    def test_08_approval_token_grant_and_consume(self):
        async def _run():
            args = {"path": "archive.zip"}
            eval1 = await self.gate.evaluate("delete_file", args)
            token = eval1["approval_token"]
            self.assertIsNotNone(token)

            # Grant approval
            ok = self.gate.grant_approval(token)
            self.assertTrue(ok)

            # Re-evaluate with token
            eval2 = await self.gate.evaluate("delete_file", args, approval_token=token)
            self.assertTrue(eval2["allowed"])

            # Verify token is consumed
            self.assertFalse(self.gate.is_approval_valid(token, token))
        asyncio.run(_run())

    def test_09_approval_token_expired(self):
        gate = ZyeExecutionGate(
            premortem_brain=self.mock_pm,
            preflight=self.mock_pf,
            config={"approval_ttl_seconds": 0.05},
        )
        async def _run():
            args = {"path": "expired.tmp"}
            eval1 = await gate.evaluate("delete_file", args)
            token = eval1["approval_token"]
            gate.grant_approval(token)

            # Wait for TTL to expire
            await asyncio.sleep(0.06)

            eval2 = await gate.evaluate("delete_file", args, approval_token=token)
            self.assertFalse(eval2["allowed"])
        asyncio.run(_run())

    def test_10_argument_mismatch_invalidates_token(self):
        async def _run():
            args1 = {"path": "fileA.txt"}
            args2 = {"path": "fileB.txt"}  # Modified arguments!
            eval1 = await self.gate.evaluate("delete_file", args1)
            token1 = eval1["approval_token"]
            self.gate.grant_approval(token1)

            # Attempt to use token1 on args2
            eval2 = await self.gate.evaluate("delete_file", args2, approval_token=token1)
            self.assertFalse(eval2["allowed"])
        asyncio.run(_run())

    def test_11_critical_risk_blocks_execution(self):
        self.mock_pm.run_audit = AsyncMock(return_value={
            "overall_failure_risk": "CRITICAL",
            "predicted_problems": ["Data corruption imminent"],
            "hidden_assumptions_broken": [],
            "corrected_hardened_steps": [],
            "requires_user_confirmation": True,
            "confirmation_reason": "CRITICAL risk identified",
            "residual_risks": [],
            "missing_information": [],
            "preflight_summary": {},
            "recommended_execution_strategy": "Abort",
            "audit_timestamp": "2026-11-19T12:00:00Z",
            "model_name": "mock",
        })

        async def _run():
            res = await self.gate.evaluate("edit_file", {"path": "database.py"})
            self.assertFalse(res["allowed"])
            self.assertTrue(res["requires_confirmation"])
            self.assertIn("CRITICAL", res["reason"])
        asyncio.run(_run())

    def test_12_post_execution_verification_detects_error(self):
        ver_ok = self.gate.verify_post_execution("get_info", {"status": "SUCCESS", "data": "123"})
        self.assertTrue(ver_ok["verified"])
        self.assertFalse(ver_ok["error_detected"])

        ver_err = self.gate.verify_post_execution("delete_file", {"status": "FAILED", "error": "Access denied"})
        self.assertFalse(ver_err["verified"])
        self.assertTrue(ver_err["error_detected"])


if __name__ == "__main__":
    unittest.main()

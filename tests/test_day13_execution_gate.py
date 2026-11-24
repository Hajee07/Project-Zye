"""
Unit tests for Day 13 Execution Authorization Gate.
Tests zye_intelligence.execution_gate: ZyeExecutionGate, risk classification tiers,
mandatory Negative Brain pre-mortem interlocks, cryptographic approval tokens,
and fail-closed policies.
"""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from zye_intelligence.execution_gate import (
    TOOL_RISK_REGISTRY,
    ZyeExecutionGate,
)
from zye_intelligence.mission_controller import ZyeMissionController
from zye_intelligence.preflight import ZyeSystemPreflight
from zye_intelligence.premortem import ZyeNegativePreMortem


class TestDay13ExecutionGate(unittest.TestCase):
    def setUp(self) -> None:
        self.mc = ZyeMissionController()
        self.pf = ZyeSystemPreflight()
        self.brain = ZyeNegativePreMortem()
        self.gate = ZyeExecutionGate(
            premortem_brain=self.brain,
            preflight=self.pf,
            mission_controller=self.mc,
        )

    def test_01_negative_brain_called_first(self) -> None:
        """Verify modifying tools invoke Negative Brain audit during gate evaluation."""
        with patch.object(self.brain, "run_audit", wraps=self.brain.run_audit) as mock_audit:
            eval_res = asyncio.run(self.gate.evaluate("patch_own_code", {"filename": "main.py"}))
            mock_audit.assert_called_once()
            self.assertIn("audit_report", eval_res)

    def test_02_file_modification_blocked_when_audit_fails(self) -> None:
        """Verify modifying tools are blocked if pre-mortem audit raises exception."""
        with patch.object(self.brain, "run_audit", side_effect=RuntimeError("Audit crashed")):
            eval_res = asyncio.run(self.gate.evaluate("edit_file", {"path": "main.py"}))
            self.assertFalse(eval_res["allowed"])
            self.assertIn("BLOCKED", eval_res["reason"])

    def test_03_system_operation_blocked_when_audit_fails(self) -> None:
        """Verify privileged operations fail-closed when audit brain is unavailable."""
        gate_no_brain = ZyeExecutionGate(premortem_brain=None, preflight=self.pf, mission_controller=self.mc)
        eval_res = asyncio.run(gate_no_brain.evaluate("run_system_command", {"command": "dir"}))
        self.assertFalse(eval_res["allowed"])
        self.assertIn("unavailable", eval_res["reason"].lower())

    def test_04_corrected_steps_applied(self) -> None:
        """Verify audit report attached to gate evaluation contains corrected hardened steps."""
        eval_res = asyncio.run(self.gate.evaluate("patch_own_code", {"filename": "main.py"}))
        audit = eval_res.get("audit_report")
        self.assertIsNotNone(audit)
        self.assertIn("corrected_hardened_steps", audit)

    def test_05_mission_restriction_enforced(self) -> None:
        """Verify that EMERGENCY_LOCKDOWN mission blocks modifying/privileged tools."""
        self.mc.set_mission("EMERGENCY_LOCKDOWN", force=True)
        eval_res = asyncio.run(self.gate.evaluate("patch_own_code", {"filename": "main.py"}))
        self.assertFalse(eval_res["allowed"])
        self.assertIn("EMERGENCY_LOCKDOWN", eval_res["reason"])
        # Restore normal mission
        self.mc.set_mission("NORMAL_ASSISTANT", force=True)

    def test_06_confirmation_required(self) -> None:
        """Verify destructive operations mandate human confirmation token."""
        eval_res = asyncio.run(self.gate.evaluate("delete_file", {"path": "data.db"}))
        self.assertFalse(eval_res["allowed"])
        self.assertTrue(eval_res["requires_confirmation"])
        self.assertIn("approval_token", eval_res)

    def test_07_confirmation_rejected(self) -> None:
        """Verify ungranted or invalid approval tokens are rejected."""
        eval_res = asyncio.run(self.gate.evaluate("delete_file", {"path": "data.db"}, approval_token="invalid_token"))
        self.assertFalse(eval_res["allowed"])

    def test_08_authorization_accepted(self) -> None:
        """Verify tool is permitted once human approval is granted."""
        # 1. Request token
        eval1 = asyncio.run(self.gate.evaluate("delete_file", {"path": "temp.log"}))
        token = eval1["approval_token"]

        # 2. Grant approval
        granted = self.gate.grant_approval(token)
        self.assertTrue(granted)

        # 3. Re-evaluate with granted token
        eval2 = asyncio.run(self.gate.evaluate("delete_file", {"path": "temp.log"}, approval_token=token))
        self.assertTrue(eval2["allowed"])

    def test_09_execution_result_verified(self) -> None:
        """Verify post-execution verification records tool outcome."""
        res = self.gate.verify_post_execution("delete_file", {"status": "SUCCESS"})
        self.assertEqual(res["verification_status"], "SUCCESS")

        res_fail = self.gate.verify_post_execution("delete_file", {"status": "error", "error": "file locked"})
        self.assertEqual(res_fail["verification_status"], "FAILED")

    def test_10_no_gemini_bypass(self) -> None:
        """Verify that direct dispatch through gate cannot be bypassed by tool arguments."""
        eval_res = asyncio.run(self.gate.evaluate(
            "delete_file",
            {"path": "core.py", "override_security": True, "bypass_gate": True}
        ))
        self.assertFalse(eval_res["allowed"])
        self.assertTrue(eval_res["requires_confirmation"])


if __name__ == "__main__":
    unittest.main()

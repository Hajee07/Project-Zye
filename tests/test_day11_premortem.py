"""Unit tests for Zye Day 11 Negative Pre-Mortem Brain."""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from zye_autonomy.premortem import ZyeNegativePreMortem
from zye_autonomy.schemas import NegativeAuditReport


class TestZyeNegativePreMortem(unittest.TestCase):
    def setUp(self):
        self.brain = ZyeNegativePreMortem()

    def test_01_valid_task_audit(self):
        async def _run():
            res = await self.brain.run_audit(
                task_description="Create a new profile file",
                proposed_steps=["Generate config", "Write to profiles/user.json"],
                targets=["profiles/user.json"],
            )
            self.assertIn("overall_failure_risk", res)
            self.assertIn(res["overall_failure_risk"], ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
            self.assertIsInstance(res["predicted_problems"], list)
            self.assertIsInstance(res["corrected_hardened_steps"], list)
        asyncio.run(_run())

    def test_02_missing_task_description_raises(self):
        async def _run():
            with self.assertRaises(ValueError):
                await self.brain.run_audit("", ["step 1"])
        asyncio.run(_run())

    def test_03_missing_proposed_steps_raises(self):
        async def _run():
            with self.assertRaises(ValueError):
                await self.brain.run_audit("Do task", [])
        asyncio.run(_run())

    def test_04_empty_targets_handled(self):
        async def _run():
            res = await self.brain.run_audit("Do task", ["step 1"], targets=[])
            self.assertIn("overall_failure_risk", res)
            self.assertIsInstance(res["corrected_hardened_steps"], list)
        asyncio.run(_run())

    def test_05_valid_gemini_structured_output(self):
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "overall_failure_risk": "MEDIUM",
            "predicted_problems": ["Network drop during file download"],
            "hidden_assumptions_broken": ["Assumed internet is continuously available"],
            "corrected_hardened_steps": ["Check network connectivity first", "Download with retry"],
            "requires_user_confirmation": False,
            "confirmation_reason": "",
            "residual_risks": ["Minor latency spike"],
            "missing_information": [],
            "preflight_summary": {},
            "recommended_execution_strategy": "Proceed with retry policy",
            "audit_timestamp": "2026-11-19T12:00:00Z",
            "model_name": "gemini-2.5-flash",
        })

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        brain = ZyeNegativePreMortem(gemini_client=mock_client)

        async def _run():
            res = await brain.run_audit("Download asset", ["Download from cdn"])
            self.assertEqual(res["overall_failure_risk"], "MEDIUM")
            self.assertEqual(len(res["predicted_problems"]), 1)
            self.assertFalse(res["requires_user_confirmation"])
        asyncio.run(_run())

    def test_06_invalid_gemini_json_raises(self):
        mock_response = MagicMock()
        mock_response.text = "NOT_VALID_JSON{{"

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        brain = ZyeNegativePreMortem(gemini_client=mock_client, config={"strict_json_mode": True})

        async def _run():
            with self.assertRaises(ValueError):
                await brain.run_audit("Download asset", ["Download from cdn"])
        asyncio.run(_run())

    def test_07_pydantic_validation_enforced(self):
        invalid_data = {
            "overall_failure_risk": "INVALID_RISK_STRING",
            "requires_user_confirmation": True,
        }
        with self.assertRaises(Exception):
            self.brain.validate_audit(invalid_data)

    def test_08_high_risk_result(self):
        async def _run():
            res = await self.brain.run_audit(
                task_description="Modify existing python source file",
                proposed_steps=["Open zye_audio_ear.py", "Edit buffer logic", "Save file"],
                targets=["zye_audio_ear.py"],
            )
            self.assertIn(res["overall_failure_risk"], ["HIGH", "CRITICAL"])
            self.assertTrue(res["requires_user_confirmation"])
        asyncio.run(_run())

    def test_09_critical_risk_result(self):
        async def _run():
            res = await self.brain.run_audit(
                task_description="Delete user database and purge archives",
                proposed_steps=["Drop tables", "Delete database file"],
                targets=["data/database.sqlite"],
            )
            self.assertEqual(res["overall_failure_risk"], "CRITICAL")
            self.assertTrue(res["requires_user_confirmation"])
            self.assertIn("backup", res["confirmation_reason"].lower() + str(res["corrected_hardened_steps"]).lower())
        asyncio.run(_run())

    def test_10_hidden_assumptions_reported(self):
        async def _run():
            res = await self.brain.run_audit(
                task_description="Write data to sales.xlsx",
                proposed_steps=["Write records", "Save"],
            )
            self.assertGreater(len(res["hidden_assumptions_broken"]), 0)
        asyncio.run(_run())

    def test_11_corrected_hardened_steps_generated(self):
        async def _run():
            res = await self.brain.run_audit(
                task_description="Delete obsolete test cache",
                proposed_steps=["rm -rf cache"],
            )
            steps = self.brain.create_hardened_plan(res)
            self.assertIsInstance(steps, list)
            self.assertGreater(len(steps), 0)
        asyncio.run(_run())

    def test_12_residual_risks_reported(self):
        async def _run():
            res = await self.brain.run_audit(
                task_description="Task with residual risks",
                proposed_steps=["step 1"],
            )
            self.assertIn("residual_risks", res)
            self.assertIsInstance(res["residual_risks"], list)
        asyncio.run(_run())

    def test_13_gemini_call_failure_uses_offline_fallback(self):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("API Network Timeout")

        brain = ZyeNegativePreMortem(gemini_client=mock_client)

        async def _run():
            res = await brain.run_audit("Do operation", ["step 1"])
            self.assertIn(res["overall_failure_risk"], ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
            self.assertIn("API Network Timeout", str(res["residual_risks"]))
        asyncio.run(_run())

    def test_14_tool_execution_prohibited_by_audit(self):
        # Verify that running an audit has zero side effects and does not execute tools
        async def _run():
            res = await self.brain.run_audit("Delete all project files", ["del *.*"])
            # The audit only audits and returns report, never executes
            self.assertIn("overall_failure_risk", res)
            self.assertFalse(hasattr(self.brain, "execute_tool"))
        asyncio.run(_run())

    def test_15_calculate_risk_level_helper(self):
        report = {"overall_failure_risk": "HIGH"}
        self.assertEqual(self.brain.calculate_risk_level(report), "HIGH")


if __name__ == "__main__":
    unittest.main()

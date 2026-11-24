"""
Unit tests for Day 13 100% Negative Pre-Mortem Brain & FMEA.
Tests zye_intelligence.premortem: ZyeNegativePreMortem, _run_negative_brain_sync,
and zye_intelligence.negative_audit: NegativeAuditEngine.
"""

from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from zye_intelligence.negative_audit import NegativeAuditEngine
from zye_intelligence.premortem import ZyeNegativePreMortem, _run_negative_brain_sync
from zye_intelligence.schemas import NegativeAuditReport


class TestDay13NegativeBrain(unittest.TestCase):
    def setUp(self) -> None:
        self.brain = ZyeNegativePreMortem()
        self.engine = NegativeAuditEngine(premortem_brain=self.brain)

    def test_01_valid_audit(self) -> None:
        """Test a normal adversarial pre-mortem audit."""
        report = asyncio.run(self.brain.run_audit(
            task_description="Create a backup file of main.py",
            proposed_steps=["Read main.py", "Copy to backups/main.py.bak"],
            targets=["main.py"],
        ))
        self.assertIn("overall_failure_risk", report)
        self.assertIn(report["overall_failure_risk"], ("LOW", "MEDIUM", "HIGH", "CRITICAL"))
        self.assertIsInstance(report["predicted_problems"], list)
        self.assertIsInstance(report["corrected_hardened_steps"], list)
        self.assertIsInstance(report["requires_user_confirmation"], bool)

    def test_02_missing_task_description(self) -> None:
        """Test that empty or whitespace task description raises ValueError."""
        with self.assertRaises(ValueError):
            asyncio.run(self.brain.run_audit(
                task_description="   ",
                proposed_steps=["step 1"],
            ))

    def test_03_empty_proposed_plan(self) -> None:
        """Test that empty proposed steps raises ValueError."""
        with self.assertRaises(ValueError):
            asyncio.run(self.brain.run_audit(
                task_description="Valid task",
                proposed_steps=[],
            ))

    def test_04_invalid_gemini_json(self) -> None:
        """Test handling when Gemini returns invalid non-JSON output."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "NOT JSON AT ALL {{{ malformed"
        mock_client.models.generate_content.return_value = mock_response

        client_brain = ZyeNegativePreMortem(gemini_client=mock_client)
        # Should gracefully fall back to offline FMEA
        report = asyncio.run(client_brain.run_audit(
            task_description="Edit database",
            proposed_steps=["step 1"],
        ))
        self.assertIn("overall_failure_risk", report)

    def test_05_missing_required_fields(self) -> None:
        """Test Pydantic schema validation when required fields are missing."""
        invalid_data = {
            "predicted_problems": ["p1"],
            "hidden_assumptions_broken": ["a1"],
            # missing overall_failure_risk and requires_user_confirmation
        }
        with self.assertRaises(Exception):
            NegativeAuditReport(**invalid_data)

    def test_06_invalid_risk_classification(self) -> None:
        """Test that invalid risk values (e.g. 'EXTREME', 'MINIMAL') are rejected."""
        invalid_data = {
            "overall_failure_risk": "EXTREME",
            "predicted_problems": [],
            "hidden_assumptions_broken": [],
            "corrected_hardened_steps": [],
            "requires_user_confirmation": False,
        }
        with self.assertRaises(Exception):
            NegativeAuditReport(**invalid_data)

    def test_07_model_timeout(self) -> None:
        """Test fallback when Gemini client raises a timeout exception."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = TimeoutError("Gemini API deadline exceeded")

        client_brain = ZyeNegativePreMortem(gemini_client=mock_client)
        report = asyncio.run(client_brain.run_audit(
            task_description="Delete old logs",
            proposed_steps=["Purge logs"],
        ))
        self.assertIn("overall_failure_risk", report)
        self.assertEqual(report["overall_failure_risk"], "CRITICAL")  # Destructive action

    def test_08_api_failure(self) -> None:
        """Test resilience against 500/network API errors."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("503 Service Unavailable")

        client_brain = ZyeNegativePreMortem(gemini_client=mock_client)
        report = asyncio.run(client_brain.run_audit(
            task_description="Read error log",
            proposed_steps=["Read file"],
        ))
        self.assertIn("overall_failure_risk", report)

    def test_09_audit_failure_blocks_protected_execution(self) -> None:
        """Test that high/critical risk audits without user confirmation block execution."""
        audit = NegativeAuditReport(
            overall_failure_risk="CRITICAL",
            predicted_problems=["Data loss risk"],
            hidden_assumptions_broken=["Assumed target had backup"],
            corrected_hardened_steps=["Step 1"],
            requires_user_confirmation=True,
        )
        auth = asyncio.run(self.engine.authorize_execution(audit, approval={"user_confirmed": False}))
        self.assertFalse(auth["authorized"])
        self.assertIn("BLOCKED", auth["reason"])

    def test_10_predicted_problems_processed(self) -> None:
        """Test that failure modes identified in preflight appear in predicted problems."""
        telemetry = {
            "ram_used_pct": 95.0,
            "disk_used_pct": 94.0,
            "target_diagnostics": [{"target": "db.sqlite", "possible_lock_status": "LOCKED", "writable": False}],
        }
        modes = asyncio.run(self.engine.identify_failure_modes("Write to database", telemetry))
        self.assertTrue(any("RAM" in m for m in modes))
        self.assertTrue(any("DISK" in m for m in modes))
        self.assertTrue(any("LOCKED" in m for m in modes))

    def test_11_hidden_assumptions_processed(self) -> None:
        """Test that broken assumptions are identified for modifying operations."""
        report = _run_negative_brain_sync(
            task_description="Patch own source code in main.py",
            proposed_steps=["Modify file directly"],
            targets=["main.py"],
        )
        self.assertGreater(len(report["hidden_assumptions_broken"]), 0)

    def test_12_hardened_plan_applied(self) -> None:
        """Test that self-correcting engine injects backup and verification steps."""
        report = asyncio.run(self.engine.audit_task(
            task="Edit configuration file zye_config.toml",
            proposed_steps=["Overwrite file"],
            targets=["zye_config.toml"],
        ))
        steps = report.corrected_hardened_steps
        self.assertTrue(any("backup" in s.lower() for s in steps))
        self.assertTrue(any("verif" in s.lower() for s in steps))

    def test_13_residual_risk_reporting(self) -> None:
        """Test residual risks are reported honestly without claiming 100% elimination."""
        audit = NegativeAuditReport(
            overall_failure_risk="MEDIUM",
            predicted_problems=["Network drop"],
            hidden_assumptions_broken=[],
            corrected_hardened_steps=["Use retry"],
            requires_user_confirmation=False,
            residual_risks=["API latency jitter"],
            missing_information=["Current cloud quota status"],
        )
        residual = asyncio.run(self.engine.evaluate_residual_risks(audit))
        self.assertGreater(len(residual), 0)
        self.assertTrue(any("quota" in r.lower() for r in residual))

    def test_14_no_recursive_audit(self) -> None:
        """Verify that pre-mortem tools themselves are exempt and never self-recurse."""
        from zye_intelligence.execution_gate import EXEMPT_TOOLS
        self.assertIn("run_negative_premortem_brain", EXEMPT_TOOLS)
        self.assertIn("compare_and_decide_solutions", EXEMPT_TOOLS)


if __name__ == "__main__":
    unittest.main()

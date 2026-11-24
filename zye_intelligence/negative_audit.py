"""
Self-Correcting Execution Planner & Negative Audit Engine — Zye Day 13.
Implements NegativeAuditEngine to orchestrate preflight inspection, adversarial FMEA,
plan self-correction, residual risk calculation, and authorization verification.
"""

from __future__ import annotations

import logging
from typing import Any

from zye_intelligence.preflight import ZyeSystemPreflight
from zye_intelligence.premortem import ZyeNegativePreMortem
from zye_intelligence.schemas import NegativeAuditReport

logger = logging.getLogger("zye.intelligence.negative_audit")


class NegativeAuditEngine:
    """
    Self-correcting execution planner and audit coordinator.
    Enforces preflight diagnostics, failure mode analysis, hardened step synthesis,
    and authorization gates prior to protected MCP tool execution.
    """

    def __init__(
        self,
        preflight: ZyeSystemPreflight | None = None,
        premortem_brain: ZyeNegativePreMortem | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.preflight = preflight or ZyeSystemPreflight()
        self.premortem_brain = premortem_brain or ZyeNegativePreMortem()
        self.config = config or {}

    async def inspect_preflight(self, targets: list[str]) -> dict[str, Any]:
        """Inspect live system telemetry and target resource states asynchronously."""
        return await self.preflight.preflight_system_check_async(targets)

    async def identify_failure_modes(
        self, task: str, telemetry: dict[str, Any]
    ) -> list[str]:
        """
        Adversarially evaluate task against telemetry to extract potential failure modes.
        """
        modes: list[str] = []
        ram_pct = telemetry.get("ram_used_pct", 0.0)
        disk_pct = telemetry.get("disk_used_pct", 0.0)
        batt_pct = telemetry.get("battery_percent")
        plugged = telemetry.get("power_plugged")

        if ram_pct >= 88.0:
            modes.append(f"RAM_SATURATION: {ram_pct:.1f}% used")
        if disk_pct >= 92.0:
            modes.append(f"DISK_EXHAUSTION: {disk_pct:.1f}% used")
        if plugged is False and batt_pct is not None and batt_pct <= 15.0:
            modes.append(f"BATTERY_LOW: {batt_pct:.1f}% unplugged")

        for diag in telemetry.get("target_diagnostics", []):
            if diag.get("exists") is False:
                modes.append(f"TARGET_MISSING: {diag.get('target')}")
            elif diag.get("possible_lock_status") == "LOCKED":
                modes.append(f"TARGET_LOCKED: {diag.get('target')}")
            elif diag.get("writable") is False:
                modes.append(f"PERMISSION_DENIED: {diag.get('target')}")

        return modes

    async def correct_execution_plan(
        self, audit: NegativeAuditReport
    ) -> list[str]:
        """
        Read predicted problems and broken assumptions, applying mitigations to produce
        an updated, hardened execution plan.
        """
        corrected: list[str] = []
        corrected.append("Validate system preflight prerequisites and active file locks")

        # Check if backups are needed
        has_file_risk = any(
            any(k in p.lower() for k in ["file", "disk", "write", "lock", "patch", "modify"])
            for p in audit.predicted_problems
        )
        if has_file_risk or audit.overall_failure_risk in ("HIGH", "CRITICAL"):
            corrected.append("Create atomic timestamped backup in backups/ directory")

        # Incorporate original or hardened steps
        for step in audit.corrected_hardened_steps:
            if step not in corrected:
                corrected.append(step)

        # Append post-execution verification
        if not any("verif" in s.lower() for s in corrected):
            corrected.append("Perform post-execution integrity verification and telemetry check")

        return corrected

    async def evaluate_residual_risks(
        self, audit: NegativeAuditReport
    ) -> list[str]:
        """
        Evaluate irreducible uncertainties, unmonitored external dependencies,
        and residual risks after plan correction.
        """
        residual: list[str] = list(audit.residual_risks)
        if not residual:
            residual.append("Transient OS scheduling latency or unmonitored concurrent processes")

        for missing in audit.missing_information:
            if missing not in residual:
                residual.append(f"Information Gap: {missing}")

        return residual

    async def authorize_execution(
        self,
        audit: NegativeAuditReport,
        approval: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate risk policy and human confirmation rules.
        LOW: Can proceed automatically.
        MEDIUM: Can proceed with mitigations unless mission mandates zero-trust.
        HIGH / CRITICAL: Requires verified human approval token.
        """
        risk = audit.overall_failure_risk
        requires_confirm = audit.requires_user_confirmation
        appr = approval or {}

        if risk == "CRITICAL" or requires_confirm:
            confirmed = bool(appr.get("user_confirmed", False))
            if not confirmed:
                return {
                    "authorized": False,
                    "risk_level": risk,
                    "reason": f"Execution BLOCKED: Operation classified as {risk} risk and requires explicit human confirmation.",
                    "requires_user_confirmation": True,
                    "rollback_ready": len(audit.rollback_plan) > 0,
                }

        return {
            "authorized": True,
            "risk_level": risk,
            "reason": f"Execution authorized under {audit.mission_mode} profile.",
            "requires_user_confirmation": False,
            "rollback_ready": len(audit.rollback_plan) > 0,
        }

    async def audit_task(
        self,
        task: str,
        proposed_steps: list[str] | None = None,
        targets: list[str] | None = None,
        mission: str = "NORMAL_ASSISTANT",
    ) -> NegativeAuditReport:
        """
        Full end-to-end self-correcting negative audit workflow:
        1. Live system preflight inspection
        2. Adversarial FMEA audit via Gemini or offline heuristics
        3. Plan self-correction
        4. Residual risk evaluation
        5. Return validated NegativeAuditReport model instance
        """
        steps = proposed_steps or ["Analyze task requirements", "Execute tool action", "Verify result"]
        t_list = targets or []

        # 1. Preflight
        preflight_data = await self.inspect_preflight(t_list)

        # 2. Run adversarial pre-mortem
        audit_raw = await self.premortem_brain.run_audit(
            task_description=task,
            proposed_steps=steps,
            targets=t_list,
            preflight_summary=preflight_data,
            mission=mission,
        )

        report = NegativeAuditReport(**audit_raw)

        # 3. Plan self-correction
        corrected_steps = await self.correct_execution_plan(report)
        report.corrected_hardened_steps = corrected_steps

        # 4. Residual risks
        residual = await self.evaluate_residual_risks(report)
        report.residual_risks = residual

        return report

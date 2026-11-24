"""
100% Negative Pre-Mortem Brain & Adversarial FMEA — Zye Day 13.
Implements the Devil's Advocate reasoning engine, structured Gemini 2.5 Flash audits,
and deterministic offline FMEA heuristics when offline.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

from zye_intelligence.schemas import NegativeAuditReport

logger = logging.getLogger("zye.intelligence.premortem")

ADVERSARIAL_SYSTEM_INSTRUCTION = (
    "You are Zye's 100% Pessimistic Adversarial Devil's Advocate Brain.\n\n"
    "Your ONLY mission is to perform an exhaustive Failure Mode and Effects Analysis (FMEA) "
    "before any task is executed.\n\n"
    "Assume Murphy's Law: Every reasonably foreseeable failure scenario must be investigated.\n"
    "Do not blindly trust the original plan.\n"
    "Identify every observable risk, hidden broken assumption, and missing dependency.\n"
    "Predict possible crashes, data loss, race conditions, resource exhaustion, permission failures, "
    "network failures, security problems, and unexpected application behavior.\n\n"
    "CATEGORIES TO AUDIT:\n"
    "A. Filesystem Failures (file not found, file locked, permission denied, invalid path, traversal, "
    "disk exhaustion, corrupt file, overwrite, missing backup)\n"
    "B. System Failures (RAM exhaustion, CPU overload, disk saturation, process termination, driver/device unavailable)\n"
    "C. Execution Failures (wrong execution order, missing dependency, invalid args, stale tool schema, timeouts, races)\n"
    "D. Network Failures (offline, DNS failure, rate limit, auth failure, request timeout)\n"
    "E. Security Failures (unauthorized operation, command injection, path traversal, credential exposure)\n"
    "F. Logical Failures (wrong assumptions, missing inputs, division by zero, invalid data)\n"
    "G. Recovery Failures (backup missing, rollback failure, partial database update)\n\n"
    "Correct the plan before execution. Produce a structured hardened execution strategy.\n"
    "Separate confirmed facts, inferred risks, and unknown conditions.\n"
    "Never invent telemetry or pretend a diagnostic check succeeded.\n"
    "Return a structured JSON object strictly matching the NegativeAuditReport schema."
)


def _clean_gemini_schema(d: Any) -> Any:
    """Recursively strip fields unsupported by Gemini Developer API mode (e.g. additionalProperties)."""
    if isinstance(d, dict):
        d.pop("additionalProperties", None)
        for k, v in list(d.items()):
            d[k] = _clean_gemini_schema(v)
    elif isinstance(d, list):
        return [_clean_gemini_schema(item) for item in d]
    return d


def _generate_offline_fmea(
    task: str,
    steps: list[str],
    targets: list[str],
    preflight: dict[str, Any],
    mission: str,
) -> dict[str, Any]:
    """
    Deterministic offline Failure Mode and Effects Analysis (FMEA).
    Provides robust, hardened adversarial auditing when cloud Gemini is unreachable.
    """
    t_lower = task.lower()
    predicted_problems: list[str] = []
    broken_assumptions: list[str] = []
    hardened_steps: list[str] = []
    evidence: list[str] = []
    mitigations: list[str] = []
    residual_risks: list[str] = []
    rollback_plan: list[str] = []
    verification_steps: list[str] = []
    required_permissions: list[str] = []
    missing_info: list[str] = []

    # 1. Telemetry checks
    ram_pct = float(preflight.get("ram_used_pct", 0.0))
    disk_pct = float(preflight.get("disk_used_pct", 0.0))
    batt_pct = preflight.get("battery_percent")
    batt_plugged = preflight.get("power_plugged")

    if ram_pct >= 88.0:
        predicted_problems.append(f"RAM utilization is at {ram_pct:.1f}% (>= 88% threshold) — risk of OOM crash")
        broken_assumptions.append("Assumed sufficient free system memory for execution")
        mitigations.append("Invoke garbage collection and inspect top memory processes before task")
        evidence.append(f"Measured RAM used: {ram_pct:.1f}%")

    if disk_pct >= 92.0:
        predicted_problems.append(f"Disk utilization is at {disk_pct:.1f}% (>= 92% threshold) — risk of write saturation")
        broken_assumptions.append("Assumed adequate disk storage for temp files and backups")
        mitigations.append("Verify free disk block headroom on containing drive")
        evidence.append(f"Measured Disk used: {disk_pct:.1f}%")

    if batt_plugged is False and batt_pct is not None and batt_pct <= 15.0:
        severity_label = "CRITICAL" if batt_pct <= 8.0 else "HIGH"
        predicted_problems.append(f"Battery is {severity_label} ({batt_pct:.1f}%, unplugged) — risk of mid-execution shutdown")
        broken_assumptions.append("Assumed persistent power supply during multi-step operation")
        mitigations.append("Switch to STEALTH_BATTERY_SAVER mission profile and defer non-essential compute")
        evidence.append(f"Measured Battery: {batt_pct:.1f}%, unplugged")

    # 2. Target path checks
    target_diags = preflight.get("target_diagnostics", [])
    for diag in target_diags:
        t_name = diag.get("target") or diag.get("original_target", "unknown")
        if diag.get("exists") is False:
            if not any(k in t_lower for k in ["create", "new", "write", "generate"]):
                predicted_problems.append(f"Target file or path does not exist: {t_name}")
                broken_assumptions.append(f"Assumed target resource '{t_name}' already existed")
                mitigations.append(f"Verify path or create required parent directories for '{t_name}'")
        elif diag.get("possible_lock_status") == "LOCKED":
            predicted_problems.append(f"Target file '{t_name}' is locked by another process (sharing violation)")
            broken_assumptions.append(f"Assumed exclusive read/write access to target file '{t_name}'")
            mitigations.append(f"Prompt user to save and close active application holding lock on '{t_name}'")
            evidence.append(f"File handle lock violation detected on '{t_name}'")
        elif diag.get("lock_status") == "UNKNOWN":
            missing_info.append(f"Definitive lock status for '{t_name}' is UNKNOWN (non-invasive check)")

        if diag.get("exists") is True and diag.get("writable") is False:
            predicted_problems.append(f"Target '{t_name}' is read-only or permission denied")
            broken_assumptions.append(f"Assumed write permissions on '{t_name}'")
            required_permissions.append(f"Write permissions for '{t_name}'")

    # 3. Action type checks
    is_modifying = any(k in t_lower for k in ["patch", "edit", "write", "modify", "update", "repair", "replace"])
    is_destructive = any(k in t_lower for k in ["delete", "remove", "drop", "purge", "format", "erase"])
    is_code = any(k in t_lower for k in ["code", "py", "script", "function", "class", "ast"])

    if is_modifying or is_destructive:
        broken_assumptions.append("Assumed original file contents can be replaced without immediate rollback backup")
        mitigations.append("Generate timestamped pre-operation backup before applying modifications")
        rollback_plan.append("Restore original file state from pre-operation backup if execution fails")
        verification_steps.append("Inspect target file hash and syntax compilation after write")

    if is_code:
        predicted_problems.append("Potential syntax error, import error, or regression in patched Python code")
        mitigations.append("Run AST parsing and py_compile check prior to saving changes")
        verification_steps.append("Execute python -m py_compile on modified script")

    # 4. Construct hardened execution steps
    hardened_steps.append("Step 0: Validate target resources, free disk space, and active locks")
    if is_modifying or is_destructive:
        hardened_steps.append("Step 1: Create atomic backup copy in backups/ directory")
    for idx, s in enumerate(steps, start=2):
        hardened_steps.append(f"Step {idx}: Execute hardened action: {s}")
    hardened_steps.append(f"Step {len(steps) + 2}: Run post-execution verification and health audit")

    # 5. Determine overall failure risk
    if is_destructive or any("CRITICAL" in p for p in predicted_problems):
        risk = "CRITICAL"
        requires_confirm = True
    elif is_modifying or any("lock" in p.lower() for p in predicted_problems) or len(predicted_problems) >= 2:
        risk = "HIGH"
        requires_confirm = True
    elif len(predicted_problems) == 1 or mission == "EMERGENCY_LOCKDOWN":
        risk = "MEDIUM"
        requires_confirm = (mission == "EMERGENCY_LOCKDOWN")
    else:
        risk = "LOW"
        requires_confirm = False

    residual_risks.append("Unmonitored background OS processes could acquire lock concurrently")
    if missing_info:
        residual_risks.extend(missing_info)

    return {
        "overall_failure_risk": risk,
        "predicted_problems": predicted_problems if predicted_problems else ["No critical failure modes identified"],
        "hidden_assumptions_broken": broken_assumptions if broken_assumptions else ["Standard operational assumptions hold"],
        "corrected_hardened_steps": hardened_steps,
        "requires_user_confirmation": requires_confirm,
        "confirmation_reason": f"FMEA identified {len(predicted_problems)} potential risk factors requiring verification" if requires_confirm else "",
        "risk_rationale": f"Adversarial audit completed: classified as {risk} failure risk based on system state and operation scope.",
        "evidence": evidence,
        "affected_resources": targets if targets else ["System processes"],
        "mitigation_actions": mitigations if mitigations else ["Proceed with standard safety boundaries"],
        "residual_risks": residual_risks,
        "rollback_plan": rollback_plan if rollback_plan else ["No rollback required for read-only actions"],
        "verification_steps": verification_steps if verification_steps else ["Verify process return code"],
        "required_permissions": required_permissions if required_permissions else ["Standard user permissions"],
        "missing_information": missing_info,
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "mission_mode": mission,
        "audit_version": "1.0.0",
        "preflight_summary": preflight,
    }


class ZyeNegativePreMortem:
    """
    100% Negative Pre-Mortem Brain Engine.
    Uses Google Gemini 2.5 Flash with structured output and falls back to deterministic
    offline FMEA analysis when credentials or network connectivity are absent.
    """

    def __init__(
        self, gemini_client: Any = None, config: dict[str, Any] | None = None
    ) -> None:
        self._client = gemini_client
        self._config = config or {}
        self._model = self._config.get("model", "gemini-3.8-flash")
        self._temperature = float(self._config.get("temperature", 0.2))

        if self._client is None:
            try:
                from gemini_gateway import ZyeGeminiGateway
                gw = ZyeGeminiGateway.get_instance()
                self._client = gw.key_manager.get_client(3) or gw.key_manager.get_client(1)
            except Exception:
                self._client = None

    def _call_gemini_structured_sync(
        self,
        task_description: str,
        steps: list[str],
        targets: list[str],
        preflight: dict[str, Any],
        mission: str,
    ) -> dict[str, Any]:
        """Synchronous invocation of Gemini API with structured NegativeAuditReport output."""
        if self._client is None:
            logger.info("Gemini client not provided — running offline pre-mortem heuristics")
            return _generate_offline_fmea(task_description, steps, targets, preflight, mission)

        prompt = (
            f"=== ADVERSARIAL PRE-MORTEM REQUEST ===\n"
            f"TASK DESCRIPTION:\n{task_description}\n\n"
            f"PROPOSED STEPS:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps)) + "\n\n"
            f"TARGET RESOURCES:\n" + ("\n".join(f"- {t}" for t in targets) if targets else "(none)") + "\n\n"
            f"ACTIVE MISSION MODE: {mission}\n\n"
            f"LIVE PREFLIGHT TELEMETRY:\n{json.dumps(preflight, indent=2)}\n\n"
            f"Perform an adversarial FMEA audit. Return ONLY valid JSON matching NegativeAuditReport."
        )

        try:
            clean_schema = _clean_gemini_schema(NegativeAuditReport.model_json_schema())
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config={
                    "system_instruction": ADVERSARIAL_SYSTEM_INSTRUCTION,
                    "temperature": self._temperature,
                    "response_mime_type": "application/json",
                    "response_schema": clean_schema,
                },
            )
            raw_text = response.text or ""
            if not raw_text.strip():
                raise ValueError("Gemini returned empty pre-mortem response")
            data = json.loads(raw_text)
            # Validate schema
            report = NegativeAuditReport(**data)
            return report.model_dump()
        except json.JSONDecodeError as jde:
            # If strict_json_mode is enabled (Day 11 backward compat), re-raise as ValueError
            if self._config.get("strict_json_mode", False):
                raise ValueError(f"Invalid JSON from Gemini: {jde}") from jde
            logger.warning("Gemini pre-mortem call failed (%s); using hardened offline audit", jde)
            fallback = _generate_offline_fmea(task_description, steps, targets, preflight, mission)
            fallback.setdefault("residual_risks", [])
            fallback["residual_risks"].append(f"Gemini JSON parse error: {jde}")
            return fallback
        except Exception as exc:
            logger.warning("Gemini pre-mortem call failed (%s); using hardened offline audit", exc)
            fallback = _generate_offline_fmea(task_description, steps, targets, preflight, mission)
            fallback.setdefault("residual_risks", [])
            fallback["residual_risks"].append(f"Gemini call failed: {exc}")
            return fallback

    # ── Day 11 backward-compatibility methods ──────────────────────────

    def validate_audit(self, data: dict[str, Any]) -> NegativeAuditReport:
        """Validate a dict against NegativeAuditReport schema. Raises on invalid data."""
        return NegativeAuditReport(**data)

    @staticmethod
    def create_hardened_plan(audit_result: dict[str, Any]) -> list[str]:
        """Extract or generate a hardened execution plan from an audit result dict."""
        steps = audit_result.get("corrected_hardened_steps", [])
        if steps:
            return list(steps)
        # Fallback: wrap predicted problems as verification steps
        problems = audit_result.get("predicted_problems", [])
        return [f"Verify mitigation for: {p}" for p in problems] if problems else ["No hardened steps available"]

    @staticmethod
    def calculate_risk_level(audit_result: dict[str, Any]) -> str:
        """Extract the overall failure risk level from an audit result dict."""
        return audit_result.get("overall_failure_risk", "MEDIUM")

    # ── Core audit entry point ───────────────────────────────────────

    async def run_audit(
        self,
        task_description: str,
        proposed_steps: list[str],
        targets: list[str] | None = None,
        preflight_summary: dict[str, Any] | None = None,
        mission: str = "NORMAL_ASSISTANT",
    ) -> dict[str, Any]:
        """
        Run adversarial audit asynchronously via asyncio.to_thread.
        Validates inputs, executes FMEA, and returns NegativeAuditReport dict.
        """
        if not task_description or not str(task_description).strip():
            raise ValueError("task_description must not be empty")
        if not proposed_steps or len(proposed_steps) == 0:
            raise ValueError("proposed_steps must not be empty")

        targets_clean = targets or []
        pf = preflight_summary or {}

        # Run model or offline heuristics with tight timeout to prevent freezing
        try:
            audit_dict = await asyncio.wait_for(
                asyncio.to_thread(
                    self._call_gemini_structured_sync,
                    task_description=str(task_description).strip(),
                    steps=list(proposed_steps),
                    targets=list(targets_clean),
                    preflight=pf,
                    mission=mission,
                ),
                timeout=3.5,
            )
        except (asyncio.TimeoutError, Exception) as exc:
            logger.info("Pre-mortem audit timed out or offline (%s); using hardened offline FMEA", exc)
            audit_dict = _generate_offline_fmea(task_description, proposed_steps, targets_clean, pf, mission)

        # Validate with Pydantic
        report = NegativeAuditReport(**audit_dict)
        return report.model_dump()


def _run_negative_brain_sync(
    task_description: str,
    proposed_steps: list[str],
    targets: list[str] | None = None,
) -> dict[str, Any]:
    """Top-level synchronous entry point for Section 07 pre-mortem audits."""
    from zye_intelligence.preflight import ZyeSystemPreflight

    pf = ZyeSystemPreflight().generate_preflight_report(targets or [])
    brain = ZyeNegativePreMortem()
    return _generate_offline_fmea(
        task=task_description,
        steps=proposed_steps,
        targets=targets or [],
        preflight=pf,
        mission="NORMAL_ASSISTANT",
    )

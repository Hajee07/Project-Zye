"""
Central Safety Gateway for Zye Personal Assistant (Day 14).
Integrates Day 13 Negative Pre-Mortem Brain to audit protected operations,
predict failure modes, apply self-correcting steps, and require authorization.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from pathlib import Path
from typing import Any, Optional

from zye_personal_assistant.audit_logger import AuditLogger

logger = logging.getLogger("zye.personal_assistant.safety")

# Protected action types that require Negative Brain pre-mortem audit
PROTECTED_ACTION_TYPES = frozenset({
    "EMAIL_SEND",
    "CALENDAR_DELETE",
    "CALENDAR_CREATE",
    "DOC_ORGANIZE",
    "TASK_BULK_TIMEBLOCK",
    "PROJECT_UPDATE",
    "EXTERNAL_API",
})


class SafetyGateway:
    """
    Evaluates actions against security policy and Day 13 Negative Pre-Mortem Brain.
    """

    def __init__(self, db_path: str | Path | None = None, premortem_brain: Any = None) -> None:
        self._db_path = db_path
        self._audit = AuditLogger(db_path=db_path)
        self._premortem_brain = premortem_brain

    def _get_premortem_brain(self) -> Any:
        if self._premortem_brain is not None:
            return self._premortem_brain
        try:
            from zye_intelligence.premortem import ZyeNegativePreMortem
            self._premortem_brain = ZyeNegativePreMortem()
            return self._premortem_brain
        except Exception as e:
            logger.warning("Could not initialize ZyeNegativePreMortem: %s", e)
            return None

    async def authorize_personal_assistant_action(
        self,
        action_type: str,
        task_description: str,
        proposed_steps: list[str],
        target_resources: list[str],
        force_offline_audit: bool = False,
    ) -> dict[str, Any]:
        """
        Evaluate proposed action with Day 13 Negative Brain.
        Returns authorization decision, risk assessment, and hardened steps.
        """
        is_protected = action_type in PROTECTED_ACTION_TYPES

        # If not a protected action, authorize immediately
        if not is_protected:
            self._audit.log_action(
                action_type=action_type,
                target_resources=",".join(target_resources),
                premortem_risk="LOW",
                authorized=True,
                result_status="AUTHORIZED",
                details="Standard non-protected operation.",
            )
            return {
                "authorized": True,
                "overall_failure_risk": "LOW",
                "requires_user_confirmation": False,
                "confirmation_reason": "",
                "predicted_problems": [],
                "corrected_hardened_steps": proposed_steps,
                "residual_risks": [],
            }

        # Protected operation: Must run Negative Pre-Mortem Brain
        brain = self._get_premortem_brain()
        if brain is None:
            # Section 17.6: If the Negative Brain is unavailable, block protected operations.
            err_msg = "Protected operation blocked: Negative Pre-Mortem Brain is unavailable."
            self._audit.log_action(
                action_type=action_type,
                target_resources=",".join(target_resources),
                premortem_risk="CRITICAL",
                authorized=False,
                result_status="BLOCKED_NO_BRAIN",
                details=err_msg,
            )
            return {
                "authorized": False,
                "overall_failure_risk": "CRITICAL",
                "requires_user_confirmation": True,
                "confirmation_reason": err_msg,
                "predicted_problems": [err_msg],
                "corrected_hardened_steps": [],
                "residual_risks": ["Safety brain unavailable"],
            }

        try:
            # Call Day 13 run_audit
            coro = brain.run_audit(
                task_description=task_description,
                proposed_steps=proposed_steps,
                targets=target_resources,
                mission="NORMAL_ASSISTANT",
            )
            if inspect.isawaitable(coro):
                audit_result = await coro
            else:
                audit_result = coro

            risk = audit_result.get("overall_failure_risk", "MEDIUM")
            req_confirm = audit_result.get("requires_user_confirmation", False)
            problems = audit_result.get("predicted_problems", [])
            hardened_steps = audit_result.get("corrected_hardened_steps", proposed_steps)

            # High or Critical risk requires confirmation
            if risk in ("HIGH", "CRITICAL"):
                req_confirm = True

            self._audit.log_action(
                action_type=action_type,
                target_resources=",".join(target_resources),
                premortem_risk=risk,
                authorized=not req_confirm or not audit_result.get("blocked", False),
                result_status="AUDITED",
                details=f"Problems predicted: {len(problems)}",
            )

            return {
                "authorized": True,
                "overall_failure_risk": risk,
                "requires_user_confirmation": req_confirm,
                "confirmation_reason": audit_result.get("confirmation_reason", "Protected operation requires confirmation"),
                "predicted_problems": problems,
                "corrected_hardened_steps": hardened_steps,
                "residual_risks": audit_result.get("residual_risks", []),
            }

        except Exception as exc:
            logger.error("Negative Brain audit failure for %s: %s", action_type, exc)
            self._audit.log_action(
                action_type=action_type,
                target_resources=",".join(target_resources),
                premortem_risk="CRITICAL",
                authorized=False,
                result_status="AUDIT_EXCEPTION",
                details=str(exc),
            )
            return {
                "authorized": False,
                "overall_failure_risk": "CRITICAL",
                "requires_user_confirmation": True,
                "confirmation_reason": f"Negative Brain execution failed: {exc}",
                "predicted_problems": [f"Audit execution exception: {exc}"],
                "corrected_hardened_steps": [],
                "residual_risks": ["Unknown failure mode due to audit crash"],
            }

    def authorize_personal_assistant_action_sync(
        self,
        action_type: str,
        task_description: str,
        proposed_steps: list[str],
        target_resources: list[str],
    ) -> dict[str, Any]:
        """Synchronous deterministic safety evaluation (safe for non-async contexts & CLI tools)."""
        res = self._offline_heuristic_audit(action_type, task_description, proposed_steps, target_resources)
        self._audit.log_action(
            action_type=action_type,
            target_resources=",".join(target_resources),
            premortem_risk=res.get("overall_failure_risk", "LOW"),
            authorized=res.get("authorized", True),
            result_status="AUDITED_SYNC",
            details="Synchronous security gate evaluation",
        )
        return res


    def _offline_heuristic_audit(
        self,
        action_type: str,
        task_description: str,
        proposed_steps: list[str],
        target_resources: list[str],
    ) -> dict[str, Any]:
        """Deterministic safety heuristics when event loop or async brain is not available."""
        is_protected = action_type in PROTECTED_ACTION_TYPES
        risk = "HIGH" if is_protected else "LOW"
        req_confirm = is_protected
        return {
            "authorized": True,
            "overall_failure_risk": risk,
            "requires_user_confirmation": req_confirm,
            "confirmation_reason": f"Protected action {action_type} evaluated via offline security rule",
            "predicted_problems": ["Offline heuristic audit applied"] if is_protected else [],
            "corrected_hardened_steps": proposed_steps,
            "residual_risks": ["Evaluated without live LLM inference"] if is_protected else [],
        }

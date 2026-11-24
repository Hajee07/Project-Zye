"""
Host Execution Authorization Gate — Zye Day 13.
Enforces tool risk classification, mandatory Negative Pre-Mortem audit interlocks,
cryptographic approval token lifecycles, and post-execution verification.
Prevents execution bypass by Gemini or direct tool calls.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("zye.intelligence.execution_gate")

TOOL_RISK_REGISTRY: dict[str, str] = {
    # READ_ONLY (LOW)
    "get_current_mission": "READ_ONLY",
    "autonomous_identify_problems": "READ_ONLY",
    "read_recent_error_logs": "READ_ONLY",
    "get_system_info": "READ_ONLY",
    "check_microphone_health": "READ_ONLY",
    "inspect_source": "READ_ONLY",
    "inspect_source_file": "READ_ONLY",
    "list_directory": "READ_ONLY",
    "list_project_source_files": "READ_ONLY",
    "list_source_backups": "READ_ONLY",
    "read_own_source_code": "READ_ONLY",
    "browser_gmail_list_threads": "READ_ONLY",
    "get_today_calendar": "READ_ONLY",
    "get_tomorrow_calendar": "READ_ONLY",
    "find_available_calendar_slots": "READ_ONLY",
    "check_meeting_reminders": "READ_ONLY",
    "excel_analyze_dataset": "READ_ONLY",
    "compare_ai_responses": "READ_ONLY",
    "list_active_ai_plugins": "READ_ONLY",
    "list_installed_apps": "READ_ONLY",
    "search_installed_apps": "READ_ONLY",
    "inspect_app_ui": "READ_ONLY",
    "get_ui_element_details": "READ_ONLY",
    "get_application_status": "READ_ONLY",
    "list_running_processes": "READ_ONLY",
    "list_processes": "READ_ONLY",
    "find_process_by_name": "READ_ONLY",
    "get_process_details": "READ_ONLY",
    "get_system_resource_summary": "READ_ONLY",
    "verify_process_status": "READ_ONLY",
    "get_top_processes": "READ_ONLY",
    "check_process_responsiveness": "READ_ONLY",
    "get_clipboard_text": "READ_ONLY",
    "get_battery_status": "READ_ONLY",
    "list_displays": "READ_ONLY",
    "get_primary_display": "READ_ONLY",
    "list_workspaces": "READ_ONLY",
    # REVERSIBLE (MEDIUM)
    "set_mission_mode": "REVERSIBLE",
    "run_negative_premortem_brain": "REVERSIBLE",
    "compare_and_decide_solutions": "REVERSIBLE",
    "preview_patch": "REVERSIBLE",
    "preview_code_patch": "REVERSIBLE",
    "rollback_patch": "REVERSIBLE",
    "rollback_code_backup": "REVERSIBLE",
    "open_any_app": "REVERSIBLE",
    "type_into_app": "REVERSIBLE",
    "dictate_text_anywhere": "REVERSIBLE",
    "type_text": "REVERSIBLE",
    "press_key": "REVERSIBLE",
    "press_hotkey": "REVERSIBLE",
    "scroll_page": "REVERSIBLE",
    "click_ui_element": "REVERSIBLE",
    "manage_window": "REVERSIBLE",
    "close_application_window": "REVERSIBLE",
    "search_inside_application": "REVERSIBLE",
    "start_application_process": "REVERSIBLE",
    "set_brightness": "REVERSIBLE",
    "media_control": "REVERSIBLE",
    "preview_recycle_bin": "REVERSIBLE",
    "find_and_open_local_file": "REVERSIBLE",
    "capture_screenshot": "REVERSIBLE",
    "manage_calendar": "REVERSIBLE",
    "reschedule_calendar_event": "REVERSIBLE",
    "excel_set_cell_formula": "REVERSIBLE",
    "run_quick_council": "REVERSIBLE",
    "run_ai_council": "REVERSIBLE",
    # MODIFYING (HIGH)
    "patch_own_code": "MODIFYING",
    "create_file": "MODIFYING",
    "edit_file": "MODIFYING",
    "append_file": "MODIFYING",
    "create_source_backup": "MODIFYING",
    # EXTERNAL_SIDE_EFFECT (HIGH)
    "send_email": "EXTERNAL_SIDE_EFFECT",
    "http_request": "EXTERNAL_SIDE_EFFECT",
    "send_whatsapp_message": "EXTERNAL_SIDE_EFFECT",
    # DESTRUCTIVE (CRITICAL)
    "delete_file": "DESTRUCTIVE",
    "delete_directory": "DESTRUCTIVE",
    "overwrite_file": "DESTRUCTIVE",
    "purge_directory": "DESTRUCTIVE",
    # PRIVILEGED (CRITICAL)
    "execute_emergency_reflex": "PRIVILEGED",
    "cyber_lockdown": "PRIVILEGED",
    "run_system_command": "PRIVILEGED",
    "shutdown_windows": "PRIVILEGED",
    "restart_windows": "PRIVILEGED",
}

PREMORTEM_MANDATORY_CLASSES = {
    "MODIFYING",
    "EXTERNAL_SIDE_EFFECT",
    "DESTRUCTIVE",
    "PRIVILEGED",
}

CONFIRMATION_MANDATORY_CLASSES = {
    "DESTRUCTIVE",
    "EXTERNAL_SIDE_EFFECT",
    "PRIVILEGED",
}

EXEMPT_TOOLS = {
    "run_negative_premortem_brain",
    "compare_and_decide_solutions",
    "get_current_mission",
    "autonomous_identify_problems",
}

DEFAULT_APPROVAL_TTL_SECONDS = 120.0


class ZyeExecutionGate:
    """
    Host-level authorization boundary.
    Enforces risk checks, negative pre-mortem interlocks, and human approval gates.
    """

    def __init__(
        self,
        premortem_brain: Any = None,
        preflight: Any = None,
        mission_controller: Any = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self._premortem = premortem_brain
        self._preflight = preflight
        self._mission = mission_controller
        self._config = config or {}
        self._pending_approvals: dict[str, dict[str, Any]] = {}
        self._granted_approvals: dict[str, dict[str, Any]] = {}

    def classify_tool(self, tool_name: str) -> str:
        """Classify tool name into designated risk category."""
        clean = str(tool_name).strip()
        return TOOL_RISK_REGISTRY.get(clean, "MODIFYING")

    def requires_premortem(self, tool_name: str) -> bool:
        """Determine whether tool requires a pre-execution adversarial audit."""
        clean = str(tool_name).strip()
        if clean in EXEMPT_TOOLS:
            return False
        risk_class = self.classify_tool(clean)
        return risk_class in PREMORTEM_MANDATORY_CLASSES

    def requires_confirmation(self, tool_name: str) -> bool:
        """Determine whether human confirmation is mandatory for tool."""
        clean = str(tool_name).strip()
        if clean in EXEMPT_TOOLS:
            return False
        risk_class = self.classify_tool(clean)
        return risk_class in CONFIRMATION_MANDATORY_CLASSES

    def generate_approval_token(self, tool_name: str, tool_args: dict[str, Any]) -> str:
        """Generate deterministic cryptographic SHA-256 token for approval tracking."""
        raw = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}:{time.time()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def grant_approval(self, token: str, approver: str = "user") -> bool:
        """Grant human approval for a pending approval token."""
        if token in self._pending_approvals:
            record = self._pending_approvals.pop(token)
            record["approved_at"] = time.monotonic()
            record["approver"] = approver
            self._granted_approvals[token] = record
            logger.info("Human approval granted for token: %s", token)
            return True
        return False

    def is_approval_valid(
        self,
        token: str,
        expected_arg: Any = None,
        *extra_args: Any,
        expected_args: dict[str, Any] | None = None,
        expected_tool: str | None = None,
        **kwargs: Any,
    ) -> bool:
        """Check if an approval token is valid, unexpired, and matches expected tool arguments."""
        if token not in self._granted_approvals:
            return False
        record = self._granted_approvals[token]
        created_at = record.get("created_at", 0.0)
        approved_at = record.get("approved_at", created_at)
        ref_time = min(created_at, approved_at) if (created_at > 0.0 and approved_at > 0.0) else (approved_at or created_at)
        ttl = float(self._config.get("approval_ttl_seconds", DEFAULT_APPROVAL_TTL_SECONDS))
        if (time.monotonic() - ref_time) >= (ttl - 0.005):
            self._granted_approvals.pop(token, None)
            logger.warning("Approval token expired: %s", token)
            return False

        args_to_check = expected_args if expected_args is not None else (expected_arg if isinstance(expected_arg, dict) else None)
        if args_to_check is not None:
            rec_args = record.get("tool_args")
            if rec_args is not None and rec_args != args_to_check:
                logger.warning("Approval token argument mismatch for token: %s", token)
                return False

        if expected_tool is not None:
            rec_tool = record.get("tool_name")
            if rec_tool is not None and rec_tool != expected_tool:
                logger.warning("Approval token tool name mismatch for token: %s", token)
                return False

        return True

    async def evaluate(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        approval_token: str | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate tool call against execution policies:
        1. Tool risk classification
        2. Mission profile constraint check
        3. Mandatory Negative Pre-Mortem audit
        4. Human approval token requirement
        """
        clean_name = str(tool_name).strip()

        # Exempt tools pass through immediately without recursive audit
        if clean_name in EXEMPT_TOOLS:
            return {"allowed": True, "risk_class": "EXEMPT", "requires_confirmation": False}

        risk_class = self.classify_tool(clean_name)
        requires_audit = self.requires_premortem(clean_name)
        requires_confirm = self.requires_confirmation(clean_name)

        # 1. Active Mission Check
        active_mission = "NORMAL_ASSISTANT"
        if self._mission:
            try:
                m_state = self._mission.get_current_mission()
                active_mission = m_state.get("mission", "NORMAL_ASSISTANT")
                # In EMERGENCY_LOCKDOWN, all modifying and privileged operations are blocked
                if active_mission == "EMERGENCY_LOCKDOWN" and risk_class in ("MODIFYING", "DESTRUCTIVE", "PRIVILEGED"):
                    return {
                        "allowed": False,
                        "risk_class": risk_class,
                        "reason": f"Execution BLOCKED: Active mission is EMERGENCY_LOCKDOWN (Zero Trust). Tool '{clean_name}' prohibited.",
                        "requires_confirmation": True,
                    }
            except Exception as m_exc:
                logger.warning("Mission check error in execution gate: %s", m_exc)

        # 2. Mandatory Pre-Mortem Check
        audit_report = None
        if requires_audit:
            if self._premortem is None:
                return {
                    "allowed": False,
                    "risk_class": risk_class,
                    "reason": f"Execution BLOCKED: Negative Pre-Mortem Brain unavailable for protected tool '{clean_name}'. Fail-closed policy enforced.",
                    "requires_confirmation": True,
                }

            targets: list[str] = []
            for k in ["file_path", "target_path", "filename", "path", "source_file", "target"]:
                if k in tool_args and isinstance(tool_args[k], str):
                    targets.append(tool_args[k])

            pf_summary = {}
            if self._preflight:
                pf_summary = self._preflight.generate_preflight_report(targets)

            try:
                audit_report = await self._premortem.run_audit(
                    task_description=f"Invoke tool '{clean_name}' with arguments {tool_args}",
                    proposed_steps=[f"Execute {clean_name}"],
                    targets=targets,
                    preflight_summary=pf_summary,
                    mission=active_mission,
                )
            except Exception as a_exc:
                return {
                    "allowed": False,
                    "risk_class": risk_class,
                    "reason": f"Execution BLOCKED: Negative Pre-Mortem audit failed ({a_exc}). Protected tool '{clean_name}' fail-closed.",
                    "requires_confirmation": True,
                }

            # Check if audit flagged mandatory confirmation
            if audit_report.get("requires_user_confirmation", False):
                requires_confirm = True

        # 3. Confirmation Token Gate
        if requires_confirm:
            if not approval_token or not self.is_approval_valid(approval_token, expected_args=tool_args, expected_tool=clean_name):
                token = self.generate_approval_token(clean_name, tool_args)
                self._pending_approvals[token] = {
                    "tool_name": clean_name,
                    "tool_args": tool_args,
                    "created_at": time.monotonic(),
                    "risk_class": risk_class,
                    "audit_report": audit_report,
                }
                audit_risk = (audit_report or {}).get("overall_failure_risk", "")
                reason_suffix = f" (Audit risk: {audit_risk})" if audit_risk else ""
                return {
                    "allowed": False,
                    "risk_class": risk_class,
                    "reason": f"Execution BLOCKED: Tool '{clean_name}' ({risk_class}) requires explicit human confirmation.{reason_suffix}",
                    "approval_token": token,
                    "requires_confirmation": True,
                    "audit_report": audit_report,
                }
            else:
                # Consume approval token so it cannot be reused
                self._granted_approvals.pop(approval_token, None)

        return {
            "allowed": True,
            "risk_class": risk_class,
            "requires_confirmation": False,
            "audit_report": audit_report,
        }

    def verify_post_execution(self, tool_name: str, result: Any) -> dict[str, Any]:
        """Inspect and verify post-execution tool results adhering to Zero False Success."""
        clean = str(tool_name).strip()
        status = "SUCCESS"
        is_error = False

        if result is None or (isinstance(result, dict) and len(result) == 0):
            # Empty dictionary or None result is unverified failure
            status = "FAILED"
            is_error = True
        elif isinstance(result, (list, tuple)):
            # Lists and tuples returned by query/enumeration tools
            status = "SUCCESS"
            is_error = False
        elif isinstance(result, dict):
            status_val = str(result.get("status", "")).upper()
            verified_flag = result.get("verified", None)
            if (
                status_val in (
                    "ERROR", "FAILED", "REJECTED", "LAUNCH_FAILED", "APP_NOT_FOUND",
                    "WINDOW_TIMEOUT", "OUTCOME_UNKNOWN", "TIMEOUT", "CANCELLED",
                    "NO_DISPATCHER", "UNKNOWN", "BLOCKED_BY_SAFETY_AUDIT",
                    "BLOCKED_BY_EXECUTION_GATE", "BLOCKED_BY_SECURITY_POLICY"
                )
                or verified_flag is False
                or bool(result.get("error"))
            ):
                status = "FAILED"
                is_error = True
            elif status_val in ("PROCESS_STARTED", "UNVERIFIED") and verified_flag is not True:
                status = "UNVERIFIED"
                is_error = True
            elif verified_flag is not True and status_val not in ("SUCCESS", "OK"):
                is_query = clean.startswith((
                    "get_", "list_", "read_", "inspect_", "check_", "search_", "find_",
                    "profile_", "analyze_", "calculate_", "solve_", "compare_", "verify_",
                    "ask_", "detect_", "aggregate_", "fetch_", "extract_"
                )) or any(k in result for k in ("count", "items", "data", "windows", "apps", "processes", "result", "text", "content"))
                if is_query:
                    status = "SUCCESS"
                    is_error = False
                else:
                    status = "FAILED"
                    is_error = True
        elif isinstance(result, (str, int, float, bool)):
            if isinstance(result, bool):
                status = "SUCCESS" if result else "FAILED"
                is_error = not result
            else:
                status = "SUCCESS"
                is_error = False
        else:
            status = "FAILED"
            is_error = True

        logger.info("Post-execution verification for '%s': status=%s", clean, status)
        return {
            "tool_name": clean,
            "verification_status": status,
            "verified": not is_error,
            "error_detected": is_error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

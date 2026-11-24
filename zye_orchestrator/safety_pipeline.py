"""
Safety Execution Gateway & Pipeline for Zye Master MCP Orchestrator (Day 15).
Enforces mandatory 100% Negative Pre-Mortem Brain audit on protected operations,
cryptographically bound approval tokens, permission checks, and post-execution verification.
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

from zye_autonomy.audit_logger import AuditLogger

logger = logging.getLogger("zye.orchestrator.safety_pipeline")


class RiskLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL_RISK = "CRITICAL_RISK"


# Canonical tool risk mappings
DEFAULT_TOOL_RISK_MAP: dict[str, RiskLevel] = {
    # READ_ONLY
    "get_current_mission": RiskLevel.READ_ONLY,
    "autonomous_identify_problems": RiskLevel.READ_ONLY,
    "read_recent_error_logs": RiskLevel.READ_ONLY,
    "get_system_info": RiskLevel.READ_ONLY,
    "check_microphone_health": RiskLevel.READ_ONLY,
    "inspect_source": RiskLevel.READ_ONLY,
    "inspect_source_file": RiskLevel.READ_ONLY,
    "list_directory": RiskLevel.READ_ONLY,
    "list_project_source_files": RiskLevel.READ_ONLY,
    "list_source_backups": RiskLevel.READ_ONLY,
    "read_own_source_code": RiskLevel.READ_ONLY,
    "check_meeting_reminders": RiskLevel.READ_ONLY,
    "conduct_information_research": RiskLevel.READ_ONLY,
    "inspect_app_ui": RiskLevel.READ_ONLY,
    "get_battery_status": RiskLevel.READ_ONLY,
    "get_clipboard_text": RiskLevel.READ_ONLY,
    "find_and_open_local_file": RiskLevel.READ_ONLY,
    "get_whatsapp_call_status": RiskLevel.READ_ONLY,
    "search_whatsapp_contact": RiskLevel.READ_ONLY,
    "preview_recycle_bin": RiskLevel.READ_ONLY,
    "list_running_processes": RiskLevel.READ_ONLY,
    "get_process_details": RiskLevel.READ_ONLY,
    "get_top_processes": RiskLevel.READ_ONLY,
    "check_process_responsiveness": RiskLevel.READ_ONLY,
    "get_process_tree": RiskLevel.READ_ONLY,
    "get_system_resource_snapshot": RiskLevel.READ_ONLY,
    "get_application_health": RiskLevel.READ_ONLY,
    "validate_source_syntax": RiskLevel.READ_ONLY,
    "verify_backup_payload": RiskLevel.READ_ONLY,
    "read_telemetry_errors": RiskLevel.READ_ONLY,
    # Day 18 Read-Only Tools
    "list_open_windows": RiskLevel.READ_ONLY,
    "find_window": RiskLevel.READ_ONLY,
    "get_active_window": RiskLevel.READ_ONLY,
    "get_connected_displays": RiskLevel.READ_ONLY,
    "get_virtual_desktops": RiskLevel.READ_ONLY,
    "get_clipboard_metadata": RiskLevel.READ_ONLY,
    "search_local_files": RiskLevel.READ_ONLY,
    "get_file_details": RiskLevel.READ_ONLY,
    "get_active_media_session": RiskLevel.READ_ONLY,
    "get_media_session_details": RiskLevel.READ_ONLY,
    "list_screenshots": RiskLevel.READ_ONLY,
    # Day 19 Read-Only Tools
    "list_processes": RiskLevel.READ_ONLY,
    "find_process_by_name": RiskLevel.READ_ONLY,
    "get_system_resource_summary": RiskLevel.READ_ONLY,
    "verify_process_status": RiskLevel.READ_ONLY,
    "list_installed_apps": RiskLevel.READ_ONLY,
    "search_installed_apps": RiskLevel.READ_ONLY,
    "get_ui_element_details": RiskLevel.READ_ONLY,
    "get_application_status": RiskLevel.READ_ONLY,
    # Day 20 Read-Only Tools
    "office_get_session_details": RiskLevel.READ_ONLY,
    "office_list_sessions": RiskLevel.READ_ONLY,
    "office_inspect_document": RiskLevel.READ_ONLY,
    "office_health_check": RiskLevel.READ_ONLY,
    "office_check_installation": RiskLevel.READ_ONLY,
    "office_list_capabilities": RiskLevel.READ_ONLY,
    "office_list_operations": RiskLevel.READ_ONLY,
    # Day 21 Read-Only Tools
    "word_inspect_document": RiskLevel.READ_ONLY,
    "word_get_document_metadata": RiskLevel.READ_ONLY,
    "word_get_track_changes_status": RiskLevel.READ_ONLY,
    "word_get_revisions": RiskLevel.READ_ONLY,
    "word_get_comments": RiskLevel.READ_ONLY,
    "word_inspect_mail_merge": RiskLevel.READ_ONLY,
    "word_get_statistics": RiskLevel.READ_ONLY,
    "word_inspect_accessibility": RiskLevel.READ_ONLY,
    "word_generate_accessibility_report": RiskLevel.READ_ONLY,
    # LOW_RISK
    "generate_daily_report": RiskLevel.LOW_RISK,
    "analyze_business_data": RiskLevel.LOW_RISK,
    "plan_travel_itinerary": RiskLevel.LOW_RISK,
    "open_any_app": RiskLevel.LOW_RISK,
    "open_whatsapp_chat": RiskLevel.LOW_RISK,
    "capture_screenshot": RiskLevel.LOW_RISK,
    "capture_active_window": RiskLevel.LOW_RISK,
    "launch_application": RiskLevel.LOW_RISK,
    "switch_virtual_desktop": RiskLevel.LOW_RISK,
    "create_virtual_desktop": RiskLevel.LOW_RISK,
    "move_window_to_monitor": RiskLevel.LOW_RISK,
    "move_window": RiskLevel.LOW_RISK,
    "resize_window": RiskLevel.LOW_RISK,
    "center_window": RiskLevel.LOW_RISK,
    "search_inside_application": RiskLevel.LOW_RISK,
    # Day 20 Low-Risk Tools
    "office_connect": RiskLevel.LOW_RISK,
    "office_disconnect": RiskLevel.LOW_RISK,
    "office_execute_operation": RiskLevel.LOW_RISK,
    "office_export_pdf": RiskLevel.LOW_RISK,
    "office_accelerate_ribbon": RiskLevel.LOW_RISK,
    # Day 21 Low-Risk Tools
    "word_create_document": RiskLevel.LOW_RISK,
    "word_open_document": RiskLevel.LOW_RISK,
    "word_save_document": RiskLevel.LOW_RISK,
    "word_insert_text": RiskLevel.LOW_RISK,
    "word_format_text": RiskLevel.LOW_RISK,
    "word_format_paragraph": RiskLevel.LOW_RISK,
    "word_apply_style": RiskLevel.LOW_RISK,
    "word_set_document_properties": RiskLevel.LOW_RISK,
    "word_create_bookmark": RiskLevel.LOW_RISK,
    "word_insert_hyperlink": RiskLevel.LOW_RISK,
    "word_set_track_changes": RiskLevel.LOW_RISK,
    "word_add_comment": RiskLevel.LOW_RISK,
    "word_resolve_comment": RiskLevel.LOW_RISK,
    "word_create_bullet_list": RiskLevel.LOW_RISK,
    "word_create_numbered_list": RiskLevel.LOW_RISK,
    # MEDIUM_RISK
    "close_application_window": RiskLevel.MEDIUM_RISK,
    "start_application_process": RiskLevel.MEDIUM_RISK,
    # MEDIUM_RISK
    "set_mission_mode": RiskLevel.MEDIUM_RISK,
    "run_negative_premortem_brain": RiskLevel.MEDIUM_RISK,
    "compare_and_decide_solutions": RiskLevel.MEDIUM_RISK,
    "preview_patch": RiskLevel.MEDIUM_RISK,
    "preview_code_patch": RiskLevel.MEDIUM_RISK,
    "rollback_patch": RiskLevel.MEDIUM_RISK,
    "rollback_code_backup": RiskLevel.MEDIUM_RISK,
    "rollback_to_backup": RiskLevel.MEDIUM_RISK,
    "rollback_to_latest": RiskLevel.MEDIUM_RISK,
    "close_application_gracefully": RiskLevel.MEDIUM_RISK,
    "restart_application": RiskLevel.MEDIUM_RISK,
    "request_process_termination": RiskLevel.MEDIUM_RISK,
    "manage_project_support": RiskLevel.MEDIUM_RISK,
    "schedule_and_timeblock_tasks": RiskLevel.MEDIUM_RISK,
    "set_brightness": RiskLevel.MEDIUM_RISK,
    "control_volume": RiskLevel.MEDIUM_RISK,
    "set_volume_percent": RiskLevel.MEDIUM_RISK,
    "media_control": RiskLevel.MEDIUM_RISK,
    "manage_window": RiskLevel.MEDIUM_RISK,
    "scroll_page": RiskLevel.MEDIUM_RISK,
    "click_ui_element": RiskLevel.MEDIUM_RISK,
    "type_into_app": RiskLevel.MEDIUM_RISK,
    "dictate_text_anywhere": RiskLevel.MEDIUM_RISK,
    "compose_whatsapp_message": RiskLevel.MEDIUM_RISK,
    "press_hotkey": RiskLevel.MEDIUM_RISK,
    "execute_shortcut": RiskLevel.MEDIUM_RISK,
    # Day 21 Medium-Risk Tools
    "word_save_document_as": RiskLevel.MEDIUM_RISK,
    "word_close_document": RiskLevel.MEDIUM_RISK,
    "word_create_table": RiskLevel.MEDIUM_RISK,
    "word_populate_table": RiskLevel.MEDIUM_RISK,
    "word_format_table": RiskLevel.MEDIUM_RISK,
    "word_add_table_row": RiskLevel.MEDIUM_RISK,
    "word_delete_table_row": RiskLevel.MEDIUM_RISK,
    "word_set_header": RiskLevel.MEDIUM_RISK,
    "word_set_footer": RiskLevel.MEDIUM_RISK,
    "word_insert_page_numbers": RiskLevel.MEDIUM_RISK,
    "word_set_first_page_header": RiskLevel.MEDIUM_RISK,
    "word_set_page_orientation": RiskLevel.MEDIUM_RISK,
    "word_set_page_margins": RiskLevel.MEDIUM_RISK,
    "word_set_paper_size": RiskLevel.MEDIUM_RISK,
    "word_insert_page_break": RiskLevel.MEDIUM_RISK,
    "word_insert_section_break": RiskLevel.MEDIUM_RISK,
    "word_insert_toc": RiskLevel.MEDIUM_RISK,
    "word_update_toc": RiskLevel.MEDIUM_RISK,
    "word_accept_revision": RiskLevel.MEDIUM_RISK,
    "word_reject_revision": RiskLevel.MEDIUM_RISK,
    "word_connect_merge_source": RiskLevel.MEDIUM_RISK,
    "word_export_pdf_advanced": RiskLevel.MEDIUM_RISK,
    "word_create_custom_style": RiskLevel.MEDIUM_RISK,
    # HIGH_RISK
    "patch_own_code": RiskLevel.HIGH_RISK,
    "apply_code_patch": RiskLevel.HIGH_RISK,
    "apply_patch": RiskLevel.HIGH_RISK,
    "create_file": RiskLevel.HIGH_RISK,
    "edit_file": RiskLevel.HIGH_RISK,
    "append_file": RiskLevel.HIGH_RISK,
    "create_source_backup": RiskLevel.HIGH_RISK,
    "manage_documents": RiskLevel.HIGH_RISK,
    "manage_emails": RiskLevel.HIGH_RISK,
    "send_email": RiskLevel.HIGH_RISK,
    "http_request": RiskLevel.HIGH_RISK,
    "send_whatsapp_message": RiskLevel.HIGH_RISK,
    "start_whatsapp_voice_call": RiskLevel.HIGH_RISK,
    "start_whatsapp_video_call": RiskLevel.HIGH_RISK,
    "end_whatsapp_call": RiskLevel.HIGH_RISK,
    "set_clipboard_text": RiskLevel.HIGH_RISK,
    "clear_clipboard": RiskLevel.HIGH_RISK,
    "delete_screenshot": RiskLevel.HIGH_RISK,
    # Day 21 High-Risk Tools (Require Explicit Confirmation)
    "word_delete_selected_text": RiskLevel.HIGH_RISK,
    "word_replace_text": RiskLevel.HIGH_RISK,
    "word_accept_all_revisions": RiskLevel.HIGH_RISK,
    "word_reject_all_revisions": RiskLevel.HIGH_RISK,
    "word_execute_mail_merge": RiskLevel.HIGH_RISK,
    # CRITICAL_RISK
    "word_run_vba_macro": RiskLevel.CRITICAL_RISK,
    "word_execute_arbitrary_script": RiskLevel.CRITICAL_RISK,
    "delete_file": RiskLevel.CRITICAL_RISK,
    "delete_directory": RiskLevel.CRITICAL_RISK,
    "overwrite_file": RiskLevel.CRITICAL_RISK,
    "purge_directory": RiskLevel.CRITICAL_RISK,
    "execute_emergency_reflex": RiskLevel.CRITICAL_RISK,
    "cyber_lockdown": RiskLevel.CRITICAL_RISK,
    "run_system_command": RiskLevel.CRITICAL_RISK,
    "shutdown_windows": RiskLevel.CRITICAL_RISK,
    "restart_windows": RiskLevel.CRITICAL_RISK,
    "power_action": RiskLevel.CRITICAL_RISK,
    "empty_recycle_bin": RiskLevel.CRITICAL_RISK,
    "terminate_process": RiskLevel.CRITICAL_RISK,
}

TOOL_RISK_MAP = DEFAULT_TOOL_RISK_MAP

PROTECTED_RISK_LEVELS = {
    RiskLevel.HIGH_RISK,
    RiskLevel.CRITICAL_RISK,
}

CONFIRMATION_RISK_LEVELS = {
    RiskLevel.HIGH_RISK,
    RiskLevel.CRITICAL_RISK,
}


def compute_approval_fingerprint(
    action: str,
    target_resources: list[str],
    parameters: dict[str, Any],
) -> str:
    """Generate deterministic fingerprint of action, targets, and parameters."""
    raw = f"{action}::{sorted(target_resources)}::{json.dumps(parameters, sort_keys=True)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class SafetyExecutionGateway:
    """
    Mandatory Execution Safety Gateway.
    No protected file-modifying or system action executes without Negative Brain audit.
    """

    def __init__(
        self,
        premortem_brain: Any = None,
        preflight: Any = None,
        mission_controller: Any = None,
        audit_logger: Optional[AuditLogger] = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self._premortem = premortem_brain
        self._preflight = preflight
        self._mission_controller = mission_controller
        self._audit = audit_logger or AuditLogger()
        self._cfg = config or {}
        self._approvals: dict[str, dict[str, Any]] = {}
        self._ttl_seconds = float(self._cfg.get("approval_ttl_seconds", 120.0))

    def classify_risk(self, tool_name: str, action: str = "") -> RiskLevel:
        """Classify tool or action into standard 5-level risk classification."""
        norm_tool = tool_name.strip()
        if norm_tool in DEFAULT_TOOL_RISK_MAP:
            return DEFAULT_TOOL_RISK_MAP[norm_tool]

        # Check action parameter if present
        clean_act = action.strip().lower()
        if clean_act in ("delete", "overwrite", "purge", "destroy"):
            return RiskLevel.CRITICAL_RISK
        if clean_act in ("send", "modify", "organize", "update", "patch"):
            return RiskLevel.HIGH_RISK
        if clean_act in ("add", "create", "set", "schedule"):
            return RiskLevel.MEDIUM_RISK
        if clean_act in ("generate", "plan", "analyze"):
            return RiskLevel.LOW_RISK

        # Heuristic name checks
        if any(w in norm_tool for w in ("delete", "shutdown", "destroy", "purge", "emergency")):
            return RiskLevel.CRITICAL_RISK
        if any(w in norm_tool for w in ("patch", "modify", "write", "send", "edit", "append")):
            return RiskLevel.HIGH_RISK
        if any(w in norm_tool for w in ("set", "create", "add", "timeblock")):
            return RiskLevel.MEDIUM_RISK
        if any(w in norm_tool for w in ("read", "list", "get", "inspect", "check", "search")):
            return RiskLevel.READ_ONLY

        return RiskLevel.MEDIUM_RISK

    def generate_approval_token(
        self,
        audit_id: str,
        action: str,
        target_resources: list[str],
        parameters: dict[str, Any],
    ) -> str:
        """Issue time-bounded cryptographic approval token bound to exact action, targets, and args."""
        fp = compute_approval_fingerprint(action, target_resources, parameters)
        token = f"tok_{audit_id}_{fp}"
        self._approvals[token] = {
            "audit_id": audit_id,
            "action": action,
            "target_resources": list(target_resources),
            "parameters": parameters,
            "fingerprint": fp,
            "issued_at": time.time(),
            "expires_at": time.time() + self._ttl_seconds,
            "user_confirmed": False,
        }
        return token

    def confirm_approval_token(self, token: str) -> bool:
        """Record explicit user confirmation for an active token."""
        entry = self._approvals.get(token)
        if not entry:
            return False
        if time.time() > entry["expires_at"]:
            del self._approvals[token]
            return False
        entry["user_confirmed"] = True
        return True

    def validate_approval_token(
        self,
        token: str,
        action: str,
        target_resources: list[str],
        parameters: dict[str, Any],
    ) -> tuple[bool, str]:
        """Validate token validity, expiration, and parameter binding."""
        entry = self._approvals.get(token)
        if not entry:
            return False, "Approval token not found or revoked."
        if time.time() > entry["expires_at"]:
            del self._approvals[token]
            return False, "Approval token has expired."
        if not entry.get("user_confirmed", False):
            return False, "Approval token has not been confirmed by user."

        curr_fp = compute_approval_fingerprint(action, target_resources, parameters)
        if curr_fp != entry.get("fingerprint"):
            return False, "Parameters or target resources modified after approval (Parameter Tampering Protection)."

        return True, "Valid"

    async def authorize_and_execute(
        self,
        task_description: str,
        action_type: str,
        target_resources: list[str],
        tool_name: str,
        tool_args: dict[str, Any],
        executor_fn: Callable[..., Any],
        user_confirmed: bool = False,
        approval_token: str = "",
    ) -> dict[str, Any]:
        """
        Complete 15-step safety execution pipeline.
        Enforces Negative Pre-Mortem Brain audit before any protected action.
        """
        # Step 01 & 02: Identify requested action and risk level
        risk_level = self.classify_risk(tool_name, action=action_type)
        is_protected = risk_level in PROTECTED_RISK_LEVELS

        # Step 03: Resources
        targets = list(target_resources) or [str(tool_args.get("path") or tool_args.get("file_path") or tool_name)]

        # Step 04: Live Preflight Inspection
        preflight_summary: dict[str, Any] = {}
        if self._preflight is not None:
            try:
                preflight_summary = self._preflight.generate_preflight_report(targets)
            except Exception as e:
                logger.warning("Preflight inspection error: %s", e)

        # Step 05: Run Negative Pre-Mortem Brain if protected
        predicted_problems: list[str] = []
        broken_assumptions: list[str] = []
        hardened_steps: list[str] = []
        requires_user_confirmation = risk_level in CONFIRMATION_RISK_LEVELS
        audit_id = f"aud_{hashlib.sha256(f'{tool_name}:{time.time()}'.encode()).hexdigest()[:10]}"

        if is_protected:
            if self._premortem is None:
                # Failure policy: block protected side-effecting operations if Brain unavailable
                err_msg = "Negative Pre-Mortem Brain unavailable. Protected operation BLOCKED by Safety Gateway."
                self._audit.log_event(
                    tool_name=tool_name,
                    action_type=action_type,
                    risk_level=risk_level.value,
                    target_resources=",".join(targets),
                    authorized=False,
                    result_status="BLOCKED_PREMORTEM_UNAVAILABLE",
                    details=err_msg,
                )
                return {
                    "status": "BLOCKED",
                    "code": "PREMORTEM_BRAIN_UNAVAILABLE",
                    "tool_name": tool_name,
                    "risk_level": risk_level.value,
                    "message": err_msg,
                }

            # Run Brain audit
            try:
                current_mission = "NORMAL_ASSISTANT"
                if self._mission_controller:
                    current_mission = self._mission_controller.get_current_mission().get("mission", "NORMAL_ASSISTANT")

                proposed = [f"Execute tool '{tool_name}' with args {json.dumps(tool_args)}"]
                audit_rep = await self._premortem.run_audit(
                    task_description=task_description or f"Execute {tool_name}",
                    proposed_steps=proposed,
                    targets=targets,
                    preflight_summary=preflight_summary,
                    mission=current_mission,
                )
                predicted_problems = audit_rep.get("predicted_problems", [])
                broken_assumptions = audit_rep.get("hidden_assumptions_broken", [])
                hardened_steps = audit_rep.get("corrected_hardened_steps", [])
                if audit_rep.get("requires_user_confirmation", False):
                    requires_user_confirmation = True

            except Exception as b_exc:
                logger.error("Pre-Mortem Brain execution error: %s", b_exc)
                return {
                    "status": "BLOCKED",
                    "code": "PREMORTEM_AUDIT_FAILED",
                    "tool_name": tool_name,
                    "message": f"Pre-mortem audit failed: {b_exc}",
                }

        # Step 09 & 10: Determine confirmation requirement
        if requires_user_confirmation and not user_confirmed:
            # Issue approval token and require confirmation
            token = self.generate_approval_token(audit_id, action_type, targets, tool_args)
            self._audit.log_event(
                tool_name=tool_name,
                action_type=action_type,
                risk_level=risk_level.value,
                target_resources=",".join(targets),
                authorized=False,
                result_status="CONFIRMATION_REQUIRED",
                details={"token": token, "predicted_problems": predicted_problems},
            )
            return {
                "status": "CONFIRMATION_REQUIRED",
                "tool_name": tool_name,
                "risk_level": risk_level.value,
                "approval_token": token,
                "predicted_problems": predicted_problems,
                "broken_assumptions": broken_assumptions,
                "hardened_steps": hardened_steps,
                "message": f"Action '{tool_name}' is classified as {risk_level.value} and requires user confirmation.",
            }

        # Step 12: Validate token if provided
        if approval_token:
            is_valid, reason = self.validate_approval_token(approval_token, action_type, targets, tool_args)
            if not is_valid:
                return {
                    "status": "BLOCKED",
                    "code": "INVALID_APPROVAL_TOKEN",
                    "message": f"Authorization denied: {reason}",
                }

        # Step 13: Execute only the authorized plan
        exec_start = time.time()
        try:
            if inspect.iscoroutinefunction(executor_fn):
                result = await executor_fn(**tool_args)
            else:
                result = executor_fn(**tool_args)

            # Step 14: Verify result
            verification = "VERIFIED_SUCCESS" if result is not None else "VERIFIED_EMPTY"

            # Step 15: Record audit trail
            self._audit.log_event(
                tool_name=tool_name,
                action_type=action_type,
                risk_level=risk_level.value,
                target_resources=",".join(targets),
                authorized=True,
                result_status="SUCCESS",
                verification_result=verification,
                details={"latency_ms": round((time.time() - exec_start) * 1000, 2)},
            )
            return {
                "status": "SUCCESS",
                "tool_name": tool_name,
                "data": result,
                "risk_level": risk_level.value,
                "hardened_steps_applied": len(hardened_steps) > 0,
            }

        except Exception as exec_err:
            logger.error("Tool execution error: %s", exec_err)
            self._audit.log_event(
                tool_name=tool_name,
                action_type=action_type,
                risk_level=risk_level.value,
                target_resources=",".join(targets),
                authorized=True,
                result_status="EXECUTION_FAILED",
                verification_result="FAILED",
                error_category=type(exec_err).__name__,
                details=str(exec_err),
            )
            return {
                "status": "ERROR",
                "tool_name": tool_name,
                "error": str(exec_err),
            }

"""
ZYE Master MCP Autonomous Decision Server — Day 13.
Exposes 6 autonomous tools:
  1. run_negative_premortem_brain
  2. compare_and_decide_solutions
  3. set_mission_mode
  4. get_current_mission
  5. autonomous_identify_problems
  6. execute_emergency_reflex
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

from zye_guard import zye_safe_skill

# Load environment
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zye.autonomous_decision_mcp")

# Initialize FastMCP Server (compatible with mcp 1.x, 2.x, or fallback shim)
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
    _MCP_AVAILABLE = True
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[no-redef]
        _MCP_AVAILABLE = True
    except ImportError:
        _MCP_AVAILABLE = False

        class FastMCP:  # type: ignore[no-redef]
            def __init__(self, name: str, **kwargs: Any) -> None:
                self.name = name
                self._tools: dict[str, Any] = {}

            def tool(self, *args: Any, **kwargs: Any) -> Any:
                def decorator(func: Any) -> Any:
                    self._tools[func.__name__] = func
                    return func
                if args and callable(args[0]):
                    return decorator(args[0])
                return decorator

            def run(self, transport: str = "stdio") -> None:
                pass

            async def list_tools(self) -> list[Any]:
                class _Stub:
                    def __init__(self, n: str):
                        self.name = n
                return [_Stub(n) for n in self._tools]

mcp = FastMCP("ZyeAutonomousBrain")

# --- Lazy Subsystem Singletons ---
_mission_controller = None
_preflight = None
_premortem_brain = None
_decision_matrix = None
_emergency_reflex = None
_gemini_client = None


def _get_mission_controller():
    global _mission_controller
    if _mission_controller is None:
        from zye_intelligence.mission_controller import ZyeMissionController

        _mission_controller = ZyeMissionController()
    return _mission_controller


def _get_preflight():
    global _preflight
    if _preflight is None:
        from zye_intelligence.preflight import ZyeSystemPreflight

        _preflight = ZyeSystemPreflight()
    return _preflight


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        try:
            from gemini_gateway import ZyeGeminiGateway
            gw = ZyeGeminiGateway.get_instance()
            _gemini_client = gw.key_manager.get_client(3) or gw.key_manager.get_client(1)
        except Exception:
            _gemini_client = None

    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY_03", os.getenv("GEMINI_API_KEY", "")).strip()
        if api_key and not api_key.startswith("YOUR_") and not api_key.startswith("AIzaSyDummy") and not api_key.startswith("placeholder"):
            try:
                from google import genai

                _gemini_client = genai.Client(api_key=api_key)
            except Exception as exc:
                logger.warning("Failed to initialize Google GenAI Client: %s", exc)
                _gemini_client = None
    return _gemini_client


def _get_premortem_brain():
    global _premortem_brain
    if _premortem_brain is None:
        from zye_intelligence.premortem import ZyeNegativePreMortem

        client = _get_gemini_client()
        _premortem_brain = ZyeNegativePreMortem(gemini_client=client)
    return _premortem_brain


def _get_decision_matrix():
    global _decision_matrix
    if _decision_matrix is None:
        from zye_intelligence.decision_matrix import ZyeDecisionMatrix

        _decision_matrix = ZyeDecisionMatrix()
    return _decision_matrix


def _get_emergency_reflex():
    global _emergency_reflex
    if _emergency_reflex is None:
        from zye_intelligence.emergency_reflex import ZyeEmergencyReflex

        config = {
            "cyber_lockdown_enabled": os.getenv("ZYE_CYBER_LOCKDOWN_ENABLED", "false").lower() == "true",
            "brightness_target": int(os.getenv("ZYE_EMERGENCY_BRIGHTNESS", "15")),
        }
        _emergency_reflex = ZyeEmergencyReflex(
            mission_controller=_get_mission_controller(), config=config
        )
    return _emergency_reflex


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 1: run_negative_premortem_brain
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
@zye_safe_skill(max_retries=1)
async def run_negative_premortem_brain(
    task_description: str,
    proposed_steps: list[str],
    target_files_or_paths: list[str] | None = None,
) -> str:
    """
    Run 100% Negative Pre-Mortem Brain on a proposed task to challenge assumptions,
    identify failure modes (FMEA), assess live system telemetry, and produce hardened steps.
    Returns structured NegativeAuditReport JSON.
    """
    try:
        pf = _get_preflight()
        preflight_summary = pf.generate_preflight_report(target_files_or_paths or [])
        mission_state = _get_mission_controller().get_current_mission()
        current_mission = mission_state.get("mission", "NORMAL_ASSISTANT")

        brain = _get_premortem_brain()
        report = await brain.run_audit(
            task_description=task_description,
            proposed_steps=proposed_steps,
            targets=target_files_or_paths,
            preflight_summary=preflight_summary,
            mission=current_mission,
        )
        return json.dumps(report, indent=2)
    except Exception as exc:
        logger.error("run_negative_premortem_brain tool error: %s", exc)
        return json.dumps({
            "status": "FAILED",
            "error": str(exc),
            "overall_failure_risk": "HIGH",
            "requires_user_confirmation": True,
            "confirmation_reason": f"Audit failed: {exc}",
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        }, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 2: compare_and_decide_solutions
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
@zye_safe_skill()
def compare_and_decide_solutions(
    problem_statement: str,
    candidate_solutions: list[dict],
    priority_mode: str = "balanced",
) -> str:
    """
    Evaluate 2-4 candidate solutions against weighted criteria:
    Reliability, Speed, Safety, Simplicity.
    priority_mode: 'balanced' | 'speed_critical' | 'maximum_safety' | 'low_resource'.
    Each candidate must include: name, description, reliability(1-10), speed(1-10), safety(1-10), simplicity(1-10).
    Returns DecisionResult JSON with ranked alternatives, tradeoffs, and safety overrides.
    """
    try:
        dm = _get_decision_matrix()
        result = dm.compare_solutions(
            problem_statement=problem_statement,
            candidate_solutions=candidate_solutions,
            priority_mode=priority_mode,
        )
        return json.dumps(result, indent=2)
    except Exception as exc:
        logger.error("compare_and_decide_solutions tool error: %s", exc)
        return json.dumps({
            "status": "FAILED",
            "error": str(exc),
            "problem": problem_statement,
        }, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 3: set_mission_mode
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
@zye_safe_skill()
def set_mission_mode(mission_name: str, custom_objective: str = "") -> str:
    """
    Set active mission profile.
    Supported: NORMAL_ASSISTANT | DEEP_ENGINEERING | STEALTH_BATTERY_SAVER | TACTICAL_REALTIME | EMERGENCY_LOCKDOWN.
    Persists atomically to zye_mission_state.json.
    """
    try:
        mc = _get_mission_controller()
        new_state = mc.set_mission(mission_name=mission_name, custom_objective=custom_objective)
        return json.dumps({"status": "SUCCESS", "mission_state": new_state}, indent=2)
    except Exception as exc:
        logger.error("set_mission_mode tool error: %s", exc)
        return json.dumps({"status": "FAILED", "error": str(exc)}, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 4: get_current_mission
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
@zye_safe_skill()
def get_current_mission() -> str:
    """
    Query active mission profile, risk tolerance, resource budget, and policy rules.
    Returns MissionState JSON.
    """
    try:
        mc = _get_mission_controller()
        state = mc.get_current_mission()
        return json.dumps(state, indent=2)
    except Exception as exc:
        logger.error("get_current_mission tool error: %s", exc)
        return json.dumps({
            "mission": "NORMAL_ASSISTANT",
            "risk_tolerance": "MODERATE",
            "resource_budget": "BALANCED",
            "error": str(exc),
        }, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 5: autonomous_identify_problems
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
@zye_safe_skill()
async def autonomous_identify_problems() -> str:
    """
    Proactively inspect system health (RAM >= 88%, Disk >= 92%, Battery <= 15%/8%, error logs).
    Returns list of detected problems with severity, recommendations, and process telemetry.
    """
    try:
        from zye_intelligence.autonomous_watchdog import _scan_emerging_problems_sync

        scan_res = _scan_emerging_problems_sync(mission_controller=_get_mission_controller())
        detected = scan_res.get("detected_problems", [])
        scan_res["problems"] = detected
        scan_res["problems_detected"] = len(detected) > 0
        return json.dumps(scan_res, indent=2)
    except Exception as exc:
        logger.error("autonomous_identify_problems tool error: %s", exc)
        return json.dumps({
            "status": "ERROR",
            "detected_problems": [],
            "telemetry": {},
            "scan_timestamp": datetime.now(timezone.utc).isoformat(),
            "active_mission": "NORMAL_ASSISTANT",
            "error": str(exc),
        }, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 6: execute_emergency_reflex
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
@zye_safe_skill()
async def execute_emergency_reflex(emergency_type: str) -> str:
    """
    Execute a predefined emergency reflex under verified policy constraints.
    Supported types: 'battery_critical' | 'ram_overload_relief' | 'cyber_lockdown'.
    Only hardcoded, allowlisted system commands are executed; arbitrary commands are rejected.
    """
    try:
        reflex = _get_emergency_reflex()
        result = await reflex.execute(emergency_type=emergency_type)
        return json.dumps(result, indent=2)
    except Exception as exc:
        logger.error("execute_emergency_reflex tool error: %s", exc)
        return json.dumps({
            "emergency_handled": emergency_type,
            "actions_proposed": [],
            "actions_executed": [],
            "rapid_actions_executed": [],
            "verification_results": [],
            "action_verification": [],
            "failed_actions": [str(exc)],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "ERROR",
        }, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")

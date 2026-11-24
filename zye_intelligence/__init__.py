"""
ZYE Intelligence Package — Day 13 Autonomous Intelligence Engine.
Core components:
  - 100% Negative Pre-Mortem Brain & Adversarial FMEA
  - Real-time System Preflight Diagnostics
  - Multi-Solution Weighted Decision Matrix
  - Dynamic Mission Controller & Persistence
  - Autonomous Problem Detection & Zero-Prompt Watchdog
  - Bounded Emergency Reflex Controller
  - Host Execution Authorization Gate
"""

from zye_intelligence.schemas import (
    NegativeAuditReport,
    SolutionCandidate,
    DecisionResult,
    MissionState,
    WatchdogProblem,
    EmergencyResult,
)
from zye_intelligence.preflight import (
    ZyeSystemPreflight,
    _preflight_system_check,
)
from zye_intelligence.premortem import (
    ZyeNegativePreMortem,
    _run_negative_brain_sync,
)
from zye_intelligence.negative_audit import (
    NegativeAuditEngine,
)
from zye_intelligence.decision_matrix import (
    ZyeDecisionMatrix,
    compare_and_decide_solutions,
    PRIORITY_WEIGHTS,
)
from zye_intelligence.mission_controller import (
    MISSION_PROFILES,
    MISSION_STATE_FILE,
    ZyeMissionController,
    _load_mission_state,
    set_mission_mode,
    get_current_mission,
)
from zye_intelligence.autonomous_watchdog import (
    ZyeAutonomousWatchdog,
    _scan_emerging_problems_sync,
    proactive_autonomous_loop,
    WATCHDOG_INTERVAL_SECONDS,
)
from zye_intelligence.emergency_reflex import (
    ZyeEmergencyReflex,
    execute_emergency_reflex,
    SUPPORTED_EMERGENCY_TYPES,
)
from zye_intelligence.execution_gate import (
    ZyeExecutionGate,
    TOOL_RISK_REGISTRY,
    PREMORTEM_MANDATORY_CLASSES,
    CONFIRMATION_MANDATORY_CLASSES,
)

__all__ = [
    # Schemas
    "NegativeAuditReport",
    "SolutionCandidate",
    "DecisionResult",
    "MissionState",
    "WatchdogProblem",
    "EmergencyResult",
    # Preflight
    "ZyeSystemPreflight",
    "_preflight_system_check",
    # Pre-Mortem & Audit
    "ZyeNegativePreMortem",
    "_run_negative_brain_sync",
    "NegativeAuditEngine",
    # Decision Matrix
    "ZyeDecisionMatrix",
    "compare_and_decide_solutions",
    "PRIORITY_WEIGHTS",
    # Mission Controller
    "MISSION_PROFILES",
    "MISSION_STATE_FILE",
    "ZyeMissionController",
    "_load_mission_state",
    "set_mission_mode",
    "get_current_mission",
    # Watchdog
    "ZyeAutonomousWatchdog",
    "_scan_emerging_problems_sync",
    "proactive_autonomous_loop",
    "WATCHDOG_INTERVAL_SECONDS",
    # Emergency Reflex
    "ZyeEmergencyReflex",
    "execute_emergency_reflex",
    "SUPPORTED_EMERGENCY_TYPES",
    # Execution Gate
    "ZyeExecutionGate",
    "TOOL_RISK_REGISTRY",
    "PREMORTEM_MANDATORY_CLASSES",
    "CONFIRMATION_MANDATORY_CLASSES",
]

"""
Mission-Adaptive Behavior Controller & Persistence — Zye Day 13.
Manages the 5 core mission profiles, atomic JSON persistence, corruption recovery,
hysteresis dampening, and policy constraint enforcement.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import tempfile
import threading
import time
from datetime import datetime, timezone
from typing import Any

from zye_intelligence.schemas import MissionState

logger = logging.getLogger("zye.intelligence.missions")

MISSION_PROFILES: dict[str, dict[str, Any]] = {
    "NORMAL_ASSISTANT": {
        "risk_tolerance": "MODERATE",
        "resource_budget": "BALANCED",
        "description": "Everyday Zye operations, normal voice interaction, balanced resource usage.",
        "premortem_required": False,
        "max_background_tasks": 4,
    },
    "DEEP_ENGINEERING": {
        "risk_tolerance": "LOW",
        "resource_budget": "HIGH_COMPUTE_ALLOWED",
        "description": "Precision-first planning, advanced coding, CAD audits, mandatory pre-mortem before modification.",
        "premortem_required": True,
        "max_background_tasks": 8,
    },
    "STEALTH_BATTERY_SAVER": {
        "risk_tolerance": "CONSERVATIVE",
        "resource_budget": "ULTRA_LOW_POWER",
        "description": "Ultra-low-power resource budget, minimize background work, preserve battery life.",
        "premortem_required": True,
        "max_background_tasks": 1,
    },
    "TACTICAL_REALTIME": {
        "risk_tolerance": "FAST_REFLEX",
        "resource_budget": "LOW_LATENCY_PRIORITY",
        "description": "Prioritize fast telemetry, low latency pattern analysis, time-sensitive defensive reflexes.",
        "premortem_required": False,
        "max_background_tasks": 2,
    },
    "EMERGENCY_LOCKDOWN": {
        "risk_tolerance": "ZERO_TRUST",
        "resource_budget": "CRITICAL_DEFENSE",
        "description": "Zero trust policy, protect critical files, apply pre-authorized defensive containment.",
        "premortem_required": True,
        "max_background_tasks": 0,
    },
}

MISSION_STATE_FILE = pathlib.Path.cwd() / "zye_mission_state.json"
_STATE_LOCK = threading.RLock()
DEFAULT_HYSTERESIS_SECONDS = 0.0


class ZyeMissionController:
    """
    Manages active mission profiles, policy constraints, and persistent state.
    Guarantees atomic file updates, backup recovery, and hysteresis dampening.
    """

    def __init__(
        self,
        state_file: pathlib.Path | str | None = None,
        hysteresis_seconds: float = DEFAULT_HYSTERESIS_SECONDS,
    ) -> None:
        self._state_file = pathlib.Path(state_file or MISSION_STATE_FILE)
        self._backup_file = self._state_file.with_suffix(".json.bak")
        self._hysteresis_seconds = hysteresis_seconds
        self._last_transition_time: float = 0.0
        self._previous_mission: str | None = None
        self._transition_history: list[dict[str, Any]] = []

    def validate_mission(self, mission_name: str) -> bool:
        """Validate if mission_name is a recognized mission profile."""
        return str(mission_name).strip() in MISSION_PROFILES

    def _default_state(self) -> dict[str, Any]:
        """Construct fallback state in NORMAL_ASSISTANT."""
        profile = MISSION_PROFILES["NORMAL_ASSISTANT"]
        state = MissionState(
            mission="NORMAL_ASSISTANT",
            risk_tolerance=profile["risk_tolerance"],
            resource_budget=profile["resource_budget"],
            custom_objective="Default operational state",
            updated_at=datetime.now(timezone.utc).isoformat(),
            previous_mission=None,
            transition_reason="Initialized default state",
            configuration_version="1.0.0",
        )
        return state.model_dump()

    def _atomic_write(self, data: dict[str, Any]) -> None:
        """
        Write state atomically using a temporary file and os.replace.
        Creates and preserves a valid backup copy.
        """
        # Ensure parent directory exists
        self._state_file.parent.mkdir(parents=True, exist_ok=True)

        content = json.dumps(data, indent=2)

        # 1. Write to temp file in same directory for atomic rename
        temp_fd, temp_path = tempfile.mkstemp(
            prefix="zye_mission_", suffix=".tmp", dir=str(self._state_file.parent)
        )
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

            # 2. Backup existing state file if present and valid
            if self._state_file.exists():
                try:
                    existing_text = self._state_file.read_text(encoding="utf-8")
                    json.loads(existing_text)  # verify valid before backing up
                    self._backup_file.write_text(existing_text, encoding="utf-8")
                except Exception:
                    pass

            # 3. Atomically replace active file
            os.replace(temp_path, str(self._state_file))

            # 4. Maintain valid backup of latest successful state
            try:
                self._backup_file.write_text(content, encoding="utf-8")
            except Exception:
                pass
        except Exception as exc:
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            logger.error("Failed to write mission state atomically: %s", exc)
            raise

    def load_mission(self) -> dict[str, Any]:
        """
        Load mission state from disk.
        Safely recovers from missing or corrupted state files via backup or fallback.
        """
        with _STATE_LOCK:
            if not self._state_file.exists():
                default_data = self._default_state()
                self._atomic_write(default_data)
                return default_data

            try:
                content = self._state_file.read_text(encoding="utf-8")
                data = json.loads(content)
                mission_name = data.get("mission")
                if not mission_name or not self.validate_mission(mission_name):
                    raise ValueError(f"Invalid mission name in file: '{mission_name}'")
                return data
            except Exception as exc:
                logger.warning("Corrupted or invalid mission state file (%s); attempting backup recovery", exc)
                # Preserve corrupted file for forensics
                try:
                    corrupt_path = self._state_file.with_suffix(".json.corrupt")
                    if self._state_file.exists():
                        corrupt_path.write_bytes(self._state_file.read_bytes())
                except Exception:
                    pass

                # Attempt recovery from backup
                if self._backup_file.exists():
                    try:
                        backup_content = self._backup_file.read_text(encoding="utf-8")
                        backup_data = json.loads(backup_content)
                        if self.validate_mission(backup_data.get("mission", "")):
                            logger.info("Successfully recovered mission state from backup copy")
                            self._atomic_write(backup_data)
                            return backup_data
                    except Exception as b_exc:
                        logger.warning("Backup recovery failed: %s", b_exc)

                # Fallback to NORMAL_ASSISTANT
                fallback = self._default_state()
                fallback["transition_reason"] = f"Recovered from corrupted state: {exc}"
                self._atomic_write(fallback)
                return fallback

    def get_transition_history(self) -> list[dict[str, Any]]:
        """Return transition history list."""
        return list(self._transition_history)

    @staticmethod
    def suggest_mission(text: str) -> str:
        """Suggest appropriate mission based on task keywords. Backward compatible with Day 11."""
        t = (text or "").lower()
        if any(w in t for w in ["breach", "attack", "lockdown", "emergency", "compromise", "intrusion"]):
            return "EMERGENCY_LOCKDOWN"
        if any(w in t for w in ["battery", "unplugged", "low power", "saver", "power saving"]):
            return "STEALTH_BATTERY_SAVER"
        if any(w in t for w in ["realtime", "streaming", "reflex", "tactical", "low latency"]):
            return "TACTICAL_REALTIME"
        if any(w in t for w in ["debug", "patch", "python", "script", "code", "engineering", "compile"]):
            return "DEEP_ENGINEERING"
        return "NORMAL_ASSISTANT"

    def get_current_mission(self) -> dict[str, Any]:
        """Query active mission profile and constraints."""
        state = self.load_mission()
        mission_name = state.get("mission", "NORMAL_ASSISTANT")
        profile_meta = MISSION_PROFILES.get(mission_name, MISSION_PROFILES["NORMAL_ASSISTANT"])
        return {
            **state,
            "description": profile_meta["description"],
            "premortem_required": profile_meta["premortem_required"],
            "max_background_tasks": profile_meta["max_background_tasks"],
        }

    def set_mission(
        self,
        mission_name: str,
        custom_objective: str = "",
        transition_reason: str = "",
        force: bool = False,
    ) -> dict[str, Any]:
        """
        Set active mission profile. Enforces hysteresis unless force=True.
        Persists state atomically to zye_mission_state.json.
        """
        clean_name = str(mission_name).strip().upper()
        if not self.validate_mission(clean_name):
            valid_list = list(MISSION_PROFILES.keys())
            raise ValueError(f"Unrecognized mission profile '{mission_name}'. Valid profiles: {valid_list}")

        with _STATE_LOCK:
            now = time.monotonic()
            elapsed = now - self._last_transition_time

            # Hysteresis check (unless forced or first transition or emergency lockdown)
            if not force and clean_name != "EMERGENCY_LOCKDOWN" and self._last_transition_time > 0.0:
                if elapsed < self._hysteresis_seconds:
                    logger.debug(
                        "Mission transition to '%s' ignored due to hysteresis (elapsed %.2fs < %.2fs)",
                        clean_name,
                        elapsed,
                        self._hysteresis_seconds,
                    )
                    return self.get_current_mission()

            current = self.load_mission()
            old_mission = current.get("mission", "NORMAL_ASSISTANT")

            profile = MISSION_PROFILES[clean_name]
            new_state = MissionState(
                mission=clean_name,
                risk_tolerance=profile["risk_tolerance"],
                resource_budget=profile["resource_budget"],
                custom_objective=custom_objective or current.get("custom_objective", ""),
                updated_at=datetime.now(timezone.utc).isoformat(),
                previous_mission=old_mission,
                transition_reason=transition_reason or f"Transition to {clean_name}",
                configuration_version="1.0.0",
            ).model_dump()

            self._atomic_write(new_state)
            self._previous_mission = old_mission
            self._last_transition_time = now

            self._transition_history.append({
                "from": old_mission,
                "from_mission": old_mission,
                "to": clean_name,
                "to_mission": clean_name,
                "timestamp": new_state["updated_at"],
                "reason": new_state["transition_reason"],
            })

            logger.info("Mission profile transition: %s -> %s (Reason: %s)", old_mission, clean_name, new_state["transition_reason"])
            return self.get_current_mission()


# --- Functional interface functions (Section 12) ---

def _load_mission_state() -> dict[str, Any]:
    """Load mission state via default controller."""
    controller = ZyeMissionController()
    return controller.load_mission()


def set_mission_mode(mission_name: str, custom_objective: str = "") -> dict[str, Any]:
    """Set active mission mode via default controller."""
    controller = ZyeMissionController()
    return controller.set_mission(mission_name, custom_objective=custom_objective)


def get_current_mission() -> dict[str, Any]:
    """Get active mission mode via default controller."""
    controller = ZyeMissionController()
    return controller.get_current_mission()

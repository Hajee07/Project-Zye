"""
Gemini Project Router — Zye Multi-Project Gemini Intelligence Infrastructure v2.0 (Section 06).
Maps distinct architectural workloads to 7 dedicated Google Cloud projects and API slots.
Enforces project authorization, per-project rate limits, and strictly prohibits cross-project
quota pooling / rate-limit evasion.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from gemini_db import get_db_connection, init_gemini_database
from gemini_key_manager import GeminiKeyManager

logger = logging.getLogger("zye.gemini.project_router")

# Standard Workload-to-Slot Canonical Mapping
DEFAULT_WORKLOAD_ROUTING: dict[str, int] = {
    # Slot 1: Primary Interaction & Conversational Core
    "INTERACTION": 1,
    "CONVERSATION": 1,
    "VOICE": 1,
    "VOICE_LOOP": 1,
    "FAST_ROUTING": 1,
    "GENERAL": 1,
    "DEFAULT": 1,

    # Slot 2: Master MCP Orchestrator & Tool Routing
    "MCP_ORCHESTRATOR": 2,
    "MCP": 2,
    "TOOL_ROUTING": 2,
    "SCHEMA_SYNC": 2,
    "SKILLS": 2,

    # Slot 3: Day 13 Negative Pre-Mortem Brain & Adversarial FMEA
    "PREMORTEM": 3,
    "NEGATIVE_BRAIN": 3,
    "ADVERSARIAL": 3,
    "FMEA": 3,
    "RISK_ANALYSIS": 3,
    "SECURITY_AUDIT": 3,

    # Slot 4: Day 14 Personal Assistant & Workflow Automation
    "PERSONAL_ASSISTANT": 4,
    "AUTOMATION": 4,
    "USER_WORKFLOW": 4,
    "DATA_INTEGRATION": 4,
    "SCHEDULE": 4,

    # Slot 5: Autonomous Watchdog & System Preflight Diagnostics
    "WATCHDOG": 5,
    "PREFLIGHT": 5,
    "DIAGNOSTICS": 5,
    "SYSTEM_METRICS": 5,
    "BACKGROUND_MONITOR": 5,

    # Slot 6: Emergency Reflex Controller & Self-Repair Engine
    "EMERGENCY_REFLEX": 6,
    "SELF_REPAIR": 6,
    "RECOVERY": 6,
    "LOCKDOWN": 6,
    "INCIDENT_RESPONSE": 6,

    # Slot 7: Task Decomposition & Bounded Parallel Workers
    "TASK_DECOMPOSITION": 7,
    "PARALLEL_WORKERS": 7,
    "MULTI_TASK": 7,
    "RESEARCH_SUBTASK": 7,
}


@dataclass
class ProjectRateLimitState:
    """Tracks per-project rate limits and backoff without cross-project pooling."""
    slot_id: int
    project_alias: str
    rpm_limit: int = 60
    tpm_limit: int = 1_000_000
    rpd_limit: int = 10_000
    recent_requests: list[float] = field(default_factory=list)  # timestamps
    recent_tokens: list[tuple[float, int]] = field(default_factory=list)  # (timestamp, tokens)
    daily_request_count: int = 0
    daily_reset_day: int = field(default_factory=lambda: datetime.now(timezone.utc).day)
    rate_limited_until: float = 0.0
    status: str = "AVAILABLE"  # AVAILABLE, RATE_LIMITED, PAUSED


class GeminiProjectRouter:
    """
    Central router that assigns workloads to dedicated Google Cloud project slots.
    Strictly forbids switching project slots to bypass 429 quota exhaustion.
    """

    def __init__(
        self,
        key_manager: GeminiKeyManager | None = None,
        db_path: str | None = None,
        allow_cross_project_fallback: bool = False,
    ) -> None:
        self._db_path = db_path
        self._key_manager = key_manager or GeminiKeyManager(db_path=db_path)
        self._allow_cross_project_fallback = allow_cross_project_fallback
        self._lock = threading.RLock()

        # Workload routing table
        self._routing_table: dict[str, int] = dict(DEFAULT_WORKLOAD_ROUTING)

        # Rate limit tracking per slot (1..7)
        self._rate_limits: dict[int, ProjectRateLimitState] = {
            i: ProjectRateLimitState(slot_id=i, project_alias=f"PROJECT_{i:02d}")
            for i in range(1, 8)
        }

        # Initialize database tables
        init_gemini_database(self._db_path)
        self.sync_registry_to_db()

    @property
    def key_manager(self) -> GeminiKeyManager:
        return self._key_manager

    @property
    def allow_cross_project_fallback(self) -> bool:
        return self._allow_cross_project_fallback

    def route_workload(self, workload: str) -> int:
        """
        Determine which slot (1..7) owns the given workload.
        Returns canonical slot ID (1..7).
        """
        clean = workload.strip().upper()
        with self._lock:
            if clean in self._routing_table:
                return self._routing_table[clean]

            # Heuristic match
            for key, slot_id in self._routing_table.items():
                if key in clean or clean in key:
                    return slot_id

            logger.info("Workload '%s' not explicitly mapped; routing to Slot 1 (Interaction Core)", workload)
            return 1

    def register_workload(self, workload: str, slot_id: int) -> bool:
        """Explicitly assign a workload name to a slot ID (1..7)."""
        if not (1 <= slot_id <= 7):
            logger.warning("Invalid slot_id %d for workload registration", slot_id)
            return False

        clean = workload.strip().upper()
        with self._lock:
            self._routing_table[clean] = slot_id
            self.sync_registry_to_db()
            logger.info("Registered workload '%s' to slot %d", clean, slot_id)
            return True

    def get_routing_table(self) -> dict[str, int]:
        """Return a copy of the active workload routing table."""
        with self._lock:
            return dict(self._routing_table)

    def is_slot_available(self, slot_id: int) -> tuple[bool, str]:
        """
        Check if a project slot is available for processing requests.
        Returns (is_available, reason).
        """
        with self._lock:
            rl = self._rate_limits.get(slot_id)
            if not rl:
                return False, f"Invalid slot {slot_id}"

            now = time.time()
            if rl.rate_limited_until > now:
                remaining = int(rl.rate_limited_until - now)
                return False, f"Slot {slot_id} rate limited for {remaining} more seconds"

            slot = self._key_manager.get_slot(slot_id)
            if not slot or not slot.enabled:
                return False, f"Slot {slot_id} is disabled"

            if slot.auth_status == "AUTH_FAILED":
                return False, f"Slot {slot_id} authentication failed"

            # Check RPM / TPM sliding windows
            self._prune_windows(rl, now)
            if len(rl.recent_requests) >= rl.rpm_limit:
                return False, f"Slot {slot_id} exceeded RPM limit ({rl.rpm_limit}/min)"

            current_tpm = sum(tokens for _, tokens in rl.recent_tokens)
            if current_tpm >= rl.tpm_limit:
                return False, f"Slot {slot_id} exceeded TPM limit ({rl.tpm_limit}/min)"

            return True, "OK"

    def record_request_start(self, slot_id: int, estimated_tokens: int = 0) -> None:
        """Record the initiation of a request to update rate limit trackers."""
        with self._lock:
            rl = self._rate_limits.get(slot_id)
            if not rl:
                return

            now = time.time()
            self._prune_windows(rl, now)
            rl.recent_requests.append(now)
            if estimated_tokens > 0:
                rl.recent_tokens.append((now, estimated_tokens))

            today = datetime.now(timezone.utc).day
            if rl.daily_reset_day != today:
                rl.daily_request_count = 0
                rl.daily_reset_day = today
            rl.daily_request_count += 1

    def mark_rate_limited(self, slot_id: int, retry_after_seconds: float = 60.0) -> None:
        """
        Mark a project slot as rate-limited (HTTP 429).
        Does NOT switch project slots. Enforces backoff on this slot.
        """
        with self._lock:
            rl = self._rate_limits.get(slot_id)
            if rl:
                rl.rate_limited_until = time.time() + max(1.0, retry_after_seconds)
                rl.status = "RATE_LIMITED"
                logger.warning(
                    "Project slot %d marked RATE_LIMITED for %.1f seconds. (Cross-project switching is DISABLED)",
                    slot_id,
                    retry_after_seconds,
                )
            self._key_manager.mark_rate_limited(slot_id)

    def clear_rate_limit(self, slot_id: int) -> None:
        """Manually or automatically clear rate limit for a slot."""
        with self._lock:
            rl = self._rate_limits.get(slot_id)
            if rl:
                rl.rate_limited_until = 0.0
                rl.status = "AVAILABLE"
                logger.info("Cleared rate limit for slot %d", slot_id)

    def get_project_for_slot(self, slot_id: int) -> dict[str, Any] | None:
        """Get project metadata for a specific slot."""
        slot = self._key_manager.get_slot(slot_id)
        if not slot:
            return None

        with self._lock:
            rl = self._rate_limits.get(slot_id)
            now = time.time()
            rate_limited = bool(rl and rl.rate_limited_until > now)

        return {
            "slot_id": slot.slot_id,
            "account_alias": slot.account_alias,
            "project_alias": slot.project_alias,
            "project_id": slot.project_id,
            "auth_status": slot.auth_status,
            "key_health": slot.key_health,
            "rate_limited": rate_limited,
            "assigned_workloads": [
                w for w, s in self._routing_table.items() if s == slot_id
            ],
        }

    def get_all_projects_status(self) -> list[dict[str, Any]]:
        """Return status summary for all 7 project slots."""
        return [
            proj for i in range(1, 8)
            if (proj := self.get_project_for_slot(i)) is not None
        ]

    def _prune_windows(self, rl: ProjectRateLimitState, now: float) -> None:
        """Prune requests and tokens older than 60 seconds from sliding window."""
        cutoff = now - 60.0
        rl.recent_requests = [t for t in rl.recent_requests if t >= cutoff]
        rl.recent_tokens = [(t, tok) for t, tok in rl.recent_tokens if t >= cutoff]

    def sync_registry_to_db(self) -> None:
        """Persist project assignments to SQLite gemini_project_registry table."""
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            conn = get_db_connection(self._db_path)
            try:
                with conn:
                    for slot_id in range(1, 8):
                        slot = self._key_manager.get_slot(slot_id)
                        if not slot:
                            continue

                        assigned = [w for w, s in self._routing_table.items() if s == slot_id]
                        assigned_json = json.dumps(assigned)
                        proj_id = slot.project_id or f"zye-project-{slot_id:02d}"

                        conn.execute("""
                            INSERT INTO gemini_project_registry
                            (slot_id, project_alias, project_id, account_alias, assigned_workloads, status, billing_status, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                            ON CONFLICT(slot_id) DO UPDATE SET
                                project_alias = excluded.project_alias,
                                project_id = excluded.project_id,
                                account_alias = excluded.account_alias,
                                assigned_workloads = excluded.assigned_workloads,
                                status = excluded.status,
                                updated_at = excluded.updated_at;
                        """, (
                            slot_id,
                            slot.project_alias,
                            proj_id,
                            slot.account_alias,
                            assigned_json,
                            slot.auth_status,
                            now,
                            now,
                        ))
            except Exception as exc:
                logger.warning("Failed to sync project registry to DB: %s", exc)
            finally:
                conn.close()

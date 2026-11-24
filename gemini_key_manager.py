"""
Gemini Key Manager — Zye Multi-Project Gemini Intelligence Infrastructure v2.0 (Section 04).
Securely manages seven independent API key slots, associated Google Cloud projects,
credential masking, health monitoring, and client lifecycle.
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

from gemini_db import get_db_connection, init_gemini_database

logger = logging.getLogger("zye.gemini.key_manager")

try:
    from google import genai
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    _GENAI_AVAILABLE = False


TOTAL_KEY_SLOTS = 7


@dataclass
class KeySlot:
    """Represents one of seven independently managed API credential slots."""
    slot_id: int
    account_alias: str
    project_alias: str
    env_key_var: str
    env_project_var: str
    api_key: str | None = None
    project_id: str | None = None
    enabled: bool = True
    auth_status: str = "UNCONFIGURED"  # CONFIGURED, VALIDATED, UNCONFIGURED, AUTH_FAILED, RATE_LIMITED, DISABLED
    key_health: str = "UNKNOWN"        # HEALTHY, DEGRADED, UNAVAILABLE, UNKNOWN
    last_used_timestamp: str | None = None
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_thinking_tokens: int = 0
    client: Any = None                 # Cached google.genai.Client instance


def mask_credential(key: str | None) -> str:
    """
    Mask an API key for safe display in UI, admin dashboards, and logs.
    Never exposes plaintext secrets.
    Format example: ************ABCD
    """
    if not key or not str(key).strip():
        return "NOT_CONFIGURED"
    clean = str(key).strip()
    if len(clean) <= 8:
        return "********"
    last4 = clean[-4:]
    return f"{'*' * (len(clean) - 4)}{last4}" if len(clean) < 16 else f"************{last4}"


class GeminiKeyManager:
    """
    Centralized 7-Slot Gemini API Key and Project Credential Manager.
    Enforces strict separation of credentials and prevents secret exposure.
    """

    def __init__(self, db_path: str | None = None, auto_load: bool = True) -> None:
        self._db_path = db_path
        self._lock = threading.RLock()
        self.slots: dict[int, KeySlot] = {}

        # Ensure database tables exist
        init_gemini_database(self._db_path)

        # Initialize the 7 slot records
        for i in range(1, TOTAL_KEY_SLOTS + 1):
            slot_str = f"{i:02d}"
            self.slots[i] = KeySlot(
                slot_id=i,
                account_alias=f"ACCOUNT_{slot_str}",
                project_alias=f"PROJECT_{slot_str}",
                env_key_var=f"GEMINI_API_KEY_{slot_str}",
                env_project_var=f"GEMINI_PROJECT_ID_{slot_str}",
            )

        if auto_load:
            self.load_from_environment()

    def load_from_environment(self) -> None:
        """Load credentials and project metadata from environment variables (.env)."""
        load_dotenv(override=False)

        with self._lock:
            for slot_id, slot in self.slots.items():
                slot_str = f"{slot_id:02d}"
                raw_key = os.environ.get(slot.env_key_var, "").strip()
                raw_project = os.environ.get(slot.env_project_var, "").strip()

                # Slot 1 backward-compatibility fallback
                if slot_id == 1 and not raw_key:
                    raw_key = os.environ.get("GEMINI_API_KEY", "").strip()

                if raw_key and not raw_key.startswith("placeholder") and raw_key != "your_gemini_api_key_here":
                    slot.api_key = raw_key
                    slot.project_id = raw_project or f"zye-project-{slot_str}"
                    slot.auth_status = "CONFIGURED"
                    slot.key_health = "HEALTHY"
                    slot.enabled = True
                    self._init_client_for_slot(slot_id)
                else:
                    slot.api_key = None
                    slot.project_id = raw_project or None
                    slot.auth_status = "UNCONFIGURED"
                    slot.key_health = "UNAVAILABLE"
                    slot.client = None

            self.sync_to_database()

    def _init_client_for_slot(self, slot_id: int) -> bool:
        """Initialize or refresh google.genai.Client for a specific slot."""
        slot = self.slots.get(slot_id)
        if not slot or not slot.api_key or not _GENAI_AVAILABLE or genai is None:
            if slot:
                slot.client = None
            return False

        try:
            # Initialize official Google GenAI Client with the slot's API key
            client = genai.Client(api_key=slot.api_key)
            slot.client = client
            return True
        except Exception as exc:
            logger.warning("Failed to initialize genai.Client for slot %d: %s", slot_id, exc)
            slot.client = None
            slot.key_health = "DEGRADED"
            return False

    def get_slot(self, slot_identifier: int | str) -> KeySlot | None:
        """
        Retrieve a slot by slot_id (1..7), account_alias ('ACCOUNT_01'),
        or project_alias ('PROJECT_01').
        """
        with self._lock:
            if isinstance(slot_identifier, int):
                return self.slots.get(slot_identifier)

            s_clean = str(slot_identifier).strip().upper()
            for slot in self.slots.values():
                if (
                    str(slot.slot_id) == s_clean
                    or slot.account_alias == s_clean
                    or slot.project_alias == s_clean
                    or (slot.project_id and slot.project_id.upper() == s_clean)
                ):
                    return slot
            return None

    def get_all_slots(self) -> list[KeySlot]:
        """Return all 7 slots in ascending order."""
        with self._lock:
            return [self.slots[i] for i in sorted(self.slots.keys())]

    def get_client(self, slot_identifier: int | str) -> Any:
        """
        Get the secure genai.Client for a slot.
        Returns None if unconfigured or disabled.
        """
        with self._lock:
            slot = self.get_slot(slot_identifier)
            if not slot or not slot.enabled or slot.auth_status in ("AUTH_FAILED", "DISABLED"):
                return None
            if slot.client is None and slot.api_key:
                self._init_client_for_slot(slot.slot_id)
            return slot.client

    def get_masked_slots_summary(self) -> list[dict[str, Any]]:
        """
        Generate safe, masked administrative overview of all 7 slots.
        Strictly prevents leaking plaintext keys.
        """
        with self._lock:
            summary = []
            for slot in self.get_all_slots():
                summary.append({
                    "slot_id": slot.slot_id,
                    "account_alias": slot.account_alias,
                    "project_alias": slot.project_alias,
                    "project_id": slot.project_id or "(none)",
                    "masked_key": mask_credential(slot.api_key),
                    "enabled": slot.enabled,
                    "auth_status": slot.auth_status,
                    "key_health": slot.key_health,
                    "total_requests": slot.total_requests,
                    "successful_requests": slot.successful_requests,
                    "failed_requests": slot.failed_requests,
                    "total_tokens": slot.total_input_tokens + slot.total_output_tokens,
                    "last_used_timestamp": slot.last_used_timestamp or "(never)",
                })
            return summary

    def set_key(
        self,
        slot_id: int,
        api_key: str,
        project_id: str | None = None,
        validate: bool = False,
    ) -> bool:
        """Explicitly configure or update an API key for a slot."""
        if slot_id not in self.slots:
            raise ValueError(f"Invalid slot ID: {slot_id}. Must be between 1 and {TOTAL_KEY_SLOTS}.")

        with self._lock:
            clean_key = str(api_key).strip()
            slot = self.slots[slot_id]
            slot.api_key = clean_key
            if project_id:
                slot.project_id = str(project_id).strip()
            slot.enabled = True
            slot.auth_status = "CONFIGURED"
            slot.key_health = "HEALTHY"
            self._init_client_for_slot(slot_id)

            if validate:
                self.validate_key(slot_id)

            self.sync_to_database()
            logger.info("Key updated for slot %d (%s)", slot_id, slot.account_alias)
            return True

    def remove_key(self, slot_id: int) -> bool:
        """Remove credential from a slot."""
        if slot_id not in self.slots:
            return False

        with self._lock:
            slot = self.slots[slot_id]
            slot.api_key = None
            slot.client = None
            slot.auth_status = "UNCONFIGURED"
            slot.key_health = "UNAVAILABLE"
            self.sync_to_database()
            logger.info("Credential removed for slot %d", slot_id)
            return True

    def disable_slot(self, slot_id: int) -> bool:
        """Temporarily disable a key slot without deleting credential."""
        with self._lock:
            slot = self.get_slot(slot_id)
            if not slot:
                return False
            slot.enabled = False
            slot.auth_status = "DISABLED"
            self.sync_to_database()
            return True

    def enable_slot(self, slot_id: int) -> bool:
        """Re-enable a previously disabled key slot."""
        with self._lock:
            slot = self.get_slot(slot_id)
            if not slot:
                return False
            slot.enabled = True
            slot.auth_status = "CONFIGURED" if slot.api_key else "UNCONFIGURED"
            self.sync_to_database()
            return True

    def mark_auth_failed(self, slot_id: int, reason: str = "") -> None:
        """Mark slot as authentication failure (401/403)."""
        with self._lock:
            slot = self.get_slot(slot_id)
            if slot:
                slot.auth_status = "AUTH_FAILED"
                slot.key_health = "UNAVAILABLE"
                self.sync_to_database()
                logger.warning("Slot %d marked AUTH_FAILED: %s", slot_id, reason)

    def mark_rate_limited(self, slot_id: int) -> None:
        """Mark slot as rate limited (429)."""
        with self._lock:
            slot = self.get_slot(slot_id)
            if slot:
                slot.auth_status = "RATE_LIMITED"
                slot.key_health = "DEGRADED"
                self.sync_to_database()

    def record_usage(
        self,
        slot_id: int,
        input_tokens: int = 0,
        output_tokens: int = 0,
        thinking_tokens: int = 0,
        success: bool = True,
    ) -> None:
        """Update slot request and token statistics."""
        with self._lock:
            slot = self.get_slot(slot_id)
            if not slot:
                return

            slot.total_requests += 1
            if success:
                slot.successful_requests += 1
                slot.key_health = "HEALTHY"
                if slot.auth_status == "RATE_LIMITED":
                    slot.auth_status = "CONFIGURED"
            else:
                slot.failed_requests += 1

            slot.total_input_tokens += max(0, input_tokens)
            slot.total_output_tokens += max(0, output_tokens)
            slot.total_thinking_tokens += max(0, thinking_tokens)
            slot.last_used_timestamp = datetime.now(timezone.utc).isoformat()
            self.sync_to_database()

    def validate_key(self, slot_id: int, live_check: bool = False) -> tuple[bool, str]:
        """
        Validate credential for a slot.
        If live_check=True and google-genai is available, attempts a lightweight model check.
        """
        with self._lock:
            slot = self.get_slot(slot_id)
            if not slot:
                return False, f"Slot {slot_id} does not exist"
            if not slot.api_key:
                return False, f"Slot {slot_id} is unconfigured"

            # Check format heuristics
            if len(slot.api_key) < 20:
                slot.key_health = "DEGRADED"
                return False, "API key string is suspiciously short"

            if not live_check:
                slot.auth_status = "VALIDATED"
                slot.key_health = "HEALTHY"
                self.sync_to_database()
                return True, "Key format valid"

            # Live API validation check
            client = self.get_client(slot_id)
            if not client:
                return False, "Failed to initialize GenAI client"

            try:
                # Count tokens on empty/short text as lightweight read check
                client.models.count_tokens(model="gemini-2.5-flash", contents="ping")
                slot.auth_status = "VALIDATED"
                slot.key_health = "HEALTHY"
                self.sync_to_database()
                return True, "Live credential validation succeeded"
            except Exception as exc:
                err_str = str(exc)
                if "401" in err_str or "API_KEY_INVALID" in err_str:
                    self.mark_auth_failed(slot_id, err_str)
                    return False, f"Authentication failed: {err_str}"
                elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    self.mark_rate_limited(slot_id)
                    return False, "Key quota exhausted or rate limited"
                else:
                    slot.key_health = "DEGRADED"
                    return False, f"Live validation check error: {err_str}"

    def get_masked_admin_summary(self) -> list[dict[str, Any]]:
        """Return masked administrative summary of all slots."""
        with self._lock:
            return [
                {
                    "slot_id": s.slot_id,
                    "account_alias": s.account_alias,
                    "project_alias": s.project_alias,
                    "masked_key": mask_credential(s.api_key),
                    "auth_status": s.auth_status,
                    "key_health": s.key_health,
                    "enabled": s.enabled,
                    "total_requests": s.total_requests,
                }
                for s in self.get_all_slots()
            ]

    def sync_to_database(self) -> None:
        """Persist current key metadata and project registry to SQLite."""
        now = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection(self._db_path)
        try:
            with conn:
                for slot in self.slots.values():
                    # 1. Update gemini_key_metadata
                    conn.execute("""
                        INSERT INTO gemini_key_metadata (
                            slot_id, account_alias, project_alias, masked_key, env_key_var,
                            env_project_var, auth_status, key_health, last_used_at,
                            total_requests, successful_requests, failed_requests, total_tokens, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(slot_id) DO UPDATE SET
                            account_alias = excluded.account_alias,
                            project_alias = excluded.project_alias,
                            masked_key = excluded.masked_key,
                            auth_status = excluded.auth_status,
                            key_health = excluded.key_health,
                            last_used_at = excluded.last_used_at,
                            total_requests = excluded.total_requests,
                            successful_requests = excluded.successful_requests,
                            failed_requests = excluded.failed_requests,
                            total_tokens = excluded.total_tokens,
                            updated_at = excluded.updated_at;
                    """, (
                        slot.slot_id,
                        slot.account_alias,
                        slot.project_alias,
                        mask_credential(slot.api_key),
                        slot.env_key_var,
                        slot.env_project_var,
                        slot.auth_status,
                        slot.key_health,
                        slot.last_used_timestamp,
                        slot.total_requests,
                        slot.successful_requests,
                        slot.failed_requests,
                        slot.total_input_tokens + slot.total_output_tokens,
                        now,
                    ))

                    # 2. Update gemini_project_registry
                    if slot.project_id:
                        conn.execute("""
                            INSERT INTO gemini_project_registry (
                                slot_id, project_alias, project_id, account_alias, status, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(slot_id) DO UPDATE SET
                                project_alias = excluded.project_alias,
                                project_id = excluded.project_id,
                                account_alias = excluded.account_alias,
                                status = excluded.status,
                                updated_at = excluded.updated_at;
                        """, (
                            slot.slot_id,
                            slot.project_alias,
                            slot.project_id,
                            slot.account_alias,
                            slot.auth_status,
                            now,
                            now,
                        ))
        except Exception as exc:
            logger.error("Failed to sync key metadata to database: %s", exc)
        finally:
            conn.close()

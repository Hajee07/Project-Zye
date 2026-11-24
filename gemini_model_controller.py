"""
Gemini Model & Thinking Controller — Zye Multi-Project Gemini Intelligence Infrastructure v2.0.
Manages primary model selection (gemini-3.8-flash), adaptive thinking levels (LOW, MEDIUM, HIGH),
manual/auto mode switches, and configuration persistence in SQLite.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

from gemini_db import get_db_connection, init_gemini_database

logger = logging.getLogger("zye.gemini.model_controller")

try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore
    _GENAI_AVAILABLE = False


DEFAULT_MODEL_ID = "gemini-3.5-flash-lite"
SUPPORTED_MODELS = {
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
}

VALID_THINKING_LEVELS = {"LOW", "MEDIUM", "HIGH"}
VALID_THINKING_MODES = {"MANUAL", "AUTO"}

# Heuristic keyword sets for AUTO mode complexity classification
HIGH_COMPLEXITY_KEYWORDS = {
    "premortem", "pre-mortem", "adversarial", "fmea", "root cause",
    "architecture", "security audit", "vulnerability", "risk assessment",
    "mathematical proof", "formal verification", "complex refactor",
    "failover", "disaster recovery", "threat model", "negative brain"
}

MEDIUM_COMPLEXITY_KEYWORDS = {
    "execute", "workflow", "orchestrate", "tool", "function call",
    "generate script", "debug", "multi-step", "code review", "refactor",
    "database migration", "sql query", "api integration", "test suite"
}


class GeminiModelController:
    """
    Central controller for Gemini model selection and adaptive thinking levels.
    Thread-safe and synchronized with SQLite.
    """

    def __init__(self, db_path: str | None = None, auto_init: bool = True) -> None:
        self._db_path = db_path
        self._lock = threading.RLock()

        # In-memory defaults
        self._model_id = DEFAULT_MODEL_ID
        self._thinking_level = "LOW"
        self._thinking_mode = "MANUAL"
        self._system_instruction = "You are Zye, an autonomous AI assistant."
        self._temperature = 0.5

        if auto_init:
            init_gemini_database(self._db_path)
            self.load_from_db()

    @property
    def model_id(self) -> str:
        with self._lock:
            return self._model_id

    @property
    def thinking_level(self) -> str:
        with self._lock:
            return self._thinking_level

    @property
    def thinking_mode(self) -> str:
        with self._lock:
            return self._thinking_mode

    @property
    def temperature(self) -> float:
        with self._lock:
            return self._temperature

    @property
    def system_instruction(self) -> str:
        with self._lock:
            return self._system_instruction

    def get_model_id(self) -> str:
        return self.model_id

    def get_thinking_level(self) -> str:
        return self.thinking_level

    def get_thinking_mode(self) -> str:
        return self.thinking_mode

    def set_model_id(self, model_id: str) -> bool:
        """Set primary model ID. Must be in supported list or start with gemini-."""
        clean = model_id.strip()
        if not clean.startswith("gemini-"):
            logger.warning("Rejecting invalid model_id: %s", model_id)
            return False

        with self._lock:
            self._model_id = clean
            self.sync_to_db()
            logger.info("Gemini Model ID set to %s", self._model_id)
            return True

    def set_thinking_level(self, level: str, mode: str = "MANUAL") -> bool:
        """
        Set active thinking level (LOW, MEDIUM, HIGH).
        Also allows setting mode (MANUAL or AUTO).
        """
        lvl = level.strip().upper()
        md = mode.strip().upper()

        if lvl not in VALID_THINKING_LEVELS:
            logger.warning("Invalid thinking level requested: %s (valid: %s)", level, VALID_THINKING_LEVELS)
            return False

        if md not in VALID_THINKING_MODES:
            md = "MANUAL"

        with self._lock:
            self._thinking_level = lvl
            self._thinking_mode = md
            self.sync_to_db()
            logger.info("Thinking level updated: %s (mode=%s)", self._thinking_level, self._thinking_mode)
            return True

    def set_thinking_mode(self, mode: str) -> bool:
        """Switch between MANUAL and AUTO thinking level determination."""
        md = mode.strip().upper()
        if md not in VALID_THINKING_MODES:
            logger.warning("Invalid thinking mode: %s", mode)
            return False

        with self._lock:
            self._thinking_mode = md
            self.sync_to_db()
            logger.info("Thinking mode updated: %s", self._thinking_mode)
            return True

    def set_temperature(self, temp: float) -> bool:
        if not (0.0 <= temp <= 2.0):
            return False
        with self._lock:
            self._temperature = temp
            self.sync_to_db()
            return True

    def set_system_instruction(self, instruction: str) -> None:
        with self._lock:
            self._system_instruction = instruction
            self.sync_to_db()

    def classify_complexity(self, prompt: str, workload: str | None = None) -> str:
        """
        Classify task complexity based on prompt content and workload classification.
        Returns 'LOW', 'MEDIUM', or 'HIGH'.
        """
        if workload:
            wl = workload.upper()
            if any(term in wl for term in ["PREMORTEM", "ADVERSARIAL", "SECURITY", "ARCHITECTURE"]):
                return "HIGH"
            if any(term in wl for term in ["WORKFLOW", "CODE", "TOOL", "ORCHESTRATOR"]):
                return "MEDIUM"

        text = prompt.lower()
        for kw in HIGH_COMPLEXITY_KEYWORDS:
            if kw in text:
                return "HIGH"

        for kw in MEDIUM_COMPLEXITY_KEYWORDS:
            if kw in text:
                return "MEDIUM"

        return "LOW"

    def resolve_thinking_level(
        self,
        prompt: str | None = None,
        workload: str | None = None,
        override_level: str | None = None,
    ) -> str:
        """
        Resolve the effective thinking level given current mode and optional overrides.
        Priority:
        1. Explicit override_level (if valid)
        2. AUTO mode evaluation (if mode == 'AUTO' and prompt/workload provided)
        3. Configured manual thinking level
        """
        if override_level:
            lvl = override_level.strip().upper()
            if lvl in VALID_THINKING_LEVELS:
                return lvl

        with self._lock:
            if self._thinking_mode == "AUTO" and (prompt or workload):
                return self.classify_complexity(prompt or "", workload=workload)
            return self._thinking_level

    def get_thinking_config(
        self,
        prompt: str | None = None,
        workload: str | None = None,
        override_level: str | None = None,
    ) -> Any:
        """
        Build google.genai.types.ThinkingConfig for the resolved thinking level.
        Returns None if genai types are unavailable.
        """
        if not _GENAI_AVAILABLE or types is None:
            return None

        effective_level = self.resolve_thinking_level(prompt, workload, override_level)

        level_enum = {
            "LOW": types.ThinkingLevel.LOW,
            "MEDIUM": types.ThinkingLevel.MEDIUM,
            "HIGH": types.ThinkingLevel.HIGH,
        }.get(effective_level, types.ThinkingLevel.LOW)

        try:
            return types.ThinkingConfig(thinking_level=level_enum)
        except Exception as exc:
            logger.warning("Error creating ThinkingConfig: %s", exc)
            return None

    def get_generate_content_config(
        self,
        prompt: str | None = None,
        workload: str | None = None,
        override_level: str | None = None,
        tools: list[Any] | None = None,
        system_instruction: str | None = None,
        temperature: float | None = None,
        response_mime_type: str | None = None,
        response_schema: Any = None,
    ) -> Any:
        """
        Build a complete google.genai.types.GenerateContentConfig including
        thinking_config, tools, system instruction, and temperature.
        """
        if not _GENAI_AVAILABLE or types is None:
            return None

        thinking_cfg = self.get_thinking_config(
            prompt=prompt,
            workload=workload,
            override_level=override_level,
        )

        with self._lock:
            sys_inst = system_instruction or self._system_instruction
            temp = temperature if temperature is not None else self._temperature

        kwargs: dict[str, Any] = {
            "thinking_config": thinking_cfg,
            "system_instruction": sys_inst,
            "temperature": temp,
        }

        if tools:
            kwargs["tools"] = tools
        if response_mime_type:
            kwargs["response_mime_type"] = response_mime_type
        if response_schema is not None:
            kwargs["response_schema"] = response_schema

        try:
            return types.GenerateContentConfig(**kwargs)
        except Exception as exc:
            logger.warning("Error instantiating GenerateContentConfig: %s", exc)
            # Fallback without thinking config if rejected
            kwargs.pop("thinking_config", None)
            return types.GenerateContentConfig(**kwargs)

    def load_from_db(self) -> None:
        """Load settings from SQLite gemini_model_settings table."""
        with self._lock:
            conn = get_db_connection(self._db_path)
            try:
                row = conn.execute(
                    "SELECT model_id, thinking_level, thinking_mode, system_instruction, temperature "
                    "FROM gemini_model_settings WHERE id = 1;"
                ).fetchone()
                if row:
                    self._model_id = str(row["model_id"])
                    self._thinking_level = str(row["thinking_level"]).upper()
                    self._thinking_mode = str(row["thinking_mode"]).upper()
                    self._system_instruction = str(row["system_instruction"] or self._system_instruction)
                    self._temperature = float(row["temperature"] if row["temperature"] is not None else 0.5)
            except Exception as exc:
                logger.warning("Failed to load gemini_model_settings from DB: %s", exc)
            finally:
                conn.close()

    def sync_to_db(self) -> None:
        """Persist current settings to SQLite gemini_model_settings table."""
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            conn = get_db_connection(self._db_path)
            try:
                with conn:
                    conn.execute("""
                        INSERT INTO gemini_model_settings
                        (id, model_id, thinking_level, thinking_mode, system_instruction, temperature, updated_at)
                        VALUES (1, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            model_id = excluded.model_id,
                            thinking_level = excluded.thinking_level,
                            thinking_mode = excluded.thinking_mode,
                            system_instruction = excluded.system_instruction,
                            temperature = excluded.temperature,
                            updated_at = excluded.updated_at;
                    """, (
                        self._model_id,
                        self._thinking_level,
                        self._thinking_mode,
                        self._system_instruction,
                        self._temperature,
                        now,
                    ))
            except Exception as exc:
                logger.warning("Failed to sync gemini_model_settings to DB: %s", exc)
            finally:
                conn.close()

    def get_settings(self) -> dict[str, Any]:
        """Return a read-only snapshot of current model settings."""
        with self._lock:
            return {
                "model_id": self._model_id,
                "thinking_level": self._thinking_level,
                "thinking_mode": self._thinking_mode,
                "temperature": self._temperature,
                "system_instruction": self._system_instruction,
            }

    def reset_to_defaults(self) -> None:
        """Reset all model settings to factory defaults."""
        with self._lock:
            self._model_id = DEFAULT_MODEL_ID
            self._thinking_level = "LOW"
            self._thinking_mode = "MANUAL"
            self._system_instruction = "You are Zye, an autonomous AI assistant."
            self._temperature = 0.5
            self.sync_to_db()

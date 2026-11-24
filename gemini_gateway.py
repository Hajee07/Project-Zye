"""
Central Gemini Intelligence Gateway — Zye Multi-Project Gemini Intelligence Infrastructure v2.0 (Section 09).
Unified gateway managing 7 API slots, 7 Google Cloud projects, adaptive thinking levels (LOW/MEDIUM/HIGH),
token optimization, cost telemetry, task decomposition, and resilient error recovery.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from typing import Any

from gemini_db import init_gemini_database
from gemini_error_handler import GeminiErrorHandler
from gemini_key_manager import GeminiKeyManager
from gemini_model_controller import GeminiModelController
from gemini_project_router import GeminiProjectRouter
from gemini_task_decomposer import GeminiTaskDecomposer
from gemini_token_optimizer import GeminiTokenOptimizer
from gemini_usage_tracker import GeminiUsageTracker, UsageRecord

logger = logging.getLogger("zye.gemini.gateway")

try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore
    _GENAI_AVAILABLE = False


class ZyeGeminiGateway:
    """
    Unified Central Gemini Intelligence Gateway.
    The single point of entry for all Gemini LLM interactions across Zye AI.
    """

    _instance: ZyeGeminiGateway | None = None
    _singleton_lock = threading.RLock()

    def __init__(
        self,
        db_path: str | None = None,
        key_manager: GeminiKeyManager | None = None,
        project_router: GeminiProjectRouter | None = None,
        model_controller: GeminiModelController | None = None,
        usage_tracker: GeminiUsageTracker | None = None,
        token_optimizer: GeminiTokenOptimizer | None = None,
        error_handler: GeminiErrorHandler | None = None,
        task_decomposer: GeminiTaskDecomposer | None = None,
    ) -> None:
        self._db_path = db_path
        self._lock = threading.RLock()

        # Database initialization
        init_gemini_database(self._db_path)

        # Initialize subcomponents
        self.key_manager = key_manager or GeminiKeyManager(db_path=self._db_path)
        self.project_router = project_router or GeminiProjectRouter(
            key_manager=self.key_manager,
            db_path=self._db_path,
        )
        self.model_controller = model_controller or GeminiModelController(db_path=self._db_path)
        self.usage_tracker = usage_tracker or GeminiUsageTracker(db_path=self._db_path)
        self.token_optimizer = token_optimizer or GeminiTokenOptimizer()
        self.error_handler = error_handler or GeminiErrorHandler(db_path=self._db_path)
        self.task_decomposer = task_decomposer or GeminiTaskDecomposer(db_path=self._db_path)
        self._live_manager: Any | None = None

        logger.info(
            "ZyeGeminiGateway initialized with model=%s, default_thinking=%s",
            self.model_controller.model_id,
            self.model_controller.thinking_level,
        )

    @classmethod
    def get_instance(cls, db_path: str | None = None) -> ZyeGeminiGateway:
        """Thread-safe singleton accessor."""
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls(db_path=db_path)
            return cls._instance

    # -------------------------------------------------------------------------
    # Core Synchronous Request Execution Pipeline
    # -------------------------------------------------------------------------
    def generate_response(
        self,
        prompt: str | None = None,
        contents: Any = None,
        workload: str = "GENERAL",
        thinking_level: str | None = None,
        tools: list[Any] | None = None,
        system_instruction: str | None = None,
        temperature: float | None = None,
        response_mime_type: str | None = None,
        response_schema: Any = None,
        timeout_seconds: float = 60.0,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Primary synchronous generation pipeline.
        Executes local-first triage, caching, project routing, rate limit validation,
        Gemini API execution, error recovery, and usage tracking.
        """
        req_id = request_id or f"req_{uuid.uuid4().hex[:12]}"
        prompt_text = prompt or ""
        if not prompt_text and contents and isinstance(contents, str):
            prompt_text = contents

        # Step 1: Local-first triage (only for plain text prompts without tools/schemas)
        if prompt_text and not tools and not response_schema:
            can_resolve, local_ans = self.token_optimizer.can_resolve_locally(prompt_text)
            if can_resolve and local_ans is not None:
                logger.info("Request %s resolved locally via TokenOptimizer", req_id)
                return {
                    "text": local_ans,
                    "thoughts": None,
                    "model": "local",
                    "thinking_level": "NONE",
                    "project_id": "LOCAL",
                    "slot_id": 0,
                    "tokens_used": 0,
                    "usage_metadata": {"prompt_token_count": 0, "candidates_token_count": 0, "total_token_count": 0},
                    "status": "LOCAL",
                    "request_id": req_id,
                }

        # Step 2: Response caching check
        effective_thinking = self.model_controller.resolve_thinking_level(
            prompt=prompt_text,
            workload=workload,
            override_level=thinking_level,
        )
        model_id = self.model_controller.model_id
        cache_key = ""
        if prompt_text and not tools and not response_schema:
            cache_key = self.token_optimizer.generate_cache_key(
                prompt=prompt_text,
                model_id=model_id,
                thinking_level=effective_thinking,
                system_instruction=system_instruction or self.model_controller.system_instruction,
            )
            cached_text = self.token_optimizer.get_cached_response(cache_key)
            if cached_text:
                logger.info("Request %s resolved from cache", req_id)
                self.usage_tracker.record_event(UsageRecord(
                    request_id=req_id,
                    workload_id=workload,
                    module_name="gateway",
                    project_id="CACHE",
                    key_alias="CACHE",
                    model_id=model_id,
                    thinking_level=effective_thinking,
                    status="CACHED",
                    prompt_hash=cache_key[:16],
                ))
                return {
                    "text": cached_text,
                    "thoughts": None,
                    "model": model_id,
                    "thinking_level": effective_thinking,
                    "project_id": "CACHE",
                    "slot_id": 0,
                    "tokens_used": 0,
                    "usage_metadata": {"cached_content_token_count": 0},
                    "status": "CACHED",
                    "request_id": req_id,
                }

        # Step 3: Workload Routing to dedicated project slot
        slot_id = self.project_router.route_workload(workload)
        slot = self.key_manager.get_slot(slot_id)
        project_id = (slot.project_id if (slot and slot.project_id) else f"zye-project-{slot_id:02d}")

        # Step 4: Check Rate Limits for this dedicated slot (NO cross-project switching!)
        is_avail, reason = self.project_router.is_slot_available(slot_id)
        if not is_avail:
            logger.warning("Project slot %d unavailable: %s", slot_id, reason)
            return {
                "text": f"Service temporarily busy for {workload}: {reason}",
                "thoughts": None,
                "model": model_id,
                "thinking_level": effective_thinking,
                "project_id": project_id,
                "slot_id": slot_id,
                "tokens_used": 0,
                "usage_metadata": {},
                "status": "RATE_LIMITED",
                "error": reason,
                "request_id": req_id,
            }

        # Step 5: Check Budget
        budget_ok, budget_reason = self.usage_tracker.check_budget(project_id)
        if not budget_ok:
            logger.warning("Token budget exceeded for project %s: %s", project_id, budget_reason)
            return {
                "text": f"Token budget exceeded: {budget_reason}",
                "thoughts": None,
                "model": model_id,
                "thinking_level": effective_thinking,
                "project_id": project_id,
                "slot_id": slot_id,
                "tokens_used": 0,
                "usage_metadata": {},
                "status": "BUDGET_EXCEEDED",
                "error": budget_reason,
                "request_id": req_id,
            }

        # Step 6: Get genai.Client
        client = self.key_manager.get_client(slot_id)
        if not client:
            err_msg = f"No active Gemini client configured for slot {slot_id} ({workload})"
            logger.error(err_msg)
            return {
                "text": err_msg,
                "thoughts": None,
                "model": model_id,
                "thinking_level": effective_thinking,
                "project_id": project_id,
                "slot_id": slot_id,
                "tokens_used": 0,
                "usage_metadata": {},
                "status": "AUTH_FAILED",
                "error": err_msg,
                "request_id": req_id,
            }

        # Step 7: Build Generation Config
        compressed_prompt = self.token_optimizer.compress_prompt(prompt_text) if prompt_text else ""
        content_payload = contents if contents is not None else compressed_prompt

        config = self.model_controller.get_generate_content_config(
            prompt=compressed_prompt,
            workload=workload,
            override_level=thinking_level,
            tools=tools,
            system_instruction=system_instruction,
            temperature=temperature,
            response_mime_type=response_mime_type,
            response_schema=response_schema,
        )

        # Step 8: Execution with retry loop (on the SAME slot only)
        retries = 0
        max_retries = self.error_handler.max_retries
        t0 = time.time()

        while retries <= max_retries:
            try:
                self.project_router.record_request_start(
                    slot_id=slot_id,
                    estimated_tokens=self.token_optimizer.estimate_tokens(compressed_prompt),
                )

                # API Invocation
                response = client.models.generate_content(
                    model=model_id,
                    contents=content_payload,
                    config=config,
                )

                duration = time.time() - t0

                # Extract content and thoughts
                generated_text = ""
                thoughts_text = ""
                function_calls = getattr(response, "function_calls", None)

                # Extract parts and thoughts if candidates present
                candidates = getattr(response, "candidates", None)
                if candidates and len(candidates) > 0:
                    cand = candidates[0]
                    content_obj = getattr(cand, "content", None)
                    parts = getattr(content_obj, "parts", None)
                    if parts:
                        for p in parts:
                            if getattr(p, "thought", False):
                                thoughts_text += getattr(p, "text", "") or ""
                            else:
                                generated_text += getattr(p, "text", "") or ""

                if not generated_text:
                    generated_text = getattr(response, "text", "") or ""

                # Extract usage metadata
                usage_meta = getattr(response, "usage_metadata", None)
                input_tokens = getattr(usage_meta, "prompt_token_count", 0) or 0
                output_tokens = getattr(usage_meta, "candidates_token_count", 0) or 0
                thinking_tokens = getattr(usage_meta, "thinking_token_count", 0) or 0
                cached_tokens = getattr(usage_meta, "cached_content_token_count", 0) or 0
                total_tokens = getattr(usage_meta, "total_token_count", 0) or (input_tokens + output_tokens)

                # Persist usage telemetry
                self.usage_tracker.record_event(UsageRecord(
                    request_id=req_id,
                    workload_id=workload,
                    module_name="gateway",
                    project_id=project_id,
                    key_alias=f"PROJECT_{slot_id:02d}",
                    model_id=model_id,
                    thinking_level=effective_thinking,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    thinking_tokens=thinking_tokens,
                    total_tokens=total_tokens,
                    cached_tokens=cached_tokens,
                    duration_seconds=duration,
                    status="SUCCESS",
                    prompt_hash=cache_key[:16] if cache_key else None,
                ))

                self.key_manager.record_usage(
                    slot_id=slot_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    thinking_tokens=thinking_tokens,
                    success=True,
                )

                # Cache response if applicable
                if cache_key and generated_text and not function_calls:
                    self.token_optimizer.store_cached_response(cache_key, generated_text)

                return {
                    "text": generated_text,
                    "thoughts": thoughts_text if thoughts_text else None,
                    "function_calls": function_calls,
                    "response": response,
                    "model": model_id,
                    "thinking_level": effective_thinking,
                    "project_id": project_id,
                    "slot_id": slot_id,
                    "tokens_used": total_tokens,
                    "usage_metadata": {
                        "prompt_token_count": input_tokens,
                        "candidates_token_count": output_tokens,
                        "thinking_token_count": thinking_tokens,
                        "cached_content_token_count": cached_tokens,
                        "total_token_count": total_tokens,
                    },
                    "duration_seconds": duration,
                    "status": "SUCCESS",
                    "request_id": req_id,
                }

            except Exception as exc:
                retries += 1
                error_plan = self.error_handler.evaluate_error(
                    exc=exc,
                    slot_id=slot_id,
                    retry_count=retries - 1,
                    request_id=req_id,
                    project_id=project_id,
                )

                if error_plan.status_code == 429:
                    self.project_router.mark_rate_limited(slot_id, error_plan.retry_delay_seconds)
                elif error_plan.status_code in (401, 403):
                    self.key_manager.mark_auth_failed(slot_id)

                self.key_manager.record_usage(slot_id=slot_id, success=False)

                if error_plan.retryable and retries <= max_retries:
                    logger.warning(
                        "Request %s failed with %s. Retrying slot %d in %.2fs (attempt %d/%d)",
                        req_id,
                        error_plan.error_type,
                        slot_id,
                        error_plan.retry_delay_seconds,
                        retries,
                        max_retries,
                    )
                    time.sleep(error_plan.retry_delay_seconds)
                    continue

                # Terminal failure
                duration = time.time() - t0
                self.usage_tracker.record_event(UsageRecord(
                    request_id=req_id,
                    workload_id=workload,
                    module_name="gateway",
                    project_id=project_id,
                    key_alias=f"PROJECT_{slot_id:02d}",
                    model_id=model_id,
                    thinking_level=effective_thinking,
                    duration_seconds=duration,
                    status="FAILED",
                    error_category=error_plan.error_type,
                ))

                logger.error("Terminal failure for request %s on slot %d: %s", req_id, slot_id, error_plan.sanitized_message)
                return {
                    "text": f"Error: {error_plan.sanitized_message}",
                    "thoughts": None,
                    "model": model_id,
                    "thinking_level": effective_thinking,
                    "project_id": project_id,
                    "slot_id": slot_id,
                    "tokens_used": 0,
                    "usage_metadata": {},
                    "duration_seconds": duration,
                    "status": "FAILED",
                    "error": error_plan.sanitized_message,
                    "error_type": error_plan.error_type,
                    "request_id": req_id,
                }

        return {
            "text": "Max retries exceeded",
            "status": "FAILED",
            "request_id": req_id,
        }

    # -------------------------------------------------------------------------
    # Core Asynchronous Request Execution Pipeline
    # -------------------------------------------------------------------------
    async def generate_response_async(
        self,
        prompt: str | None = None,
        contents: Any = None,
        workload: str = "GENERAL",
        thinking_level: str | None = None,
        tools: list[Any] | None = None,
        system_instruction: str | None = None,
        temperature: float | None = None,
        response_mime_type: str | None = None,
        response_schema: Any = None,
        timeout_seconds: float = 60.0,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Async variant running synchronous pipeline in dedicated thread pool."""
        return await asyncio.to_thread(
            self.generate_response,
            prompt=prompt,
            contents=contents,
            workload=workload,
            thinking_level=thinking_level,
            tools=tools,
            system_instruction=system_instruction,
            temperature=temperature,
            response_mime_type=response_mime_type,
            response_schema=response_schema,
            timeout_seconds=timeout_seconds,
            request_id=request_id,
        )

    # -------------------------------------------------------------------------
    # Drop-in Compatibility Helper for client.models.generate_content
    # -------------------------------------------------------------------------
    def generate_content(
        self,
        model: str | None = None,
        contents: Any = None,
        config: Any = None,
        workload: str = "GENERAL",
        **kwargs: Any,
    ) -> Any:
        """
        Drop-in replacement for client.models.generate_content.
        Returns raw Google GenAI GenerateContentResponse if successful, or raises on failure.
        """
        slot_id = self.project_router.route_workload(workload)
        client = self.key_manager.get_client(slot_id)
        if not client:
            raise RuntimeError(f"No configured Gemini client for slot {slot_id} ({workload})")

        effective_model = model or self.model_controller.model_id
        effective_config = config
        if effective_config is None:
            effective_config = self.model_controller.get_generate_content_config(workload=workload)

        return client.models.generate_content(
            model=effective_model,
            contents=contents,
            config=effective_config,
            **kwargs,
        )

    # -------------------------------------------------------------------------
    # High-Level Structured Workload Helpers
    # -------------------------------------------------------------------------
    def generate_structured_response(
        self,
        prompt: str,
        response_schema: Any,
        workload: str = "GENERAL",
        thinking_level: str = "MEDIUM",
    ) -> dict[str, Any]:
        """Generate strictly structured JSON adhering to a Pydantic or schema definition."""
        return self.generate_response(
            prompt=prompt,
            workload=workload,
            thinking_level=thinking_level,
            response_mime_type="application/json",
            response_schema=response_schema,
        )

    def classify_content(self, content: str, categories: list[str]) -> str:
        """Classify input text into one of several predefined categories."""
        prompt = (
            f"Classify the following text into exactly ONE of these categories: {', '.join(categories)}.\n"
            f"Reply with ONLY the category name.\n\n"
            f"Text: {content}"
        )
        res = self.generate_response(prompt=prompt, workload="FAST_ROUTING", thinking_level="LOW")
        ans = res.get("text", "").strip()
        for cat in categories:
            if cat.lower() in ans.lower():
                return cat
        return categories[0] if categories else "UNKNOWN"

    def summarize_content(self, content: str, max_words: int = 100) -> str:
        """Summarize text concisely within word budget."""
        prompt = f"Summarize the following content in under {max_words} words concisely:\n\n{content}"
        res = self.generate_response(prompt=prompt, workload="FAST_ROUTING", thinking_level="LOW")
        return res.get("text", "").strip()

    def conduct_research(self, query: str) -> dict[str, Any]:
        """Execute deep research query using Slot 7 / Research workload."""
        return self.generate_response(
            prompt=f"Conduct thorough research and analysis on: {query}",
            workload="RESEARCH_SUBTASK",
            thinking_level="HIGH",
        )

    def analyze_data(self, data_description: str) -> dict[str, Any]:
        """Analyze structured data or schemas."""
        return self.generate_response(
            prompt=f"Perform data analysis and structural evaluation for: {data_description}",
            workload="DATA_INTEGRATION",
            thinking_level="MEDIUM",
        )

    def execute_authorized_task(self, task_description: str) -> dict[str, Any]:
        """Execute general authorized task with appropriate thinking configuration."""
        return self.generate_response(
            prompt=task_description,
            workload="USER_WORKFLOW",
            thinking_level="MEDIUM",
        )

    async def decompose_and_execute(
        self,
        task_description: str,
        requested_roles: list[str] | None = None,
        max_concurrency: int = 1,
    ) -> Any:
        """Decompose complex task into logical subtasks and execute with bounded parallelism."""
        return await self.task_decomposer.execute_subtasks(
            task_description=task_description,
            gateway=self,
            requested_roles=requested_roles,
            max_concurrency=max_concurrency,
        )

    # -------------------------------------------------------------------------
    # Observability and Administration
    # -------------------------------------------------------------------------
    def get_health_status(self) -> dict[str, Any]:
        """Return comprehensive health assessment across all 7 slots and subsystems."""
        slots = self.key_manager.get_all_slots()
        healthy_count = sum(1 for s in slots if s.key_health == "HEALTHY")
        stats = self.usage_tracker.get_token_statistics()

        return {
            "model_id": self.model_controller.model_id,
            "thinking_level": self.model_controller.thinking_level,
            "thinking_mode": self.model_controller.thinking_mode,
            "total_slots": len(slots),
            "healthy_slots": healthy_count,
            "all_healthy": (healthy_count == len(slots)),
            "token_stats": stats,
            "slots": [
                {
                    "slot_id": s.slot_id,
                    "account": s.account_alias,
                    "project": s.project_alias,
                    "health": s.key_health,
                    "auth": s.auth_status,
                }
                for s in slots
            ],
        }

    def get_usage_statistics(self) -> dict[str, Any]:
        return self.usage_tracker.get_token_statistics()

    def set_thinking_level(self, level: str, mode: str = "MANUAL") -> bool:
        return self.model_controller.set_thinking_level(level, mode=mode)

    def get_thinking_level(self) -> str:
        return self.model_controller.get_thinking_level()

    def set_model_id(self, model_id: str) -> bool:
        return self.model_controller.set_model_id(model_id)

    def get_model_id(self) -> str:
        return self.model_controller.get_model_id()

    # -------------------------------------------------------------------------
    # Gemini Live Native Audio Integration (Section 08, 09, 10, 17)
    # -------------------------------------------------------------------------
    def get_live_manager(
        self,
        config: Any = None,
        tool_dispatcher: Any = None,
        tool_declarations: list[Any] | None = None,
        audio_capture_engine: Any = None,
    ) -> Any:
        """Obtain or initialize the managed Gemini Live session controller."""
        with self._lock:
            if self._live_manager is None:
                from zye_gemini_live import ZyeGeminiLiveManager, GeminiLiveConfig
                live_cfg = config or GeminiLiveConfig()
                self._live_manager = ZyeGeminiLiveManager(
                    config=live_cfg,
                    key_manager=self.key_manager,
                    gateway=self,
                    tool_dispatcher=tool_dispatcher,
                    tool_declarations=tool_declarations,
                    audio_capture_engine=audio_capture_engine,
                )
            return self._live_manager

    async def start_gemini_live(
        self,
        config: Any = None,
        tool_dispatcher: Any = None,
        tool_declarations: list[Any] | None = None,
        audio_capture_engine: Any = None,
    ) -> Any:
        """Start the managed Gemini Live continuous conversation session."""
        mgr = self.get_live_manager(
            config=config,
            tool_dispatcher=tool_dispatcher,
            tool_declarations=tool_declarations,
            audio_capture_engine=audio_capture_engine,
        )
        return mgr

    def stop_gemini_live(self) -> None:
        """Stop active Gemini Live session."""
        with self._lock:
            if self._live_manager is not None:
                self._live_manager.stop()
                self._live_manager = None

    def get_gemini_live_status(self) -> dict[str, Any]:
        """Return real-time status of Gemini Live subsystem."""
        with self._lock:
            if self._live_manager is not None:
                return self._live_manager.get_status()
            return {"enabled": False, "state": "DISABLED", "message": "Live manager not initialized"}

    def send_live_audio(self, pcm_bytes: bytes) -> None:
        """Push microphone PCM audio frames directly to active Gemini Live session."""
        with self._lock:
            if self._live_manager is not None:
                self._live_manager.push_microphone_audio(pcm_bytes)

    def is_gemini_live_active(self) -> bool:
        """Check if Gemini Live session is currently connected and active."""
        with self._lock:
            if self._live_manager is not None:
                return self._live_manager.state.value in ("CONNECTED", "LISTENING", "RESPONDING", "PROCESSING")
            return False


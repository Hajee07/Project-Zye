"""
Gemini Task Decomposer — Zye Multi-Project Gemini Intelligence Infrastructure v2.0 (Section 10).
Decomposes complex engineering and research requests into up to 7 distinct logical worker roles.
Executes subtasks with bounded AsyncIO concurrency and aggregates results through GeminiResultAggregator.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from gemini_db import get_db_connection, init_gemini_database
from gemini_result_aggregator import AggregatedResult, GeminiResultAggregator, SubtaskResult

logger = logging.getLogger("zye.gemini.decomposer")

ALL_LOGICAL_ROLES = [
    "TECHNICAL",
    "ARCHITECTURE",
    "DATA",
    "SECURITY",
    "RESEARCH",
    "ALTERNATIVES",
    "QUALITY",
]

ROLE_PROMPTS = {
    "TECHNICAL": "Analyze technical implementation details, syntax, libraries, and function mechanics for: ",
    "ARCHITECTURE": "Analyze system architecture, component relationships, dependencies, and modularity for: ",
    "DATA": "Analyze data schemas, database tables, persistence, and state transitions for: ",
    "SECURITY": "Analyze cybersecurity threats, authentication, secrets, and injection vulnerabilities for: ",
    "RESEARCH": "Research official documentation, external API requirements, and domain best practices for: ",
    "ALTERNATIVES": "Identify alternative approaches, trade-offs, and fallback strategies for: ",
    "QUALITY": "Analyze test coverage, edge cases, failure recovery, and performance optimization for: ",
}


class GeminiTaskDecomposer:
    """
    Decomposes tasks into logical worker roles and executes them with bounded concurrency.
    """

    def __init__(
        self,
        db_path: str | None = None,
        default_concurrency: int = 1,
        max_workers: int = 7,
    ) -> None:
        self._db_path = db_path
        self._default_concurrency = max(1, min(default_concurrency, max_workers))
        self._max_workers = max_workers
        self._aggregator = GeminiResultAggregator()
        self._lock = threading.RLock()
        init_gemini_database(self._db_path)

    @property
    def aggregator(self) -> GeminiResultAggregator:
        return self._aggregator

    def decompose(
        self,
        task_description: str,
        requested_roles: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """
        Decompose a high-level goal into role-specific subtasks.
        Returns a list of dicts with 'role' and 'subtask_prompt'.
        """
        roles = requested_roles or ALL_LOGICAL_ROLES
        subtasks = []
        for role in roles:
            clean_role = role.strip().upper()
            prefix = ROLE_PROMPTS.get(clean_role, f"Analyze {clean_role} aspects of: ")
            subtasks.append({
                "role": clean_role,
                "prompt": f"{prefix}{task_description}",
            })
        return subtasks

    async def execute_subtasks(
        self,
        task_description: str,
        gateway: Any,
        requested_roles: list[str] | None = None,
        max_concurrency: int | None = None,
        timeout_seconds: float = 30.0,
    ) -> AggregatedResult:
        """
        Execute decomposed subtasks concurrently using AsyncIO Semaphore.
        Bounds active parallel workers to prevent quota contention.
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        concurrency = max_concurrency or self._default_concurrency
        semaphore = asyncio.Semaphore(concurrency)

        subtask_specs = self.decompose(task_description, requested_roles)
        subtask_count = len(subtask_specs)

        # Log task start in DB
        self._record_task_start(task_id, subtask_count, concurrency)

        results: list[SubtaskResult] = []

        async def _run_worker(spec: dict[str, str]) -> SubtaskResult:
            role = spec["role"]
            prompt = spec["prompt"]
            job_id = f"job_{uuid.uuid4().hex[:8]}"
            t0 = time.time()

            self._record_job_start(job_id, task_id, role, slot_id=7)

            async with semaphore:
                try:
                    # Execute worker prompt via Gateway Slot 7 (Task Decomposition Workload)
                    coro = gateway.generate_response(
                        prompt=prompt,
                        workload="TASK_DECOMPOSITION",
                        thinking_level="LOW",  # keep workers nimble
                    )
                    if inspect.isawaitable(coro):
                        response = await asyncio.wait_for(coro, timeout=timeout_seconds)
                    else:
                        response = coro
                    duration = time.time() - t0
                    res = SubtaskResult(
                        worker_role=role,
                        content=response.get("text", ""),
                        status="SUCCESS",
                        tokens_used=response.get("tokens_used", 0),
                        duration_seconds=duration,
                    )
                    self._record_job_complete(job_id, "SUCCESS", res.tokens_used, None)
                    return res
                except asyncio.TimeoutError:
                    duration = time.time() - t0
                    err = f"Worker timed out after {timeout_seconds}s"
                    logger.warning("Worker %s timed out for task %s", role, task_id)
                    res = SubtaskResult(
                        worker_role=role,
                        content="",
                        status="TIMED_OUT",
                        duration_seconds=duration,
                        error=err,
                    )
                    self._record_job_complete(job_id, "TIMED_OUT", 0, err)
                    return res
                except Exception as exc:
                    duration = time.time() - t0
                    err = str(exc)
                    logger.warning("Worker %s failed: %s", role, err)
                    res = SubtaskResult(
                        worker_role=role,
                        content="",
                        status="FAILED",
                        duration_seconds=duration,
                        error=err,
                    )
                    self._record_job_complete(job_id, "FAILED", 0, err)
                    return res

        # Run with asyncio.gather
        tasks = [_run_worker(spec) for spec in subtask_specs]
        results = await asyncio.gather(*tasks)

        # Aggregate synthesis
        aggregated = self._aggregator.aggregate(task_id, list(results))

        # Log task completion in DB
        self._record_task_complete(
            task_id,
            status="SUCCESS" if aggregated.all_successful else "PARTIAL_SUCCESS",
            total_tokens=aggregated.total_tokens_used,
            duration=aggregated.total_duration_seconds,
        )

        return aggregated

    def _record_task_start(self, task_id: str, subtasks_count: int, workers_count: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        try:
            conn = get_db_connection(self._db_path)
            try:
                with conn:
                    conn.execute("""
                        INSERT INTO gemini_task_history
                        (task_id, complexity, subtasks_count, parallel_workers_count, status, total_tokens, duration_seconds, created_at)
                        VALUES (?, 'MODERATE', ?, ?, 'RUNNING', 0, 0.0, ?);
                    """, (task_id, subtasks_count, workers_count, now))
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Error recording task start: %s", exc)

    def _record_task_complete(self, task_id: str, status: str, total_tokens: int, duration: float) -> None:
        try:
            conn = get_db_connection(self._db_path)
            try:
                with conn:
                    conn.execute("""
                        UPDATE gemini_task_history
                        SET status = ?, total_tokens = ?, duration_seconds = ?
                        WHERE task_id = ?;
                    """, (status, total_tokens, duration, task_id))
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Error recording task completion: %s", exc)

    def _record_job_start(self, job_id: str, task_id: str, role: str, slot_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        try:
            conn = get_db_connection(self._db_path)
            try:
                with conn:
                    conn.execute("""
                        INSERT INTO gemini_parallel_jobs
                        (job_id, task_id, worker_role, slot_id, status, tokens_used, created_at)
                        VALUES (?, ?, ?, ?, 'RUNNING', 0, ?);
                    """, (job_id, task_id, role, slot_id, now))
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Error recording job start: %s", exc)

    def _record_job_complete(self, job_id: str, status: str, tokens: int, error: str | None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        try:
            conn = get_db_connection(self._db_path)
            try:
                with conn:
                    conn.execute("""
                        UPDATE gemini_parallel_jobs
                        SET status = ?, tokens_used = ?, error = ?, completed_at = ?
                        WHERE job_id = ?;
                    """, (status, tokens, error, now, job_id))
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Error recording job completion: %s", exc)

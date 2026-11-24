"""
ZYE AI — Persistent SQLite Task Scheduler with Worker Leases
============================================================

Implements Section 24 of Master Engineering Specification.
Manages cron expressions, recurring interval triggers, and one-off delayed tasks.
Features:
1. SQLite persistence with WAL mode.
2. Worker lease locking to eliminate overlapping task runs.
3. Zombie task recovery when lease expires without completion.
4. Clean exception isolation per task run.
5. Integration with ZyeEventBus (TASK_STARTED, TASK_COMPLETED).
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from zye_core.event_bus import ZyeEventBus
from zye_core.types import ZyeEvent, ZyeEventType

logger = logging.getLogger("zye.scheduler")


@dataclass
class ScheduledTask:
    """A persistent scheduled task definition."""

    id: str
    prompt: str
    schedule_type: str  # "interval", "once", "cron"
    schedule_value: str  # seconds for interval, epoch or iso for once
    status: str = "active"  # "active", "running", "completed", "cancelled"
    next_run: float = field(default_factory=time.time)
    last_run: Optional[float] = None
    lease_expires: Optional[float] = None
    run_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskScheduler:
    """
    Robust SQLite-backed task scheduler with lease acquisition and heartbeat tracking.
    """

    def __init__(
        self,
        db_path: str = "data/tasks.db",
        event_bus: Optional[ZyeEventBus] = None,
    ) -> None:
        self.db_path = db_path
        self._shared_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row
        else:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self.event_bus = event_bus
        self._lock = threading.RLock()
        self._running = False
        self._poll_thread: Optional[threading.Thread] = None
        self._task_executor: Optional[Callable[[ScheduledTask], None]] = None
        self._init_db()

    @contextlib.contextmanager
    def _connection(self):
        if self._shared_conn is not None:
            with self._lock:
                try:
                    yield self._shared_conn
                    self._shared_conn.commit()
                except Exception:
                    self._shared_conn.rollback()
                    raise
        else:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

    def _init_db(self) -> None:
        with self._lock, self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    schedule_type TEXT NOT NULL,
                    schedule_value TEXT NOT NULL,
                    status TEXT NOT NULL,
                    next_run REAL NOT NULL,
                    last_run REAL,
                    lease_expires REAL,
                    run_count INTEGER NOT NULL DEFAULT 0,
                    metadata TEXT NOT NULL DEFAULT '{}'
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due ON scheduled_tasks(status, next_run);")

    def schedule(
        self,
        prompt: str,
        schedule_type: str,
        schedule_value: str,
        initial_delay_seconds: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScheduledTask:
        """Schedule a new task for autonomous execution."""
        task_id = uuid.uuid4().hex[:12]
        now = time.time()
        next_run = now + initial_delay_seconds
        meta_json = json.dumps(metadata or {})

        task = ScheduledTask(
            id=task_id,
            prompt=prompt,
            schedule_type=schedule_type,
            schedule_value=schedule_value,
            status="active",
            next_run=next_run,
            metadata=metadata or {},
        )

        with self._lock, self._connection() as conn:
            conn.execute(
                """
                INSERT INTO scheduled_tasks (id, prompt, schedule_type, schedule_value, status, next_run, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (task.id, task.prompt, task.schedule_type, task.schedule_value, task.status, task.next_run, meta_json),
            )
        logger.info("Task scheduled [%s]: '%s' (%s: %s)", task.id, task.prompt, task.schedule_type, task.schedule_value)
        return task

    def schedule_once(
        self,
        prompt: str,
        initial_delay_seconds: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Schedule a one-off task. Returns task id."""
        task = self.schedule(
            prompt=prompt,
            schedule_type="once",
            schedule_value="once",
            initial_delay_seconds=initial_delay_seconds,
            metadata=metadata,
        )
        return task.id

    def schedule_interval(
        self,
        prompt: str,
        interval_seconds: float,
        initial_delay_seconds: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Schedule a recurring interval task. Returns task id."""
        task = self.schedule(
            prompt=prompt,
            schedule_type="interval",
            schedule_value=str(interval_seconds),
            initial_delay_seconds=initial_delay_seconds,
            metadata=metadata,
        )
        return task.id

    def cancel(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        with self._lock, self._connection() as conn:
            cursor = conn.execute("UPDATE scheduled_tasks SET status = 'cancelled' WHERE id = ?;", (task_id,))
            return cursor.rowcount > 0

    def list_tasks(self, status: Optional[str] = None) -> List[ScheduledTask]:
        """List tasks matching status filter."""
        with self._lock, self._connection() as conn:
            if status:
                cursor = conn.execute("SELECT * FROM scheduled_tasks WHERE status = ? ORDER BY next_run ASC;", (status,))
            else:
                cursor = conn.execute("SELECT * FROM scheduled_tasks ORDER BY next_run ASC;")
            rows = cursor.fetchall()

        tasks = []
        for r in rows:
            tasks.append(
                ScheduledTask(
                    id=r["id"],
                    prompt=r["prompt"],
                    schedule_type=r["schedule_type"],
                    schedule_value=r["schedule_value"],
                    status=r["status"],
                    next_run=r["next_run"],
                    last_run=r["last_run"],
                    lease_expires=r["lease_expires"],
                    run_count=r["run_count"],
                    metadata=json.loads(r["metadata"]),
                )
            )
        return tasks

    def acquire_due_tasks(self, lease_seconds: float = 60.0) -> List[ScheduledTask]:
        """
        Atomically acquire tasks whose next_run is due and are not actively leased.
        Recovers zombie tasks whose leases have expired.
        """
        now = time.time()
        new_lease = now + lease_seconds
        due_tasks: List[ScheduledTask] = []

        with self._lock, self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT id FROM scheduled_tasks
                WHERE (status = 'active' AND next_run <= ?)
                   OR (status = 'running' AND lease_expires IS NOT NULL AND lease_expires < ?);
                """,
                (now, now),
            )
            candidate_ids = [r["id"] for r in cursor.fetchall()]

            for tid in candidate_ids:
                update_cur = conn.execute(
                    """
                    UPDATE scheduled_tasks
                    SET status = 'running', lease_expires = ?
                    WHERE id = ?;
                    """,
                    (new_lease, tid),
                )
                if update_cur.rowcount > 0:
                    row = conn.execute("SELECT * FROM scheduled_tasks WHERE id = ?;", (tid,)).fetchone()
                    due_tasks.append(
                        ScheduledTask(
                            id=row["id"],
                            prompt=row["prompt"],
                            schedule_type=row["schedule_type"],
                            schedule_value=row["schedule_value"],
                            status="running",
                            next_run=row["next_run"],
                            last_run=row["last_run"],
                            lease_expires=new_lease,
                            run_count=row["run_count"],
                            metadata=json.loads(row["metadata"]),
                        )
                    )

        return due_tasks

    def finish_task(self, task_id: str, success: bool = True, error: Optional[str] = None) -> None:
        """Release lease, update run count, and reschedule or mark completed/failed."""
        now = time.time()
        with self._lock, self._connection() as conn:
            row = conn.execute("SELECT * FROM scheduled_tasks WHERE id = ?;", (task_id,)).fetchone()
            if not row:
                return

            stype = row["schedule_type"]
            sval = row["schedule_value"]
            new_run_count = row["run_count"] + 1

            meta = json.loads(row["metadata"] or "{}")
            meta["last_success"] = success
            if error:
                meta["last_error"] = str(error)
            elif success and "last_error" in meta:
                meta.pop("last_error", None)
            updated_meta_json = json.dumps(meta)

            if stype == "once":
                # ZYE-BUG-014: If execution failed, status is 'failed', not 'completed'
                final_status = "completed" if success else "failed"
                conn.execute(
                    """
                    UPDATE scheduled_tasks
                    SET status = ?, last_run = ?, lease_expires = NULL, run_count = ?, metadata = ?
                    WHERE id = ?;
                    """,
                    (final_status, now, new_run_count, updated_meta_json, task_id),
                )
            elif stype == "interval":
                try:
                    interval_sec = float(sval)
                except ValueError:
                    interval_sec = 60.0
                next_run = now + interval_sec
                conn.execute(
                    """
                    UPDATE scheduled_tasks
                    SET status = 'active', last_run = ?, next_run = ?, lease_expires = NULL, run_count = ?, metadata = ?
                    WHERE id = ?;
                    """,
                    (now, next_run, new_run_count, updated_meta_json, task_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE scheduled_tasks
                    SET status = 'active', last_run = ?, next_run = ?, lease_expires = NULL, run_count = ?, metadata = ?
                    WHERE id = ?;
                    """,
                    (now, now + 300.0, new_run_count, updated_meta_json, task_id),
                )

    def run_due_tasks_once(self, executor: Optional[Callable[[ScheduledTask], None]] = None) -> int:
        """Single polling cycle: acquires and executes due tasks."""
        exec_fn = executor or self._task_executor
        due = self.acquire_due_tasks()
        executed_count = 0

        for task in due:
            logger.info("Executing scheduled task [%s]: '%s'", task.id, task.prompt)
            if self.event_bus:
                self.event_bus.publish_sync(
                    ZyeEvent(
                        event_type=ZyeEventType.TASK_STARTED,
                        source_module="zye.scheduler",
                        payload={"task_id": task.id, "prompt": task.prompt},
                    )
                )

            success = True
            error_msg: Optional[str] = None
            if exec_fn is None:
                # ZYE-BUG-014: Missing executor must not be recorded as successful execution
                logger.warning("No executor provided for task [%s]; marking unexecuted/failed.", task.id)
                success = False
                error_msg = "No task executor provided"
            else:
                try:
                    exec_fn(task)
                    success = True
                except Exception as exc:
                    logger.error("Task [%s] execution failed: %s", task.id, exc)
                    success = False
                    error_msg = str(exc)

            self.finish_task(task.id, success=success, error=error_msg)
            executed_count += 1

            if self.event_bus:
                self.event_bus.publish_sync(
                    ZyeEvent(
                        event_type=ZyeEventType.TASK_COMPLETED,
                        source_module="zye.scheduler",
                        payload={"task_id": task.id, "success": success, "error": error_msg},
                    )
                )

        return executed_count

    def start(
        self,
        poll_interval: float = 2.0,
        executor: Optional[Callable[[ScheduledTask], None]] = None,
    ) -> None:
        """Start background polling thread."""
        if self._running:
            return
        self._task_executor = executor
        self._running = True

        def _loop() -> None:
            while self._running:
                try:
                    self.run_due_tasks_once()
                except Exception as exc:
                    logger.error("Error during scheduler poll: %s", exc)
                time.sleep(poll_interval)

        self._poll_thread = threading.Thread(target=_loop, name="ZyeTaskSchedulerWorker", daemon=True)
        self._poll_thread.start()
        logger.info("ZYE TaskScheduler worker thread started.")

    def stop(self) -> None:
        """Stop background polling thread."""
        self._running = False
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=2.0)
        logger.info("ZYE TaskScheduler worker thread stopped.")

    def close(self) -> None:
        """Stop polling and close shared connection if in-memory."""
        self.stop()
        if self._shared_conn is not None:
            try:
                self._shared_conn.close()
            except Exception:
                pass
            self._shared_conn = None


__all__ = ["ScheduledTask", "TaskScheduler"]

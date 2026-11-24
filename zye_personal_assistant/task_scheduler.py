"""
Task Scheduling and Automatic Timeblocking Engine for Zye Personal Assistant (Day 14 & Day 29).
Provides priority-ordered task queues, deadline sorting, idempotency, duplicate prevention,
and intelligent conflict-free calendar timeblocking with configurable buffers.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
import zoneinfo

from zye_personal_assistant.database import get_db_connection, init_assistant_database
from zye_personal_assistant.safety_gateway import SafetyGateway

logger = logging.getLogger("zye.personal_assistant.tasks")

VALID_PRIORITIES = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


class TaskScheduler:
    def __init__(
        self,
        db_path: str | Path | None = None,
        default_timezone: str = "Asia/Kolkata",
        safety_gateway: Optional[SafetyGateway] = None,
    ) -> None:
        self._db_path = db_path
        self._default_tz = default_timezone
        self._safety = safety_gateway or SafetyGateway(db_path=db_path)
        init_assistant_database(self._db_path)

    def _get_now_local(self) -> datetime:
        return datetime.now(zoneinfo.ZoneInfo(self._default_tz))

    def add_task(
        self,
        title: str,
        priority: str = "MEDIUM",
        due_iso: str = "",
        est_minutes: int = 45,
        project_name: str = "General",
    ) -> dict[str, Any]:
        """Add a new task to the task queue with strict priority validation."""
        clean_title = title.strip()
        if not clean_title:
            return {"status": "ERROR", "message": "Task title cannot be empty."}

        clean_priority = priority.strip().upper()
        if clean_priority not in VALID_PRIORITIES:
            return {
                "status": "ERROR",
                "error_code": "TASK_INVALID_PRIORITY",
                "message": f"Invalid priority '{priority}'. Must be one of: {', '.join(VALID_PRIORITIES.keys())}.",
            }

        # Validate due_iso if provided
        if due_iso.strip():
            try:
                datetime.fromisoformat(due_iso.strip())
            except ValueError:
                return {
                    "status": "TASK_INVALID_DEADLINE",
                    "message": f"Invalid due date format '{due_iso}'. Must be valid ISO 8601 (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).",
                }

        now_str = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection(self._db_path)
        try:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO tasks
                    (title, priority, due_iso, est_minutes, project_name, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 'PENDING', ?, ?);
                    """,
                    (clean_title, clean_priority, due_iso.strip(), est_minutes, project_name.strip(), now_str, now_str),
                )
                task_id = cursor.lastrowid
            logger.info("Added task id=%d: '%s' [%s]", task_id, clean_title, clean_priority)
            return {
                "status": "SUCCESS",
                "action": "TASK_ADDED",
                "task_id": task_id,
                "title": clean_title,
                "priority": clean_priority,
                "due_iso": due_iso.strip(),
                "est_minutes": est_minutes,
                "project_name": project_name.strip(),
                "message": f"Task '{clean_title}' added successfully.",
            }
        finally:
            conn.close()

    def list_tasks(self, status: str = "PENDING", limit: int = 50) -> list[dict[str, Any]]:
        """List tasks ordered by priority (CRITICAL > HIGH > MEDIUM > LOW), then deadline."""
        conn = get_db_connection(self._db_path)
        try:
            query = """
                SELECT id, title, priority, due_iso, est_minutes, project_name, status, scheduled_start_iso, scheduled_end_iso, linked_event_id
                FROM tasks
            """
            params: list[Any] = []
            if status.upper() != "ALL":
                query += " WHERE status = ?"
                params.append(status.upper())

            rows = conn.execute(query, params).fetchall()
            tasks = [dict(r) for r in rows]

            # Priority rank then deadline
            tasks.sort(key=lambda t: (
                VALID_PRIORITIES.get(t["priority"].upper(), 99),
                t["due_iso"] or "9999-99-99",
            ))
            return tasks[:limit]
        finally:
            conn.close()

    def complete_task(self, task_id: int) -> dict[str, Any]:
        """Mark a task as completed and update project progress."""
        if not task_id:
            return {"status": "ERROR", "message": "Valid task_id is required."}

        now_str = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection(self._db_path)
        try:
            row = conn.execute("SELECT id, title, project_name, status FROM tasks WHERE id = ?;", (task_id,)).fetchone()
            if not row:
                return {"status": "TASK_NOT_FOUND", "message": f"Task id {task_id} not found."}

            if row["status"] == "COMPLETED":
                return {
                    "status": "TASK_ALREADY_COMPLETED",
                    "task_id": task_id,
                    "title": row["title"],
                    "message": f"Task id {task_id} ('{row['title']}') is already completed.",
                }

            title = row["title"]
            proj_name = row["project_name"]

            with conn:
                conn.execute(
                    "UPDATE tasks SET status = 'COMPLETED', updated_at = ? WHERE id = ?;",
                    (now_str, task_id),
                )
                if proj_name and proj_name != "General":
                    self._update_project_progress(conn, proj_name)

            logger.info("Marked task id=%d completed: '%s'", task_id, title)
            return {
                "status": "SUCCESS",
                "task_id": task_id,
                "title": title,
                "project_name": proj_name,
                "task_status": "COMPLETED",
                "message": f"Task '{title}' marked as COMPLETED.",
            }
        finally:
            conn.close()

    def _update_project_progress(self, conn: Any, project_name: str) -> None:
        """Recalculate project completion percentage from tasks."""
        row = conn.execute(
            """
            SELECT COUNT(*) as total, SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as done
            FROM tasks WHERE project_name = ?;
            """,
            (project_name,),
        ).fetchone()
        if row and row["total"] > 0:
            pct = round((row["done"] / row["total"]) * 100.0, 1)
            conn.execute("UPDATE projects SET completion_percent = ? WHERE name = ?;", (pct, project_name))

    def auto_timeblock_today(
        self,
        buffer_minutes: int = 10,
        work_start_hour: int = 9,
        work_end_hour: int = 18,
        target_date: Optional[str] = None,
        target_date_iso: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Identify free calendar slots and schedule pending tasks by priority.
        Preserves all existing meetings without conflict.
        Enforces idempotency: does not reschedule tasks already scheduled for today.
        """
        eff_target = target_date_iso or target_date
        tz = zoneinfo.ZoneInfo(self._default_tz)
        if eff_target:
            try:
                base_dt = datetime.fromisoformat(eff_target.split("T")[0]).replace(tzinfo=tz)
            except Exception:
                base_dt = self._get_now_local()
            day_start = base_dt.replace(hour=work_start_hour, minute=0, second=0, microsecond=0)
            day_end = base_dt.replace(hour=work_end_hour, minute=0, second=0, microsecond=0)
            cursor = day_start
        else:
            now = self._get_now_local()
            day_start = now.replace(hour=work_start_hour, minute=0, second=0, microsecond=0)
            day_end = now.replace(hour=work_end_hour, minute=0, second=0, microsecond=0)
            cursor = day_start if now >= day_end else max(day_start, now)

        pending_tasks = self.list_tasks(status="PENDING")
        if not pending_tasks:
            return {"status": "NO_TASKS", "message": "No pending tasks to schedule.", "scheduled": []}

        # Negative Brain Audit
        audit = self._safety.authorize_personal_assistant_action_sync(
            action_type="TASK_BULK_TIMEBLOCK",
            task_description=f"Auto-timeblock {len(pending_tasks)} pending tasks for {day_start.strftime('%Y-%m-%d')}",
            proposed_steps=[
                f"Inspect existing events between {day_start.strftime('%I:%M %p')} and {day_end.strftime('%I:%M %p')}",
                f"Allocate non-overlapping slots with {buffer_minutes}m buffer",
            ],
            target_resources=["calendar:today", "tasks:pending"],
        )

        conn = get_db_connection(self._db_path)
        scheduled_list: list[dict[str, Any]] = []
        already_scheduled_list: list[dict[str, Any]] = []
        unscheduled_list: list[dict[str, Any]] = []

        try:
            # Fetch existing events today
            evt_rows = conn.execute(
                """
                SELECT id, start_iso, end_iso FROM events
                WHERE event_status != 'CANCELLED'
                  AND end_iso > ? AND start_iso < ?
                ORDER BY start_iso ASC;
                """,
                (day_start.isoformat(), day_end.isoformat()),
            ).fetchall()

            existing_events: list[tuple[datetime, datetime]] = []
            for r in evt_rows:
                try:
                    s_dt = datetime.fromisoformat(r["start_iso"])
                    if s_dt.tzinfo is None:
                        s_dt = s_dt.replace(tzinfo=tz)
                    e_dt = datetime.fromisoformat(r["end_iso"])
                    if e_dt.tzinfo is None:
                        e_dt = e_dt.replace(tzinfo=tz)
                    existing_events.append((s_dt, e_dt))
                except Exception:
                    pass

            now_str = datetime.now(timezone.utc).isoformat()

            for task in pending_tasks:
                # Idempotency check: if task already has a linked active event for today, skip it
                if task.get("linked_event_id") and task.get("scheduled_start_iso"):
                    s_iso = task["scheduled_start_iso"]
                    if s_iso.startswith(day_start.strftime("%Y-%m-%d")):
                        ev_check = conn.execute(
                            "SELECT id FROM events WHERE id = ? AND event_status != 'CANCELLED';",
                            (task["linked_event_id"],)
                        ).fetchone()
                        if ev_check:
                            already_scheduled_list.append({
                                "task_id": task["id"],
                                "title": task["title"],
                                "reason": "Already scheduled for today",
                            })
                            continue

                est_min = max(15, task["est_minutes"])
                duration = timedelta(minutes=est_min)
                buf = timedelta(minutes=buffer_minutes)

                scheduled_start = None
                scheduled_end = None

                while cursor + duration <= day_end:
                    cand_start = cursor
                    cand_end = cand_start + duration

                    # Interval-overlap check: cand_start < ev_end and cand_end > ev_start
                    has_collision = False
                    for ev_start, ev_end in existing_events:
                        if cand_start < ev_end and cand_end > ev_start:
                            has_collision = True
                            cursor = ev_end + buf
                            break

                    if not has_collision:
                        scheduled_start = cand_start
                        scheduled_end = cand_end
                        existing_events.append((scheduled_start, scheduled_end))
                        cursor = scheduled_end + buf
                        break

                if scheduled_start and scheduled_end:
                    task_title = f"[Focus] {task['title']}"
                    start_str = scheduled_start.isoformat()
                    end_str = scheduled_end.isoformat()

                    with conn:
                        ev_cur = conn.execute(
                            """
                            INSERT INTO events (title, start_iso, end_iso, location, notes, timezone, created_at, updated_at, event_status)
                            VALUES (?, ?, ?, 'Workstation', 'Auto-scheduled focus block', ?, ?, ?, 'SCHEDULED');
                            """,
                            (task_title, start_str, end_str, self._default_tz, now_str, now_str),
                        )
                        event_id = ev_cur.lastrowid

                        conn.execute(
                            """
                            UPDATE tasks SET scheduled_start_iso = ?, scheduled_end_iso = ?, linked_event_id = ?
                            WHERE id = ?;
                            """,
                            (start_str, end_str, event_id, task["id"]),
                        )

                        conn.execute(
                            """
                            INSERT INTO task_timeblocks (task_id, event_id, block_start, block_end, created_at)
                            VALUES (?, ?, ?, ?, ?);
                            """,
                            (task["id"], event_id, start_str, end_str, now_str),
                        )

                    scheduled_list.append({
                        "task_id": task["id"],
                        "title": task["title"],
                        "priority": task["priority"],
                        "scheduled_start_iso": start_str,
                        "scheduled_end_iso": end_str,
                        "start_time": scheduled_start.strftime("%I:%M %p"),
                        "end_time": scheduled_end.strftime("%I:%M %p"),
                        "duration_minutes": est_min,
                    })
                else:
                    unscheduled_list.append({
                        "task_id": task["id"],
                        "title": task["title"],
                        "priority": task["priority"],
                        "reason": "No available free slot within working hours",
                    })

            if not scheduled_list and already_scheduled_list and not unscheduled_list:
                return {
                    "status": "SUCCESS",
                    "message": f"No unscheduled pending tasks. {len(already_scheduled_list)} tasks already scheduled.",
                    "scheduled_count": 0,
                    "scheduled_tasks": [],
                    "already_scheduled_count": len(already_scheduled_list),
                    "already_scheduled_tasks": already_scheduled_list,
                    "unscheduled_count": 0,
                    "unscheduled_tasks": [],
                    "safety_audit": audit,
                }

            if not scheduled_list and not already_scheduled_list and unscheduled_list:
                return {
                    "status": "NO_AVAILABLE_SLOT",
                    "message": "No available free calendar slots within working hours to schedule tasks.",
                    "scheduled_count": 0,
                    "unscheduled_tasks": unscheduled_list,
                    "safety_audit": audit,
                }

            logger.info("Auto-timeblocked %d tasks for today (%d already scheduled, %d unscheduled)",
                        len(scheduled_list), len(already_scheduled_list), len(unscheduled_list))
            return {
                "status": "SUCCESS",
                "scheduled_count": len(scheduled_list),
                "scheduled_tasks": scheduled_list,
                "already_scheduled_count": len(already_scheduled_list),
                "already_scheduled_tasks": already_scheduled_list,
                "unscheduled_count": len(unscheduled_list),
                "unscheduled_tasks": unscheduled_list,
                "safety_audit": audit,
            }
        finally:
            conn.close()

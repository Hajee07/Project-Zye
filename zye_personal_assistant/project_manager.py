"""
Project Management Support Engine for Zye Personal Assistant (Day 14 & Day 29).
Provides project tracking, blocker flagging, milestone records, delay risk calculation,
dynamic completion calculation from linked tasks, and status board aggregation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from zye_personal_assistant.database import get_db_connection, init_assistant_database
from zye_personal_assistant.safety_gateway import SafetyGateway

logger = logging.getLogger("zye.personal_assistant.projects")

VALID_STATUSES = {"ACTIVE", "AT_RISK", "BLOCKED", "COMPLETED", "ON_HOLD"}
VALID_RISKS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


class ProjectManager:
    def __init__(
        self,
        db_path: str | Path | None = None,
        safety_gateway: Optional[SafetyGateway] = None,
    ) -> None:
        self._db_path = db_path
        self._safety = safety_gateway or SafetyGateway(db_path=db_path)
        init_assistant_database(self._db_path)

    def create_or_update_project(
        self,
        name: str,
        objective: str = "",
        deadline_iso: str = "",
        blockers: str = "",
        status: str = "ACTIVE",
        risk_level: str = "LOW",
        completion_percent: Optional[float] = None,
    ) -> dict[str, Any]:
        """Create or update a project record in SQLite."""
        clean_name = name.strip()
        if not clean_name:
            return {"status": "ERROR", "message": "Project name cannot be empty."}

        clean_status = status.strip().upper()
        if clean_status not in VALID_STATUSES:
            clean_status = "ACTIVE"

        clean_risk = risk_level.strip().upper()
        if clean_risk not in VALID_RISKS:
            if clean_status == "BLOCKED":
                clean_risk = "CRITICAL"
            elif clean_status == "AT_RISK" or blockers.strip():
                clean_risk = "HIGH"
            else:
                clean_risk = "LOW"

        now_str = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT id, objective, deadline_iso, blockers, status, risk_level, completion_percent FROM projects WHERE name = ?;",
                (clean_name,),
            ).fetchone()
            with conn:
                if row:
                    # Update existing project preserving non-empty existing values if omitted
                    new_obj = objective if objective.strip() else row["objective"]
                    new_dead = deadline_iso if deadline_iso.strip() else row["deadline_iso"]
                    new_block = blockers if blockers.strip() else row["blockers"]
                    new_comp = (
                        round(float(completion_percent), 1)
                        if (completion_percent is not None and completion_percent >= 0)
                        else row["completion_percent"]
                    )
                    # If blockers are added and status was ACTIVE, mark AT_RISK
                    if new_block.strip() and clean_status == "ACTIVE":
                        clean_status = "AT_RISK"
                        if clean_risk == "LOW":
                            clean_risk = "HIGH"

                    conn.execute(
                        """
                        UPDATE projects
                        SET objective = ?, deadline_iso = ?, blockers = ?, status = ?, risk_level = ?, completion_percent = ?, updated_at = ?
                        WHERE name = ?;
                        """,
                        (new_obj, new_dead, new_block, clean_status, clean_risk, new_comp, now_str, clean_name),
                    )
                    action_done = "UPDATED"
                    proj_id = row["id"]
                    final_obj = new_obj
                    final_dead = new_dead
                    final_block = new_block
                    final_comp = new_comp
                else:
                    if blockers.strip() and clean_status == "ACTIVE":
                        clean_status = "AT_RISK"
                        if clean_risk == "LOW":
                            clean_risk = "HIGH"

                    init_comp = round(float(completion_percent), 1) if (completion_percent is not None and completion_percent >= 0) else 0.0
                    cursor = conn.execute(
                        """
                        INSERT INTO projects (name, objective, deadline_iso, blockers, status, risk_level, completion_percent, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (clean_name, objective.strip(), deadline_iso.strip(), blockers.strip(), clean_status, clean_risk, init_comp, now_str, now_str),
                    )
                    action_done = "CREATED"
                    proj_id = cursor.lastrowid
                    final_obj = objective.strip()
                    final_dead = deadline_iso.strip()
                    final_block = blockers.strip()
                    final_comp = init_comp

            logger.info("Project %s: '%s' (status: %s, risk: %s)", action_done, clean_name, clean_status, clean_risk)
            return {
                "status": "SUCCESS",
                "action": action_done,
                "project_id": proj_id,
                "name": clean_name,
                "objective": final_obj,
                "deadline_iso": final_dead,
                "project_status": clean_status,
                "blockers": final_block,
                "risk_level": clean_risk,
                "completion_percent": final_comp,
            }
        finally:
            conn.close()

    def flag_blocker(
        self,
        name: str,
        blocker_description: str,
        risk_level: str = "HIGH",
        mark_blocked: bool = False,
    ) -> dict[str, Any]:
        """Flag a project blocker and automatically transition project status to AT_RISK or BLOCKED."""
        clean_name = name.strip()
        clean_desc = blocker_description.strip()
        if not clean_name:
            return {"status": "ERROR", "message": "Project name cannot be empty."}
        if not clean_desc:
            return {"status": "ERROR", "message": "Blocker description cannot be empty."}

        now_str = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection(self._db_path)
        try:
            row = conn.execute("SELECT id, blockers, status FROM projects WHERE name = ?;", (clean_name,)).fetchone()
            if not row:
                return {
                    "status": "NOT_FOUND",
                    "error_code": "PROJECT_NOT_FOUND",
                    "message": f"Project '{clean_name}' does not exist.",
                }

            existing_blockers = row["blockers"] or ""
            if existing_blockers:
                updated_blockers = f"{existing_blockers}; {clean_desc}".strip("; ")
            else:
                updated_blockers = clean_desc

            target_status = "BLOCKED" if mark_blocked else "AT_RISK"
            target_risk = "CRITICAL" if mark_blocked else (risk_level.upper() if risk_level.upper() in VALID_RISKS else "HIGH")

            with conn:
                conn.execute(
                    """
                    UPDATE projects
                    SET blockers = ?, status = ?, risk_level = ?, updated_at = ?
                    WHERE name = ?;
                    """,
                    (updated_blockers, target_status, target_risk, now_str, clean_name),
                )

            logger.warning("Flagged blocker on project '%s': %s (new status: %s)", clean_name, clean_desc, target_status)
            return {
                "status": "SUCCESS",
                "name": clean_name,
                "project_status": target_status,
                "risk_level": target_risk,
                "blockers": updated_blockers,
                "message": f"Blocker registered. Project '{clean_name}' marked {target_status}.",
            }
        finally:
            conn.close()

    def get_status_board(self) -> dict[str, Any]:
        """
        Aggregate full status board across all projects, including dynamic task completion,
        blockers, overdue task tracking, and delay risk assessments.
        """
        conn = get_db_connection(self._db_path)
        now_str = datetime.now(timezone.utc).isoformat()
        try:
            proj_rows = conn.execute(
                """
                SELECT id, name, objective, deadline_iso, status, blockers, completion_percent, risk_level
                FROM projects
                ORDER BY name ASC;
                """
            ).fetchall()

            board: list[dict[str, Any]] = []
            for p in proj_rows:
                p_name = p["name"]

                # Count linked tasks from tasks table
                t_row = conn.execute(
                    """
                    SELECT 
                        COUNT(*) as total_tasks,
                        SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as done_tasks,
                        SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending_tasks,
                        SUM(CASE WHEN status = 'PENDING' AND priority IN ('CRITICAL', 'HIGH') THEN 1 ELSE 0 END) as critical_tasks,
                        SUM(CASE WHEN status = 'PENDING' AND due_iso != '' AND due_iso < ? THEN 1 ELSE 0 END) as overdue_tasks
                    FROM tasks
                    WHERE LOWER(project_name) = LOWER(?);
                    """,
                    (now_str, p_name),
                ).fetchone()

                total_t = (t_row["total_tasks"] or 0) if t_row else 0
                done_t = (t_row["done_tasks"] or 0) if t_row else 0
                pending_t = (t_row["pending_tasks"] or 0) if t_row else 0
                crit_t = (t_row["critical_tasks"] or 0) if t_row else 0
                overdue_t = (t_row["overdue_tasks"] or 0) if t_row else 0

                # Calculate dynamic completion percentage strictly from linked tasks if tasks exist
                if total_t > 0:
                    comp_pct = round((done_t / total_t) * 100.0, 1)
                else:
                    comp_pct = float(p["completion_percent"] or 0.0)

                # Compute delay risk
                delay_risk = "LOW"
                if p["status"] == "BLOCKED" or overdue_t > 1:
                    delay_risk = "CRITICAL"
                elif p["status"] == "AT_RISK" or bool(p["blockers"]) or overdue_t > 0:
                    delay_risk = "HIGH"
                elif crit_t > 0:
                    delay_risk = "MEDIUM"

                # Keep project table in sync with computed values
                with conn:
                    conn.execute(
                        "UPDATE projects SET completion_percent = ?, risk_level = ? WHERE id = ?;",
                        (comp_pct, delay_risk, p["id"]),
                    )

                board.append({
                    "project_id": p["id"],
                    "name": p_name,
                    "objective": p["objective"],
                    "deadline_iso": p["deadline_iso"],
                    "status": p["status"],
                    "blockers": p["blockers"],
                    "completion_percent": comp_pct,
                    "delay_risk": delay_risk,
                    "total_tasks": total_t,
                    "completed_tasks": done_t,
                    "pending_tasks": pending_t,
                    "critical_tasks": crit_t,
                    "overdue_tasks": overdue_t,
                })

            active_cnt = sum(1 for b in board if b["status"] == "ACTIVE")
            at_risk_cnt = sum(1 for b in board if b["status"] == "AT_RISK")
            blocked_cnt = sum(1 for b in board if b["status"] == "BLOCKED")
            completed_cnt = sum(1 for b in board if b["status"] == "COMPLETED")

            return {
                "status": "SUCCESS",
                "total_projects": len(board),
                "active_projects": active_cnt,
                "at_risk_projects": at_risk_cnt,
                "blocked_projects": blocked_cnt,
                "completed_projects": completed_cnt,
                "projects": board,
                "summary": f"Managed {len(board)} projects ({active_cnt} active, {at_risk_cnt} at risk, {blocked_cnt} blocked, {completed_cnt} completed).",
            }
        finally:
            conn.close()

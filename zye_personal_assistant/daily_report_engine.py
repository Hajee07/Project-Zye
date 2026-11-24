"""
Daily Report Generation Engine for Zye Personal Assistant (Day 14 & Day 30).
Synthesizes verified database records into Morning Briefs and End-of-Day Reports,
with JSON, Markdown, and Tanglish/English voice summaries.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import zoneinfo

from zye_personal_assistant.database import get_db_connection, init_assistant_database

logger = logging.getLogger("zye.personal_assistant.reports")

VALID_REPORT_TYPES = {"morning_brief", "end_of_day"}


class DailyReportEngine:
    def __init__(
        self,
        db_path: str | Path | None = None,
        default_timezone: str = "Asia/Kolkata",
    ) -> None:
        self._db_path = db_path
        self._default_tz = default_timezone
        init_assistant_database(self._db_path)

    def _get_now_local(self) -> datetime:
        return datetime.now(zoneinfo.ZoneInfo(self._default_tz))

    def generate_report(
        self,
        report_type: str = "morning_brief",
        include_email_summary: bool = True,
    ) -> dict[str, Any]:
        """
        Generate Morning Brief or End-of-Day report based strictly on SQLite records.
        """
        clean_type = report_type.strip().lower()
        if clean_type not in VALID_REPORT_TYPES:
            clean_type = "morning_brief"

        now = self._get_now_local()
        now_iso = now.isoformat()
        today_str = now.strftime("%Y-%m-%d")
        today_start = f"{today_str}T00:00:00"
        today_end = f"{today_str}T23:59:59"

        conn = get_db_connection(self._db_path)
        try:
            # 1. Fetch Today's Events
            ev_rows = conn.execute(
                """
                SELECT id, title, start_iso, end_iso, location, event_status
                FROM events
                WHERE event_status != 'CANCELLED'
                  AND NOT (end_iso <= ? OR start_iso >= ?)
                ORDER BY start_iso ASC;
                """,
                (today_start, today_end),
            ).fetchall()
            events = [dict(r) for r in ev_rows]

            # Determine next upcoming meeting
            next_meeting = None
            elapsed_meetings: list[dict[str, Any]] = []
            upcoming_meetings: list[dict[str, Any]] = []
            for ev in events:
                e_end = ev.get("end_iso", "")
                e_start = ev.get("start_iso", "")
                if e_end and e_end < now_iso:
                    elapsed_meetings.append(ev)
                else:
                    upcoming_meetings.append(ev)
                    if next_meeting is None and e_start >= now_iso:
                        next_meeting = ev

            if next_meeting is None and upcoming_meetings:
                next_meeting = upcoming_meetings[0]
            elif next_meeting is None and events and report_type == "morning_brief":
                next_meeting = events[0]

            # 2. Fetch Tasks
            task_rows = conn.execute(
                """
                SELECT id, title, priority, due_iso, status, project_name, updated_at
                FROM tasks;
                """
            ).fetchall()
            all_tasks = [dict(r) for r in task_rows]

            pending_tasks = [t for t in all_tasks if t["status"] == "PENDING"]
            completed_tasks = [t for t in all_tasks if t["status"] == "COMPLETED"]
            critical_tasks = [t for t in pending_tasks if t["priority"].upper() in ("CRITICAL", "HIGH")]

            # Overdue tasks: pending and due date in the past
            overdue_tasks = [
                t for t in pending_tasks
                if t["due_iso"] and t["due_iso"] < today_str
            ]

            # Tasks due today
            due_today_tasks = [
                t for t in pending_tasks
                if t["due_iso"] and t["due_iso"].startswith(today_str)
            ]

            # 3. Fetch Active Projects & Blockers
            proj_rows = conn.execute(
                """
                SELECT id, name, status, blockers, deadline_iso, completion_percent, risk_level
                FROM projects
                WHERE status != 'COMPLETED';
                """
            ).fetchall()
            active_projects = [dict(r) for r in proj_rows]
            blocked_projects = [p for p in active_projects if p["blockers"].strip() or p["status"] in ("AT_RISK", "BLOCKED")]

            # 4. Optional Email Summary
            email_info: dict[str, Any] = {"status": "UNCONFIGURED", "unread_count": 0, "emails": []}
            if include_email_summary:
                try:
                    from zye_personal_assistant.email_engine import EmailEngine
                    ee = EmailEngine(db_path=self._db_path)
                    if ee.is_configured():
                        fetch_res = ee.fetch_unread_emails(limit=5)
                        if fetch_res.get("status") == "SUCCESS":
                            email_info = {
                                "status": "AVAILABLE",
                                "unread_count": fetch_res.get("unread_count", 0),
                                "emails": fetch_res.get("emails", [])[:3],
                            }
                except Exception as ex:
                    logger.debug("Email summary extraction bypassed: %s", ex)

            if clean_type == "morning_brief":
                return self._build_morning_brief(
                    now=now,
                    events=events,
                    next_meeting=next_meeting,
                    pending_tasks=pending_tasks,
                    critical_tasks=critical_tasks,
                    overdue_tasks=overdue_tasks,
                    due_today_tasks=due_today_tasks,
                    projects=active_projects,
                    blocked_projects=blocked_projects,
                    email_info=email_info,
                )
            else:
                return self._build_end_of_day_report(
                    now=now,
                    events=events,
                    elapsed_meetings=elapsed_meetings,
                    upcoming_meetings=upcoming_meetings,
                    completed_tasks=completed_tasks,
                    pending_tasks=pending_tasks,
                    overdue_tasks=overdue_tasks,
                    projects=active_projects,
                    blocked_projects=blocked_projects,
                    email_info=email_info,
                )

        finally:
            conn.close()

    def _build_morning_brief(
        self,
        now: datetime,
        events: list[dict[str, Any]],
        next_meeting: Optional[dict[str, Any]],
        pending_tasks: list[dict[str, Any]],
        critical_tasks: list[dict[str, Any]],
        overdue_tasks: list[dict[str, Any]],
        due_today_tasks: list[dict[str, Any]],
        projects: list[dict[str, Any]],
        blocked_projects: list[dict[str, Any]],
        email_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Construct Morning Brief payload."""
        date_str = now.strftime("%A, %d %B %Y")
        meeting_count = len(events)
        task_count = len(pending_tasks)
        crit_count = len(critical_tasks)
        overdue_count = len(overdue_tasks)

        md_lines = [
            f"# Zye Morning Briefing — {date_str}",
            "",
            f"**Scheduled Meetings:** {meeting_count} | **Pending Tasks:** {task_count} ({crit_count} high priority) | **Overdue Tasks:** {overdue_count} | **Active Projects:** {len(projects)}",
            "",
            "## Today's Meetings",
        ]
        if events:
            for ev in events:
                start_fmt = ev["start_iso"].split("T")[1][:5] if "T" in ev["start_iso"] else ev["start_iso"]
                md_lines.append(f"- **{start_fmt}**: {ev['title']} ({ev.get('location') or 'Workstation'})")
        else:
            md_lines.append("- No confirmed meetings scheduled for today.")

        if next_meeting:
            next_start = next_meeting["start_iso"].split("T")[1][:5] if "T" in next_meeting["start_iso"] else next_meeting["start_iso"]
            md_lines.extend(["", f"**Next Upcoming Meeting:** {next_meeting['title']} at {next_start}"])

        md_lines.extend(["", "## Top Priorities for Today"])
        priorities = critical_tasks or due_today_tasks or pending_tasks[:5]
        if priorities:
            for t in priorities[:5]:
                due_info = f" (Due: {t['due_iso']})" if t.get('due_iso') else ""
                md_lines.append(f"- [{t['priority']}] **{t['title']}** — {t['project_name']}{due_info}")
        else:
            md_lines.append("- Zero pending tasks. Great job!")

        if overdue_tasks:
            md_lines.extend(["", "## ⚠️ Overdue Tasks Requiring Attention"])
            for t in overdue_tasks[:4]:
                md_lines.append(f"- ❗ **{t['title']}** (was due {t['due_iso']})")

        if blocked_projects:
            md_lines.extend(["", "## ⚠️ Active Project Blockers & Risks"])
            for p in blocked_projects:
                blocker_text = p['blockers'] or f"Marked {p['status']}"
                md_lines.append(f"- **{p['name']}**: {blocker_text}")

        if email_info.get("status") == "AVAILABLE" and email_info.get("unread_count", 0) > 0:
            md_lines.extend(["", f"## Important Emails ({email_info['unread_count']} unread)"])
            for e in email_info.get("emails", []):
                md_lines.append(f"- **{e.get('sender', 'Unknown')}**: {e.get('subject', 'No Subject')} [{e.get('priority', 'MEDIUM')}]")
        elif email_info.get("status") == "UNCONFIGURED":
            md_lines.extend(["", "_Note: Email credentials unconfigured._"])

        markdown_text = "\n".join(md_lines)

        # Tanglish voice briefing
        voice_tanglish = (
            f"Good morning! Innaikku ungalukku {meeting_count} meetings, "
            f"{task_count} pending tasks, and {crit_count} high priority items irukku."
        )
        if next_meeting:
            n_start = next_meeting["start_iso"].split("T")[1][:5] if "T" in next_meeting["start_iso"] else ""
            voice_tanglish += f" Ungaloda next meeting '{next_meeting['title']}' {n_start}-ku irukku."
        if overdue_count > 0:
            voice_tanglish += f" Attention: {overdue_count} overdue tasks irukku."
        if blocked_projects:
            voice_tanglish += f" {len(blocked_projects)} project-la blockers identify aagirukku."

        voice_en = (
            f"Good morning. You have {meeting_count} meetings and {task_count} pending tasks today. "
        )
        if next_meeting:
            voice_en += f"Next meeting is {next_meeting['title']}. "

        return {
            "status": "SUCCESS",
            "report_type": "morning_brief",
            "date": date_str,
            "meeting_count": meeting_count,
            "next_meeting": next_meeting,
            "pending_task_count": task_count,
            "critical_task_count": crit_count,
            "overdue_task_count": overdue_count,
            "active_project_count": len(projects),
            "blocked_project_count": len(blocked_projects),
            "events_today": events,
            "top_tasks": priorities,
            "overdue_tasks": overdue_tasks,
            "markdown": markdown_text,
            "voice_tanglish": voice_tanglish,
            "voice_en": voice_en.strip(),
        }

    def _build_end_of_day_report(
        self,
        now: datetime,
        events: list[dict[str, Any]],
        elapsed_meetings: list[dict[str, Any]],
        upcoming_meetings: list[dict[str, Any]],
        completed_tasks: list[dict[str, Any]],
        pending_tasks: list[dict[str, Any]],
        overdue_tasks: list[dict[str, Any]],
        projects: list[dict[str, Any]],
        blocked_projects: list[dict[str, Any]],
        email_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Construct End-of-Day report payload."""
        date_str = now.strftime("%A, %d %B %Y")
        done_count = len(completed_tasks)
        pending_count = len(pending_tasks)
        overdue_count = len(overdue_tasks)

        md_lines = [
            f"# Zye End-of-Day Report — {date_str}",
            "",
            f"**Completed Tasks:** {done_count} | **Remaining Pending:** {pending_count} | **Meetings Elapsed:** {len(elapsed_meetings)} / {len(events)}",
            "",
            "## Completed Tasks",
        ]
        if completed_tasks:
            for t in completed_tasks[:10]:
                md_lines.append(f"- ✅ **{t['title']}** ({t['project_name']})")
        else:
            md_lines.append("- No tasks were marked completed today.")

        md_lines.extend(["", "## Carried Over to Tomorrow"])
        if pending_tasks:
            for t in pending_tasks[:5]:
                md_lines.append(f"- ⏳ [{t['priority']}] **{t['title']}**")
        else:
            md_lines.append("- Zero backlog! All tasks completed.")

        if overdue_tasks:
            md_lines.extend(["", "## ⚠️ Outstanding Overdue Items"])
            for t in overdue_tasks[:4]:
                md_lines.append(f"- ❗ **{t['title']}** (Due: {t['due_iso']})")

        if blocked_projects:
            md_lines.extend(["", "## ⚠️ Active Project Blockers"])
            for p in blocked_projects:
                blocker_text = p['blockers'] or f"Marked {p['status']}"
                md_lines.append(f"- **{p['name']}**: {blocker_text}")

        markdown_text = "\n".join(md_lines)

        voice_tanglish = (
            f"Innaikku end of day report: {done_count} tasks complete pannirukkeenga, "
            f"{pending_count} tasks tomorrow-ku carry over aagudhu."
        )
        if overdue_count > 0:
            voice_tanglish += f" {overdue_count} overdue items irukku."

        voice_en = (
            f"End of day summary: {done_count} tasks completed, {pending_count} pending."
        )

        return {
            "status": "SUCCESS",
            "report_type": "end_of_day",
            "date": date_str,
            "completed_task_count": done_count,
            "pending_task_count": pending_count,
            "overdue_task_count": overdue_count,
            "scheduled_meeting_count": len(events),
            "elapsed_meeting_count": len(elapsed_meetings),
            "upcoming_meeting_count": len(upcoming_meetings),
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "markdown": markdown_text,
            "voice_tanglish": voice_tanglish,
            "voice_en": voice_en,
        }

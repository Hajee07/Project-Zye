"""
Zye Personal Assistant & Daily Management Intelligence MCP Server (Day 14).
Unified MCP server exposing 10 core capabilities for calendar, reminders, email,
documents, tasks, travel, research, reports, analytics, and project tracking.
All sensitive operations are audited via Day 13 Negative Pre-Mortem Brain.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional

# Initialize FastMCP Server (compatible with mcp 1.x, 2.x, or fallback shim)
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
    _MCP_AVAILABLE = True
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[no-redef]
        _MCP_AVAILABLE = True
    except ImportError:
        _MCP_AVAILABLE = False

        class FastMCP:  # type: ignore[no-redef]
            def __init__(self, name: str, **kwargs: Any) -> None:
                self.name = name
                self._tools: dict[str, Any] = {}

            def tool(self, *args: Any, **kwargs: Any) -> Any:
                def decorator(func: Any) -> Any:
                    self._tools[func.__name__] = func
                    return func
                if args and callable(args[0]):
                    return decorator(args[0])
                return decorator

            def run(self, transport: str = "stdio") -> None:
                pass

            async def list_tools(self) -> list[Any]:
                class _Stub:
                    def __init__(self, n: str):
                        self.name = n
                return [_Stub(n) for n in self._tools]


from zye_personal_assistant import (
    BusinessAnalyticsEngine,
    CalendarEngine,
    DailyReportEngine,
    DocumentEngine,
    EmailEngine,
    ProjectManager,
    ReminderEngine,
    ResearchEngine,
    SafetyGateway,
    TaskScheduler,
    TravelEngine,
    init_assistant_database,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("zye.personal_assistant.mcp")

# Initialize SQLite tables
init_assistant_database()

# Create FastMCP server instance
mcp = FastMCP("zye-personal-assistant")

# Engines
_safety = SafetyGateway()
_calendar = CalendarEngine(safety_gateway=_safety)
_reminders = ReminderEngine()
_email = EmailEngine(safety_gateway=_safety)
_documents = DocumentEngine(safety_gateway=_safety)
_tasks = TaskScheduler(safety_gateway=_safety)
_travel = TravelEngine()
_research = ResearchEngine()
_reports = DailyReportEngine()
_analytics = BusinessAnalyticsEngine()
_projects = ProjectManager(safety_gateway=_safety)


# ---------------------------------------------------------------------------
# Tool 1: Calendar Management (Day 14 & Day 28)
# ---------------------------------------------------------------------------
@mcp.tool()
def manage_calendar(
    action: str,
    title: str = "",
    start_iso: str = "",
    end_iso: str = "",
    location: str = "",
    notes: str = "",
    event_id: int = 0,
    duration_minutes: int = 60,
    force_override: bool = False,
    operation_id: str = "",
) -> str:
    """
    Manage calendar meetings, check interval conflicts, reschedule, and discover free slots.
    Actions: 'add', 'list_upcoming', 'check_conflicts', 'update', 'reschedule', 'cancel', 'delete',
             'daily_schedule', 'find_free_slots', 'summary', 'next_meeting'.
    """
    clean_action = action.strip().lower()
    try:
        if clean_action == "add":
            res = _calendar.add_event(
                title=title,
                start_iso=start_iso,
                end_iso=end_iso,
                location=location,
                notes=notes,
                force_override=force_override,
                operation_id=operation_id,
            )
            return json.dumps(res, indent=2)
        elif clean_action == "check_conflicts":
            res = _calendar.check_conflicts(start_iso=start_iso, end_iso=end_iso, exclude_event_id=event_id or None)
            return json.dumps(res, indent=2)
        elif clean_action == "list_upcoming":
            res = _calendar.list_upcoming_events(limit=15)
            return json.dumps({"status": "SUCCESS", "events": res}, indent=2)
        elif clean_action == "update":
            res = _calendar.update_event(
                event_id=event_id,
                title=title or None,
                start_iso=start_iso or None,
                end_iso=end_iso or None,
                location=location or None,
                notes=notes or None,
                force_override=force_override,
            )
            return json.dumps(res, indent=2)
        elif clean_action == "reschedule":
            res = _calendar.reschedule_event(
                event_id=event_id,
                new_start_iso=start_iso,
                new_duration_minutes=duration_minutes if duration_minutes > 0 else None,
                force_override=force_override,
            )
            return json.dumps(res, indent=2)
        elif clean_action == "cancel":
            res = _calendar.cancel_event(event_id=event_id)
            return json.dumps(res, indent=2)
        elif clean_action == "delete":
            res = _calendar.delete_event(event_id=event_id)
            return json.dumps(res, indent=2)
        elif clean_action == "daily_schedule":
            res = _calendar.get_daily_schedule(target_date_iso=start_iso or None)
            return json.dumps({"status": "SUCCESS", "events": res}, indent=2)
        elif clean_action == "find_free_slots":
            res = _calendar.find_free_slots(target_date_iso=start_iso or "", duration_minutes=duration_minutes)
            return json.dumps({"status": "SUCCESS", "free_slots": res}, indent=2)
        elif clean_action == "summary":
            res = _calendar.get_calendar_summary()
            return json.dumps({"status": "SUCCESS", "summary": res}, indent=2)
        elif clean_action == "next_meeting":
            res = _calendar.get_calendar_summary().get("next_meeting")
            return json.dumps({"status": "SUCCESS", "next_meeting": res}, indent=2)
        else:
            return json.dumps({"status": "ERROR", "message": f"Unknown calendar action: {action}"}, indent=2)
    except Exception as exc:
        logger.error("manage_calendar failed: %s", exc)
        return json.dumps({"status": "ERROR", "message": str(exc)}, indent=2)


# ---------------------------------------------------------------------------
# Tool 2: Meeting Reminders (Day 14 & Day 28 Persistent Dispatch)
# ---------------------------------------------------------------------------
@mcp.tool()
def check_meeting_reminders(reference_time_iso: str = "") -> str:
    """
    Check for proactive 15-minute and 2-minute upcoming meeting alerts from persistent storage.
    Marks reminders as delivered and returns active alerts with English, Tanglish, and Tamil messages.
    """
    try:
        alerts = _reminders.check_meeting_reminders(reference_time_iso=reference_time_iso or None)
        return json.dumps({"status": "SUCCESS", "active_alerts_count": len(alerts), "alerts": alerts}, indent=2)
    except Exception as exc:
        logger.error("check_meeting_reminders failed: %s", exc)
        return json.dumps({"status": "ERROR", "message": str(exc)}, indent=2)


# ---------------------------------------------------------------------------
# Day 28 Granular Calendar Tools
# ---------------------------------------------------------------------------
@mcp.tool()
def get_today_calendar() -> str:
    """Get all scheduled meetings for today in chronological order."""
    try:
        events = _calendar.get_daily_schedule()
        return json.dumps({"status": "SUCCESS", "events_count": len(events), "events": events}, indent=2)
    except Exception as exc:
        return json.dumps({"status": "ERROR", "message": str(exc)}, indent=2)


@mcp.tool()
def get_tomorrow_calendar() -> str:
    """Get all scheduled meetings for tomorrow in chronological order."""
    try:
        from datetime import datetime, timedelta
        import zoneinfo
        now = datetime.now(zoneinfo.ZoneInfo("Asia/Kolkata"))
        tomorrow_iso = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        events = _calendar.get_daily_schedule(target_date_iso=tomorrow_iso)
        return json.dumps({"status": "SUCCESS", "target_date": tomorrow_iso, "events_count": len(events), "events": events}, indent=2)
    except Exception as exc:
        return json.dumps({"status": "ERROR", "message": str(exc)}, indent=2)


@mcp.tool()
def find_available_calendar_slots(
    target_date_iso: str = "",
    duration_minutes: int = 60,
    working_hours_start: str = "09:00",
    working_hours_end: str = "18:00",
    min_duration_minutes: Optional[int] = None,
) -> str:
    """
    Discover free time slots within working hours (default 09:00 - 18:00) on a given date.
    Excludes past times and existing meetings.
    """
    eff_duration = min_duration_minutes or duration_minutes
    try:
        slots = _calendar.find_free_slots(
            target_date_iso=target_date_iso,
            duration_minutes=eff_duration,
            working_hours_start=working_hours_start,
            working_hours_end=working_hours_end,
        )
        return json.dumps({"status": "SUCCESS", "free_slots_count": len(slots), "free_slots": slots}, indent=2)
    except Exception as exc:
        return json.dumps({"status": "ERROR", "message": str(exc)}, indent=2)


@mcp.tool()
def reschedule_calendar_event(
    event_id: int,
    new_start_iso: str,
    new_duration_minutes: int = 60,
    force_override: bool = False,
) -> str:
    """
    Reschedule an existing meeting to a new start time, updating 15m and 2m reminders automatically.
    """
    try:
        res = _calendar.reschedule_event(
            event_id=event_id,
            new_start_iso=new_start_iso,
            new_duration_minutes=new_duration_minutes,
            force_override=force_override,
        )
        return json.dumps(res, indent=2)
    except Exception as exc:
        return json.dumps({"status": "ERROR", "message": str(exc)}, indent=2)


@mcp.tool()
def cancel_calendar_event(event_id: int) -> str:
    """
    Soft-cancel an existing meeting and automatically cancel all pending reminders.
    """
    try:
        res = _calendar.cancel_event(event_id=event_id)
        return json.dumps(res, indent=2)
    except Exception as exc:
        return json.dumps({"status": "ERROR", "message": str(exc)}, indent=2)


@mcp.tool()
def get_calendar_health() -> str:
    """Audit SQLite database health, schema version, integrity, and active event counts."""
    try:
        health = _calendar.get_calendar_health()
        rem_status = _reminders.get_status()
        return json.dumps({
            "status": "SUCCESS",
            "schema_version": health.get("schema_version", 28),
            "calendar_health": health,
            "reminders_health": rem_status,
        }, indent=2)
    except Exception as exc:
        return json.dumps({"status": "ERROR", "message": str(exc)}, indent=2)


# ---------------------------------------------------------------------------
# Tool 3: Email Management
# ---------------------------------------------------------------------------
@mcp.tool()
def manage_emails(
    action: str,
    to_addr: str = "",
    subject: str = "",
    body: str = "",
    limit: int = 8,
    confirmed: bool = False,
    confirmation_id: str = "",
) -> str:
    """
    Manage email communications.
    Actions:
      - 'fetch_unread' / 'triage_unread': retrieves unread emails with priority scoring (CRITICAL, HIGH, MEDIUM, LOW)
      - 'draft' / 'create_draft': stores an email draft locally
      - 'send': audits with Negative Brain and sends email via SMTP SSL (requires confirmation)
    """
    clean_action = action.strip().lower()
    try:
        if clean_action in ("fetch_unread", "triage_unread", "list_unread"):
            res = _email.fetch_unread_emails(limit=limit)
            return json.dumps(res, indent=2)
        elif clean_action in ("draft", "create_draft"):
            res = _email.create_draft(to_addr=to_addr, subject=subject, body=body)
            return json.dumps(res, indent=2)
        elif clean_action in ("send", "send_email"):
            res = _email.send_email(
                to_addr=to_addr,
                subject=subject,
                body=body,
                confirmed=confirmed,
                confirmation_id=confirmation_id,
            )
            return json.dumps(res, indent=2)
        else:
            return json.dumps({"status": "ERROR", "message": f"Unknown email action: {action}"}, indent=2)
    except Exception as exc:
        logger.error("manage_emails failed: %s", exc)
        return json.dumps({"status": "ERROR", "message": str(exc)}, indent=2)


# ---------------------------------------------------------------------------
# Tool 4: Document Management
# ---------------------------------------------------------------------------
@mcp.tool()
def manage_documents(
    action: str,
    directory_path: str = "",
    query: str = "",
    dry_run: bool = True,
    confirmed: bool = False,
    rollback_manifest_path: str = "",
) -> str:
    """
    Manage, index, search, and organize local documents (PDF, Word, Excel, CSV, Text).
    Actions:
      - 'index_folder' / 'index': extracts metadata & snippets from supported files in directory
      - 'search': searches indexed documents by query
      - 'auto_organize' / 'organize': preview or move documents into categorized subfolders with collision avoidance
      - 'rollback': restores moved files using saved rollback manifest
    """
    clean_action = action.strip().lower()
    try:
        if clean_action in ("index_folder", "index"):
            res = _documents.index_folder(directory_path=directory_path)
            return json.dumps(res, indent=2)
        elif clean_action == "search":
            res = _documents.search_documents(query=query)
            return json.dumps({"status": "SUCCESS", "results_count": len(res), "matches": res}, indent=2)
        elif clean_action in ("auto_organize", "organize"):
            res = _documents.auto_organize(directory_path=directory_path, dry_run=dry_run, confirmed=confirmed)
            return json.dumps(res, indent=2)
        elif clean_action == "rollback":
            res = _documents.rollback_organization(manifest_path=rollback_manifest_path)
            return json.dumps(res, indent=2)
        else:
            return json.dumps({"status": "ERROR", "message": f"Unknown document action: {action}"}, indent=2)
    except Exception as exc:
        logger.error("manage_documents failed: %s", exc)
        return json.dumps({"status": "ERROR", "message": str(exc)}, indent=2)


# ---------------------------------------------------------------------------
# Tool 5: Task Scheduling & Auto-Timeblocking
# ---------------------------------------------------------------------------
@mcp.tool()
def schedule_and_timeblock_tasks(
    action: str,
    title: str = "",
    priority: str = "MEDIUM",
    due_iso: str = "",
    est_minutes: int = 45,
    project_name: str = "General",
    task_id: int = 0,
) -> str:
    """
    Manage task queues and automatically timeblock pending tasks into free calendar slots.
    Actions:
      - 'add': adds task with priority (CRITICAL, HIGH, MEDIUM, LOW)
      - 'list': lists tasks sorted by priority and deadline
      - 'complete': marks task complete and updates linked project progress
      - 'auto_timeblock_today': automatically creates non-conflicting calendar focus blocks
    """
    clean_action = action.strip().lower()
    try:
        if clean_action == "add":
            res = _tasks.add_task(
                title=title, priority=priority, due_iso=due_iso, est_minutes=est_minutes, project_name=project_name
            )
            return json.dumps(res, indent=2)
        elif clean_action == "list":
            res = _tasks.list_tasks()
            return json.dumps({"status": "SUCCESS", "total_tasks": len(res), "tasks": res}, indent=2)
        elif clean_action == "complete":
            res = _tasks.complete_task(task_id=task_id)
            return json.dumps(res, indent=2)
        elif clean_action == "auto_timeblock_today":
            res = _tasks.auto_timeblock_today()
            return json.dumps(res, indent=2)
        else:
            return json.dumps({"status": "ERROR", "message": f"Unknown task action: {action}"}, indent=2)
    except Exception as exc:
        logger.error("schedule_and_timeblock_tasks failed: %s", exc)
        return json.dumps({"status": "ERROR", "message": str(exc)}, indent=2)


# ---------------------------------------------------------------------------
# Tool 6: Travel Planning Itinerary
# ---------------------------------------------------------------------------
@mcp.tool()
def plan_travel_itinerary(
    destination: str,
    days: int,
    purpose: str = "Business & Exploration",
    budget_tier: str = "Moderate",
    start_date_iso: str = "",
    check_calendar_conflicts: bool = False,
) -> str:
    """
    Generate day-by-day travel itinerary with transit buffers, cost breakdown,
    packing checklists, travel risk assessment, and optional calendar conflict checks.
    """
    try:
        res = _travel.plan_itinerary(
            destination=destination,
            days=days,
            purpose=purpose,
            budget_tier=budget_tier,
            start_date_iso=start_date_iso,
            check_calendar_conflicts=check_calendar_conflicts,
        )
        return json.dumps(res, indent=2)
    except Exception as exc:
        logger.error("plan_travel_itinerary failed: %s", exc)
        return json.dumps({"status": "ERROR", "message": str(exc)}, indent=2)


# ---------------------------------------------------------------------------
# Tool 7: Information Research Engine
# ---------------------------------------------------------------------------
@mcp.tool()
def conduct_information_research(
    topic: str,
    depth: str = "executive_brief",
) -> str:
    """
    Conduct structured research on a topic with multi-angle synthesis,
    key findings, source references, quality ratings, and uncertainty analysis.
    """
    try:
        res = _research.conduct_research(topic=topic, depth=depth)
        return json.dumps(res, indent=2)
    except Exception as exc:
        logger.error("conduct_information_research failed: %s", exc)
        return json.dumps({"status": "ERROR", "message": str(exc)}, indent=2)


# ---------------------------------------------------------------------------
# Tool 8: Daily Reports (Morning Brief / End of Day)
# ---------------------------------------------------------------------------
@mcp.tool()
def generate_daily_report(
    report_type: str = "morning_brief",
    include_email_summary: bool = True,
) -> str:
    """
    Generate Morning Brief or End-of-Day report based strictly on verified SQLite records.
    Returns JSON, Markdown, and Tanglish/English voice summaries.
    """
    try:
        res = _reports.generate_report(report_type=report_type, include_email_summary=include_email_summary)
        return json.dumps(res, indent=2)
    except Exception as exc:
        logger.error("generate_daily_report failed: %s", exc)
        return json.dumps({"status": "ERROR", "message": str(exc)}, indent=2)


# ---------------------------------------------------------------------------
# Tool 9: Business Data Analytics
# ---------------------------------------------------------------------------
@mcp.tool()
def analyze_business_data(
    file_path: str,
    business_question: str = "",
    sheet_name: str = "",
) -> str:
    """
    Perform statistical profiling, KPI calculations, and anomaly detection on CSV or Excel files.
    Calculates revenue, expenses, profit margins, trends, and flags negative/duplicate anomalies.
    """
    try:
        res = _analytics.analyze_dataset(
            file_path=file_path,
            business_question=business_question,
            sheet_name=sheet_name or None,
        )
        return json.dumps(res, indent=2)
    except Exception as exc:
        logger.error("analyze_business_data failed: %s", exc)
        return json.dumps({"status": "ERROR", "message": str(exc)}, indent=2)


# ---------------------------------------------------------------------------
# Tool 10: Project Management Support
# ---------------------------------------------------------------------------
@mcp.tool()
def manage_project_support(
    action: str,
    name: str = "",
    objective: str = "",
    deadline_iso: str = "",
    blockers: str = "",
    status: str = "ACTIVE",
    risk_level: str = "LOW",
    mark_blocked: bool = False,
) -> str:
    """
    Manage project lifecycles, flag blockers, track completion rates,
    and generate status boards.
    Actions: 'create_or_update', 'flag_blocker', 'status_board'.
    """
    clean_action = action.strip().lower()
    try:
        if clean_action in ("create_or_update", "create", "update"):
            res = _projects.create_or_update_project(
                name=name,
                objective=objective,
                deadline_iso=deadline_iso,
                blockers=blockers,
                status=status,
                risk_level=risk_level,
            )
            return json.dumps(res, indent=2)
        elif clean_action == "flag_blocker":
            res = _projects.flag_blocker(
                name=name,
                blocker_description=blockers,
                risk_level=risk_level,
                mark_blocked=mark_blocked,
            )
            return json.dumps(res, indent=2)
        elif clean_action == "status_board":
            res = _projects.get_status_board()
            return json.dumps(res, indent=2)
        else:
            return json.dumps({"status": "ERROR", "message": f"Unknown project action: {action}"}, indent=2)
    except Exception as exc:
        logger.error("manage_project_support failed: %s", exc)
        return json.dumps({"status": "ERROR", "message": str(exc)}, indent=2)


# ---------------------------------------------------------------------------
# Server Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Zye Personal Assistant MCP Server starting...")
    mcp.run()

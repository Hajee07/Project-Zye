"""
Automatic Meeting Reminder Engine for Zye Personal Assistant (Day 14 & Day 28).
Provides persistent 15-minute and 2-minute proactive meeting alerts, restart recovery,
duplicate prevention, and English, Tanglish, and Tamil voice strings.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from zye_personal_assistant.database import init_assistant_database
from zye_personal_assistant.calendar.calendar_database import initialize_calendar_database
from zye_personal_assistant.reminders.reminder_scheduler import PersistentReminderScheduler

logger = logging.getLogger("zye.personal_assistant.reminders")


class ReminderEngine:
    """
    Persistent Meeting Reminder Engine.
    Exposes check_meeting_reminders() consumed by the background daemon in main.py.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        default_timezone: str = "Asia/Kolkata",
    ) -> None:
        self._db_path = db_path
        self._default_tz = default_timezone
        initialize_calendar_database(self._db_path)
        self._scheduler = PersistentReminderScheduler(
            db_path=self._db_path,
            default_timezone=self._default_tz,
        )

    def check_meeting_reminders(self, reference_time_iso: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Scan calendar events and persistent event_reminders table for due alerts.
        Returns active alerts with voice messages in English, Tanglish, and Tamil.
        """
        return self._scheduler.check_due_reminders(reference_time_iso=reference_time_iso)

    def get_status(self) -> Dict[str, Any]:
        """Return scheduler diagnostics."""
        return self._scheduler.get_scheduler_status()


async def assistant_reminder_daemon(
    engine: ReminderEngine,
    speak_callback: Any,
    check_interval: float = 45.0,
) -> None:
    """Background coroutine periodically checking meeting reminders and invoking speak_callback."""
    import asyncio
    while True:
        try:
            alerts = engine.check_meeting_reminders()
            for alert in alerts:
                spoken = alert.get("message_tanglish") or alert.get("message_en")
                if spoken and speak_callback:
                    res = speak_callback(spoken)
                    if asyncio.iscoroutine(res):
                        await res
            await asyncio.sleep(check_interval)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Error in assistant_reminder_daemon: %s", exc)
            await asyncio.sleep(5.0)


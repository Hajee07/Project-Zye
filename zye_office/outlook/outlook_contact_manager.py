"""
Contacts, Tasks, and Calendar Adapter for Microsoft Outlook — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.outlook.outlook_adapter import OutlookAdapter
from zye_office.outlook.outlook_constants import OutlookConstants

logger = logging.getLogger("zye.office.outlook.contacts_tasks")


class OutlookContactTaskManager:
    """Provides capability-aware access to Outlook Contacts, Tasks, and Calendar."""

    def __init__(self, adapter: Optional[OutlookAdapter] = None) -> None:
        self.adapter = adapter or OutlookAdapter()
        self.worker = self.adapter.worker

    def search_contacts(self, query: str) -> List[Dict[str, Any]]:
        """Search contacts by name or email."""
        def _sta_contacts() -> List[Dict[str, Any]]:
            f = self.adapter.get_default_folder_raw(OutlookConstants.olFolderContacts)
            if f is None:
                return []

            results = []
            for item in f.Items:
                try:
                    name = getattr(item, "FullName", "")
                    email = getattr(item, "Email1Address", "")
                    if query.lower() in name.lower() or query.lower() in email.lower():
                        results.append({
                            "full_name": name,
                            "email": email,
                            "company": getattr(item, "CompanyName", ""),
                        })
                except Exception:
                    pass
            return results

        return self.worker.run(_sta_contacts)

    def create_contact(self, full_name: str, email: str) -> Dict[str, Any]:
        """Create a new contact in Outlook Contacts folder."""
        def _sta_create_c() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            c = app.CreateItem(OutlookConstants.olContactItem)
            c.FullName = full_name
            c.Email1Address = email
            c.Save()
            return {
                "status": "SUCCESS",
                "full_name": full_name,
                "email": email,
            }

        return self.worker.run(_sta_create_c)

    def get_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List current Outlook tasks."""
        def _sta_tasks() -> List[Dict[str, Any]]:
            f = self.adapter.get_default_folder_raw(OutlookConstants.olFolderTasks)
            if f is None:
                return []

            tasks = []
            count = 0
            for item in f.Items:
                if count >= limit:
                    break
                try:
                    tasks.append({
                        "subject": getattr(item, "Subject", ""),
                        "due_date": str(getattr(item, "DueDate", "")),
                        "is_complete": bool(getattr(item, "Complete", False)),
                    })
                    count += 1
                except Exception:
                    pass
            return tasks

        return self.worker.run(_sta_tasks)

    def create_task(self, subject: str, due_date: Optional[str] = None) -> Dict[str, Any]:
        """Create a new task."""
        def _sta_create_t() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            t = app.CreateItem(OutlookConstants.olTaskItem)
            t.Subject = subject
            if due_date:
                try:
                    t.DueDate = due_date
                except Exception:
                    pass
            t.Save()
            return {
                "status": "SUCCESS",
                "subject": subject,
            }

        return self.worker.run(_sta_create_t)

    def get_calendar_items(self, limit: int = 5) -> List[Dict[str, Any]]:
        """List upcoming appointments or calendar items."""
        def _sta_cal() -> List[Dict[str, Any]]:
            f = self.adapter.get_default_folder_raw(OutlookConstants.olFolderCalendar)
            if f is None:
                return []

            items = f.Items
            items.Sort("[Start]", False)
            events = []
            count = 0
            for item in items:
                if count >= limit:
                    break
                try:
                    events.append({
                        "subject": getattr(item, "Subject", ""),
                        "start": str(getattr(item, "Start", "")),
                        "duration_minutes": getattr(item, "Duration", 0),
                        "location": getattr(item, "Location", ""),
                    })
                    count += 1
                except Exception:
                    pass
            return events

        return self.worker.run(_sta_cal)

    def create_calendar_item(self, subject: str, start_time: str, duration_minutes: int = 30) -> Dict[str, Any]:
        """Create a calendar appointment."""
        def _sta_create_appt() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            appt = app.CreateItem(OutlookConstants.olAppointmentItem)
            appt.Subject = subject
            appt.Start = start_time
            appt.Duration = duration_minutes
            appt.Save()
            return {
                "status": "SUCCESS",
                "subject": subject,
                "start": start_time,
                "duration_minutes": duration_minutes,
            }

        return self.worker.run(_sta_create_appt)

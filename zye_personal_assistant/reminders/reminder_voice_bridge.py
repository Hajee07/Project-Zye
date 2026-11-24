"""
Voice Phrasing Bridge for Calendar Meeting Reminders (Day 28).
Generates signature voice announcements in Tamil, English, and Tanglish for 15-minute and 2-minute alerts.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from .reminder_models import ReminderType

logger = logging.getLogger("zye.personal_assistant.reminders.voice_bridge")


def build_calendar_reminder_message(
    title: str,
    reminder_type: str,
    minutes_left: Optional[int] = None,
    location: str = "",
    language: Optional[str] = None,
) -> Dict[str, str] | str:
    """
    Format voice announcement strings for a due reminder.
    Handles exact 15-minute, exact 2-minute, and catch-up remaining times.
    If language is specified ('en', 'tanglish', 'ta'), returns the string directly.
    Otherwise returns a dict of all 3 language variants.
    """
    if minutes_left is None:
        minutes_left = 2 if reminder_type in (ReminderType.TWO_MIN.value, "2_MIN", "2") else 15

    loc_suffix_en = f" at {location}" if location and location != "online" else ""
    loc_suffix_ta = f" ({location})" if location and location != "online" else ""

    if reminder_type in (ReminderType.TWO_MIN.value, "2_MIN", "2"):
        msg_en = f"Final Reminder. '{title}' starts in 2 minutes{loc_suffix_en}."
        msg_tanglish = f"Final Reminder. '{title}' meeting innum 2 minutes-la start aaguthu{loc_suffix_ta}."
        msg_tamil = f"இறுதி நினைவூட்டல். '{title}' சந்திப்பு இன்னும் இரண்டு நிமிடங்களில் தொடங்கும்."
    elif reminder_type in (ReminderType.FIFTEEN_MIN.value, "15_MIN", "15") and minutes_left >= 13:
        msg_en = f"Meeting Reminder. Your '{title}' starts in 15 minutes{loc_suffix_en}."
        msg_tanglish = f"Meeting Reminder. Ungaloda '{title}' meeting innum 15 minutes-la start aaguthu{loc_suffix_ta}."
        msg_tamil = f"சந்திப்பு நினைவூட்டல். உங்களுடைய '{title}' சந்திப்பு இன்னும் 15 நிமிடங்களில் தொடங்கும்."
    else:
        # Catch-up reminder after restart or sleep
        mins = max(1, minutes_left)
        msg_en = f"Meeting Alert. '{title}' starts in {mins} minutes{loc_suffix_en}."
        msg_tanglish = f"Meeting Alert. '{title}' innum {mins} minutes-la start aaguthu{loc_suffix_ta}."
        msg_tamil = f"சந்திப்பு எச்சரிக்கை. '{title}' இன்னும் {mins} நிமிடங்களில் தொடங்கும்."

    res = {
        "message_en": msg_en,
        "message_tanglish": msg_tanglish,
        "message_tamil": msg_tamil,
    }

    if language:
        lang_lower = language.lower()
        if lang_lower in ("en", "english"):
            return msg_en
        elif lang_lower in ("tanglish", "ta_en"):
            return msg_tanglish
        elif lang_lower in ("ta", "tamil"):
            return msg_tamil

    return res

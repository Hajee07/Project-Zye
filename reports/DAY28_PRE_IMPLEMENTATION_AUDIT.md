# ZYE AI — DAY 28 PRE-IMPLEMENTATION ARCHITECTURAL AUDIT
**Date:** 2026-11-21  
**Module:** Day 28 — Advanced Personal Calendar & Meeting Reminder Engine  
**Milestone:** Days 28–30 (Personal Assistant Milestone)  
**Primary MCP Server:** `personal_assistant_mcp.py`  
**Database:** `data/zye_assistant_db.sqlite`  

---

## 1. Executive Summary

An exhaustive audit of the Zye AI Hybrid Assistant repository was performed to prepare for the Day 28 Smart Calendar, Conflict Detection, Free-Slot Recommendation, and Persistent 15-Minute / 2-Minute Reminder Engine.

The system currently possesses a robust Day 14 foundation in `zye_personal_assistant/` and `personal_assistant_mcp.py`. The goal of Day 28 is to elevate this foundation into an offline-first, enterprise-grade calendar engine with strict half-open interval conflict detection (`existing.start < requested.end and existing.end > requested.start`), atomic transaction locks (`BEGIN IMMEDIATE`), multi-state persistent reminder tracking (`event_reminders` table), restart recovery, timezone handling via Python's standard `zoneinfo`, and Gemini Master Brain voice integration across Tamil, English, and Tanglish.

---

## 2. Component Classification & Status

| Subsystem / Component | Path | Status | Notes |
|:---|:---|:---|:---|
| **SQLite DB Connection & Schema** | `zye_personal_assistant/database.py` | `IMPLEMENTED_AND_TESTED` | Has WAL mode, busy timeout, foreign keys, `events` table. Needs migration for `event_reminders` table and UTC timestamps. |
| **Existing Calendar Engine** | `zye_personal_assistant/calendar_engine.py` | `PARTIALLY_IMPLEMENTED` | Basic conflict check and add event exist. Needs half-open atomic transactions, reschedule, free-slot algorithms, and Pydantic validation. |
| **Existing Reminder Engine** | `zye_personal_assistant/reminder_engine.py` | `PARTIALLY_IMPLEMENTED` | Has 15m and 2m window checks on `events` table columns (`reminded_15m`, `reminded_2m`). Needs persistent `event_reminders` table, state machine, and restart recovery. |
| **Personal Assistant MCP Server** | `personal_assistant_mcp.py` | `IMPLEMENTED_AND_TESTED` | FastMCP server exposing `manage_calendar` and `check_meeting_reminders`. Needs expansion with Day 28 granular tools and rich action support. |
| **Safety Gateway / Negative Brain** | `zye_personal_assistant/safety_gateway.py` | `IMPLEMENTED_AND_TESTED` | Day 13 Negative Pre-Mortem Brain integration active. |
| **Application Lifecycle & Daemon** | `main.py` | `IMPLEMENTED_AND_TESTED` | Has `meeting_reminder_loop()` running every 45s. Needs seamless bridge to new persistent reminder states. |
| **Gemini Sovereign Master Brain** | `zye_brain/gemini_agent.py` | `IMPLEMENTED_AND_TESTED` | Protocols 1-18 active. Needs Protocol 19 for Day 28 calendar voice intents (Tamil/English/Tanglish). |
| **Diagnostics & Health Checks** | `doctor.py` | `IMPLEMENTED_AND_TESTED` | Stages 1-23 active. Needs Stage 24 for Day 28 calendar verification. |

---

## 3. Database Schema Migration Plan

1. **Keep Existing Data Safe:**
   - Database: `data/zye_assistant_db.sqlite`
   - Existing table `events` contains user events. Do not drop or recreate.
2. **Add Columns to `events` (Non-Destructive):**
   - `start_utc INTEGER`: Normalized UTC epoch milliseconds
   - `end_utc INTEGER`: Normalized UTC epoch milliseconds
   - `timezone_id TEXT DEFAULT 'Asia/Kolkata'`
   - `version INTEGER DEFAULT 1`
   - `source TEXT DEFAULT 'voice'`
3. **Add New `event_reminders` Table:**
   - Tracks 6 states: `PENDING`, `CLAIMED`, `DELIVERED`, `FAILED`, `SUPPRESSED`, `CANCELLED`
   - Unique constraint: `UNIQUE(event_id, event_version, reminder_type)`
   - Foreign key: `FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE`
   - Indices on `due_at_utc`, `status`, and `event_id`

---

## 4. Architectural Boundaries

- **Gemini Sovereign Law:** Gemini Master Brain remains the sole vocal persona and reasoning engine. Calendar operations are deterministic and execute locally in SQLite without requiring cloud egress.
- **Offline-First:** All scheduling, conflict checks, free-slot computations, and reminder tracking operate completely offline.
- **Existing Voice Engine:** Pygame playback, Edge-TTS (`en-IN-NeerjaNeural`), and SmartAudioEar PortAudio input remain 100% untouched.

---

## 5. Audit Verdict

**APPROVED TO PROCEED WITH DAY 28 IMPLEMENTATION.**
All existing modules are safely backward-compatible.

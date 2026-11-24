# Zye AI — Day 29 Personal Assistant & Daily Operations Manual

## Overview
**Day 29 of 60** upgrades Zye AI with a production-grade **Personal Assistant and Operations Manager** subsystem. It unifies Email Management, Document Intelligence, Task Scheduling & Auto-Timeblocking, and Project Tracking into an offline-first, safety-gated architecture powered by FastMCP and audited by the Day 13 Negative Pre-Mortem Brain.

---

## 1. System Architecture

```
                                  +-----------------------------+
                                  |   Google Gemini Master      |
                                  | (Gemini Live Voice / Tamil) |
                                  +--------------+--------------+
                                                 |
                                                 v
                                  +-----------------------------+
                                  |    FastMCP Orchestrator     |
                                  |  (personal_assistant_mcp)   |
                                  +--------------+--------------+
                                                 |
                   +-----------------------------+-----------------------------+
                   |                             |                             |
                   v                             v                             v
       +-----------------------+     +-----------------------+     +-----------------------+
       |     Email Engine      |     |    Document Engine    |     |    Task Scheduler     |
       |  - IMAP SSL (PEEK)    |     |  - Multi-Format Text  |     |  - Priority Queue     |
       |  - Priority Triage    |     |  - Incremental SHA256 |     |  - Auto-Timeblocking  |
       |  - Safe SMTP Sending  |     |  - Safe Auto-Organize |     |  - Conflict Avoidance |
       +-----------+-----------+     +-----------+-----------+     +-----------+-----------+
                   |                             |                             |
                   +-----------------------------+-----------------------------+
                                                 |
                                                 v
                                  +-----------------------------+
                                  |   Safety Gateway & Audit    |
                                  | (Negative Pre-Mortem Brain) |
                                  +--------------+--------------+
                                                 |
                                                 v
                                  +-----------------------------+
                                  |  Offline SQLite Database    |
                                  | (zye_assistant_db.sqlite)   |
                                  +-----------------------------+
```

---

## 2. Core Modules

### 2.1 Module A — Email Management (`EmailEngine`)
- **IMAP Read Safety:** Connects via `imaplib.IMAP4_SSL` using `BODY.PEEK[]` so unread messages are never prematurely marked as read.
- **Deterministic Priority Triage:** Scans message subjects and snippets against keyword matrices:
  - `CRITICAL`: Outage, emergency, production, incident, server down, breach.
  - `HIGH`: Meeting, interview, contract, urgent review, deadline.
  - `LOW`: Newsletter, unsubscribe, digest, update, promotional.
  - `MEDIUM`: Standard professional correspondence.
- **Safe Draft Creation:** Drafts are stored in the SQLite `email_drafts` table without network transmission.
- **Two-Stage SMTP Sending Confirmation:**
  1. Initial `send` without confirmation returns `status="APPROVAL_REQUIRED"` with a cryptographically unique `confirmation_id` and Day 13 Safety Audit details.
  2. Confirmed invocation (`confirmed=True` or valid `confirmation_id`) dispatches message via SSL port 465, records history in `email_action_history`, and logs to `logs/email_audit.log`.

### 2.2 Module B — Document Management Engine (`DocumentEngine`)
- **Multi-Format Extraction:** Extracts clean text snippets from:
  - PDF (`pypdf`)
  - Word documents (`python-docx`)
  - Excel workbooks & sheets (`openpyxl` / `pandas`)
  - CSV files (`csv.DictReader`)
  - Text, Markdown, Python, JSON files
- **Incremental Indexing:** Stores file size, modification timestamp, and SHA-256 fingerprint in `doc_index`. Subsequent runs skip unchanged files instantly.
- **Ranked Search:** Prioritizes exact filename matches, starts-with matches, category matches, and snippet matches.
- **Safe Auto-Organization:**
  - Default `dry_run=True` calculates planned destination paths without moving files.
  - Requires `dry_run=False` and `confirmed=True` to execute file relocation into `PDF_Documents`, `Word_Docs`, `Spreadsheets`, `Notes_and_Text`.
  - Automatically avoids filename collisions by appending `_1`, `_2`.
  - Saves rollback manifest enabling atomic restoration via `rollback_organization`.

### 2.3 Module C — Task Scheduling & Auto-Timeblocking (`TaskScheduler`)
- **Strict Priority Enforcement:** Validates priorities (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`); rejects invalid tiers with `TASK_INVALID_PRIORITY`.
- **Intelligent Focus Timeblocking (`auto_timeblock_today`):**
  - Working hours boundary: 09:00 to 18:00 (Asia/Kolkata).
  - Interval-overlap avoidance: Prevents collision with existing calendar events (`events` table).
  - Enforces mandatory 10-minute focus transition buffers.
  - Idempotency: Skips tasks that already possess active calendar focus blocks.
  - Saturation handling: Reports `NO_AVAILABLE_SLOT` when calendar is fully booked.

### 2.4 Module D — Project Management Support (`ProjectManager`)
- **Lifecycle Tracking:** Supports `ACTIVE`, `AT_RISK`, `BLOCKED`, `COMPLETED`, `ON_HOLD`.
- **Blocker Escalation:** `flag_blocker` registers blocker descriptions, automatically transitioning status to `AT_RISK` or `BLOCKED` with `HIGH`/`CRITICAL` risk rating.
- **Dynamic Progress Calculation:** Computes completion percentage strictly from linked tasks in the `tasks` table (`(completed / total) * 100`).
- **Status Board Aggregation:** Displays active, at-risk, blocked, and completed projects with overdue task detection.

---

## 3. FastMCP Tool Interface

| MCP Tool Name | Action | Key Parameters | Output Status |
| :--- | :--- | :--- | :--- |
| `manage_emails` | `fetch_unread` | `limit=8` | `SUCCESS`, `CONFIG_REQUIRED` |
| `manage_emails` | `draft` | `to_addr`, `subject`, `body` | `SUCCESS` (`DRAFT_CREATED`) |
| `manage_emails` | `send` | `to_addr`, `subject`, `body`, `confirmed`, `confirmation_id` | `APPROVAL_REQUIRED`, `SMTP_ACCEPTED`, `SEND_FAILED` |
| `manage_documents` | `index_folder` | `directory_path` | `SUCCESS` |
| `manage_documents` | `search` | `query` | `SUCCESS` |
| `manage_documents` | `auto_organize` | `directory_path`, `dry_run`, `confirmed` | `DRY_RUN_COMPLETED`, `ORGANIZATION_COMPLETED` |
| `manage_documents` | `rollback` | `rollback_manifest_path` | `ROLLBACK_COMPLETED` |
| `schedule_and_timeblock_tasks` | `add` | `title`, `priority`, `due_iso`, `est_minutes`, `project_name` | `SUCCESS` (`TASK_ADDED`) |
| `schedule_and_timeblock_tasks` | `list` | (none) | `SUCCESS` |
| `schedule_and_timeblock_tasks` | `complete` | `task_id` | `SUCCESS`, `TASK_ALREADY_COMPLETED` |
| `schedule_and_timeblock_tasks` | `auto_timeblock_today` | (none) | `SUCCESS`, `NO_AVAILABLE_SLOT` |
| `manage_project_support` | `create_or_update` | `name`, `objective`, `deadline_iso`, `status` | `SUCCESS` |
| `manage_project_support` | `flag_blocker` | `name`, `blockers`, `mark_blocked` | `SUCCESS`, `NOT_FOUND` |
| `manage_project_support` | `status_board` | (none) | `SUCCESS` |

---

## 4. Environment Configuration

Add the following keys to your `.env` file for live email connectivity:

```ini
# IMAP Configuration (Reading)
ZYE_EMAIL_ADDRESS="your_email@gmail.com"
ZYE_EMAIL_APP_PASSWORD="your_google_app_password"
ZYE_IMAP_HOST="imap.gmail.com"
ZYE_IMAP_PORT="993"
ZYE_IMAP_TIMEOUT="6.0"

# SMTP Configuration (Sending)
ZYE_SMTP_HOST="smtp.gmail.com"
ZYE_SMTP_PORT="465"
ZYE_SMTP_TIMEOUT="15.0"
```

---

## 5. Voice Interaction Examples

### Email Management
- **English:** "Zye, check my unread emails and tell me if there are any urgent server alerts."
- **Tanglish:** "Zye, unread emails-ah check panni edhavadhu critical issue irukkaanu sollu."
- **Tamil:** "ஜை, படிக்காத மின்னஞ்சல்களைப் பார்த்து ஏதேனும் அவசரப் பிரச்சினை உள்ளதா என்று சொல்."

### Task Scheduling & Timeblocking
- **English:** "Zye, schedule 45 minutes today to write the API test suite."
- **Tanglish:** "Zye, innikku calendar-la API test suite ezhutha oru 45 minutes focus slot poodu."
- **Tamil:** "ஜை, இன்று ஏபிஐ சோதனைத் தொடர் எழுத 45 நிமிட நேரத்தை ஒதுக்கு."

### Document Organization
- **English:** "Zye, preview organizing the files in my Downloads folder."
- **Tanglish:** "Zye, Downloads folder-la irukura documents-ah organize panna dry run kaatu."
- **Tamil:** "ஜை, பதிவிறக்கக் கோப்புறையில் உள்ள ஆவணங்களை ஒழுங்கமைக்கும் மாதிரியைக் காட்டு."

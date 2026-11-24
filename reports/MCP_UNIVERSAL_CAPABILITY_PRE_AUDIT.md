# ZYE AI — Universal MCP Capability Pre-Audit Report

**Audit Date:** 2026-11-21  
**Auditor:** Principal MCP Architect & Windows Systems Verification Specialist  
**Host Environment:** Windows Desktop (Windows 11 x64)  
**Execution Python Virtualenv:** `d:\Zye\.venv\Scripts\python.exe`  
**Master Brain:** Google Gemini 3.5 / Gemini Live Bidirectional WebSocket  
**Orchestration:** `ZyeMasterAgent` (main.py) with FastMCP Tool Dispatcher  

---

## 1. Executive Summary

This comprehensive pre-audit inventories all registered Model Context Protocol (MCP) servers and tools across the entire ZYE AI ecosystem. A total of **363 tools** across **8 official MCP servers** were audited, categorized, validated for schema integrity, and mapped to execution dispatch pathways.

Prior to this audit, a critical tool dispatch defect was uncovered in `main.py` (`_dispatch_tool_call`), where FastMCP `Tool` wrapper objects caused unhandled `TypeError` exceptions that were silently swallowed and returned false success dictionaries. That defect has been resolved: FastMCP `.fn` unwrap, coroutine awareness, sync/async auto-detection, and JSON response parsing are now verified.

---

## 2. Server Inventory & Tool Breakdown

| MCP Server File | Server Identifier | Tool Count | Primary Responsibilities | Execution Security Class |
|---|---|---|---|---|
| `windows_control_mcp.py` | `windows_control` / `windows_apps` | 31 | Windows desktop UI automation, window management, app launching, UIA inspection, WhatsApp Desktop automation | SAFE / ELEVATED (Calling/Sending requires explicit confirmation) |
| `browser_accounts_mcp.py` | `browser_accounts` | 39 | Chromium / Google Chrome persistent profile automation, search, page interaction, text extraction, Gmail, Drive | SAFE / ELEVATED |
| `office_master_mcp.py` | `office_master` | 183 | Microsoft Office COM automation (Word, Excel, PowerPoint, Outlook) without raw code execution | SAFE / REVERSIBLE |
| `system_os_mcp.py` | `system_os` | 36 | OS audio volume, screen brightness, processes, screenshots, filesystem navigation | SAFE / SYSTEM_MANAGEMENT |
| `personal_assistant_mcp.py` | `personal_assistant` | 16 | Offline SQLite Smart Calendar, reminders, email draft management, travel, tasks | SAFE / TRANSACTIONAL |
| `autonomous_decision_mcp.py` | `autonomous_brain` | 6 | Negative Pre-Mortem Brain, decision matrix, mission mode control, emergency reflexes | SAFE / REASONING |
| `ai_plugins_mcp.py` | `ai_plugins` | 40 | Multi-AI provider routing, circuit breaker, council deliberation, consensus engine | SAFE / DELEGATION |
| `self_repair_mcp.py` | `self_repair` | 12 | Health logs inspection, source backup, dry-run code patching, safe rollback | ELEVATED / SAFEGUARDED |
| **TOTAL** | **8 Servers** | **363 Tools** | **Comprehensive Windows Desktop AI Assistant** | **100% Audited** |

---

## 3. Detailed Server Audits

### 3.1 Windows Control MCP (`windows_control_mcp.py`) — 31 Tools
- **App Launching & Discovery:**
  - `open_any_app(app_name, timeout)`: Launches Win32, Store (UWP), or desktop app with verification polling.
  - `list_installed_apps(force_refresh)`: Discovers all registered Start Menu, Win32, and Store apps via PowerShell `Get-StartApps`.
  - `search_installed_apps(query)`: Fuzzy and exact substring matching against installed application catalog.
  - `launch_and_inspect_app(app_name, max_controls)`: Launches an app and immediately inspects its UIA control tree.
- **Window Management:**
  - `list_open_windows()`, `find_window(keyword)`, `get_active_window()`: Enumerate HWNDs, titles, and processes.
  - `manage_window_state(keyword, action)`: Minimizes, maximizes, restores, focuses, closes, snaps (left, right, top, bottom), moves, resizes, or centers.
- **UI Automation (UIA) & Accessibility Tree:**
  - `inspect_app_ui(window_keyword, max_controls)`: Dumps control tree (buttons, edits, menus, lists, tables).
  - `get_ui_element_details(window_keyword, element_name)`: Returns bounding rectangle, state, patterns, AutomationId.
  - `get_control_patterns(window_keyword, element_name)`: Queries Invoke, Value, Toggle, SelectionItem patterns.
  - `execute_control_pattern(window_keyword, element_name, pattern_name, parameter)`: Safely invokes native control pattern.
  - `click_ui_element(window_keyword, element_name, click_type, double_click)`: Clicks UIA element by name.
  - `type_into_app(window_keyword, text, element_name, clear_first)`: Types text into focused window or targeted input control.
  - `press_hotkey(hotkey, window_keyword)`: Sends key combinations (e.g., Ctrl+C, Alt+F4) safely.
- **WhatsApp Desktop Automation:**
  - `search_whatsapp_contact(query)`: Searches contacts or chats in WhatsApp Desktop.
  - `open_whatsapp_chat(contact_name)`: Focuses or opens conversation with named contact.
  - `compose_whatsapp_message(contact_name, message)`: **DRAFTS** message into input field without sending.
  - `send_whatsapp_message(contact_name, message, confirmed)`: Sends message only when `confirmed=True`.
  - `start_whatsapp_voice_call(contact_name, confirmed)`: Initiates voice call only when `confirmed=True`.
  - `start_whatsapp_video_call(contact_name, confirmed)`: Initiates video call only when `confirmed=True`.
  - `end_whatsapp_call()`: Terminates active call immediately.
  - `get_whatsapp_call_status()`: Checks current call state (IDLE, DIALING, CONNECTED).
- **Workspace & Virtual Desktops:**
  - `list_displays()`, `get_primary_display()`, `list_workspaces()`, `switch_workspace(workspace_id)`, `move_window_to_workspace(window_keyword, workspace_id)`.

### 3.2 Browser Accounts MCP (`browser_accounts_mcp.py`) — 39 Tools
- **Chrome Session Lifecycle:**
  - `browser_launch_session(profile_name, headless)`: Connects to or launches Google Chrome with persistent profile.
  - `browser_close_session(profile_name)`: Closes session gracefully.
  - `browser_list_profiles()`: Discovers Chrome user profiles (Default, Profile 1, etc.).
- **Web Navigation & Search:**
  - `browser_navigate(url)`: Navigates to target URL with page load state verification.
  - `browser_search(query)`: Navigates to Google Search and retrieves top search result snippets.
  - `browser_click(selector)`, `browser_type(selector, text)`: Direct DOM interaction.
  - `browser_summarize_page()`: Extracts clean article/text content and readability summary.
  - `browser_gmail_search(query)`: Searches messages in authorized Gmail web session.
  - `browser_drive_search(query)`: Searches files in authorized Google Drive web session.

### 3.3 Microsoft Office COM MCP (`office_master_mcp.py`) — 183 Tools
- **Architecture:** Zero `exec()` or arbitrary code execution; all operations use typed dispatch wrappers over pywin32 / pythoncom COM interfaces with STA thread safety (`CoInitialize()`).
- **Word Automation:** `word_create_document`, `word_open_document`, `word_insert_text`, `word_format_selection`, `word_save_document`, `word_export_pdf`, `word_add_table`, `word_inspect_open_documents`, etc.
- **Excel Automation:** `excel_create_workbook`, `excel_open_workbook`, `excel_set_cell_value`, `excel_set_cell_formula`, `excel_read_range`, `excel_format_range`, `excel_add_chart`, `excel_save_workbook`, `excel_export_pdf`, `excel_inspect_open_workbooks`, etc.
- **PowerPoint Automation:** `powerpoint_create_presentation`, `powerpoint_open_presentation`, `powerpoint_add_slide`, `powerpoint_insert_textbox`, `powerpoint_insert_shape`, `powerpoint_save_presentation`, `powerpoint_export_pdf`, etc.
- **Outlook Automation:** `outlook_get_version`, `outlook_create_email_draft`, `outlook_list_unread_emails`, `outlook_inspect_open_items`, etc.

### 3.4 System OS MCP (`system_os_mcp.py`) — 36 Tools
- Audio control (`get_master_volume`, `set_master_volume`, `mute_audio`, `unmute_audio`).
- Display brightness (`get_display_brightness`, `set_display_brightness`).
- Process supervision (`list_running_processes`, `get_process_details`, `kill_process_by_pid`).
- Windows screenshots (`capture_screen`, `capture_active_window`).
- Filesystem safety (`safe_read_file`, `safe_list_directory`, `check_disk_usage`).

### 3.5 Personal Assistant MCP (`personal_assistant_mcp.py`) — 16 Tools
- Day 28 SQLite Smart Calendar: `manage_calendar`, `check_meeting_reminders`, `get_today_calendar`, `get_tomorrow_calendar`, `find_available_calendar_slots`, `reschedule_calendar_event`, `cancel_calendar_event`, `get_calendar_health`.
- Personal assistance modules: `manage_emails`, `manage_documents`, `manage_tasks`, `manage_travel`, `manage_projects`, `manage_reports`, `manage_analytics`, `manage_research`.

### 3.6 Autonomous Decision & Self-Repair MCPs
- Negative Pre-Mortem Brain (`run_negative_premortem_brain`).
- Decision Matrix (`compare_and_decide_solutions`).
- Emergency reflex (`execute_emergency_reflex`).
- Multi-AI council (`run_quick_council`, `run_deep_council`, `compare_ai_responses`).
- Self-repair inspection and safe code patch preview (`read_recent_error_logs`, `preview_code_patch`).

---

## 4. Safety & Authorization Boundaries

1. **WhatsApp Gating:**
   - `compose_whatsapp_message` only populates the chat draft box. It NEVER presses Enter or triggers send.
   - `send_whatsapp_message` requires explicit `confirmed=True`. If `False`, it returns `CONFIRMATION_REQUIRED` and does not transmit.
   - Voice and video calls similarly enforce `confirmed=True`.
2. **Microsoft Office Execution:**
   - Restricted strictly to registered COM methods; no dynamic script execution.
   - Open unsaved document safety: saves changes only on explicit command or creates timestamped backups.
3. **Application Launch Verification:**
   - Re-checks active HWNDs before spawning; focuses running instances if present rather than launching duplicate processes.
   - Verification polling checks for window emergence within configurable timeout.

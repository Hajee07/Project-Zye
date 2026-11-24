# ZYE AI — DAY 16 CERTIFICATION REPORT
## UNIVERSAL WINDOWS APPLICATION AUTOMATION & MASTER OS CONTROL

- **Version:** DAY 16 — PHASE 2 FOUNDATION v1.0
- **Project:** ZYE AI HYBRID ASSISTANT
- **Platform:** Windows 10 / Windows 11
- **Status:** CERTIFIED & VERIFIED (All 92 Day 16 tests passing, 0 failures, 0 errors)
- **Primary Modules:**
  - `windows_control_mcp.py` (FastMCP Server — Windows Application Control)
  - `system_os_mcp.py` (FastMCP Server — System & Hardware OS Control)
  - `zye_windows/` (Universal Windows Automation Package)

---

## 1. ARCHITECTURAL OVERVIEW

Day 16 introduces **Universal Windows Application Automation and Master OS Control** to the Zye AI hybrid assistant. Designed for hands-free voice operations ("Zye, WhatsApp open pannu", "Arun-kku naan 10 minutes-la call panren nu message anuppu", "Volume increase pannu", "Brightness 40% set pannu"), Day 16 integrates Windows UI Automation (pywinauto backend="uia"), PyAutoGUI, PyGetWindow, and Windows WMI with Day 15's Master MCP Orchestrator, Safety Execution Gateway, and Autonomous Negative Pre-Mortem Brain.

```
+-----------------------------------------------------------------------------------+
|                              VOICE / TEXT INPUT                                   |
|   "WhatsApp open pannu" / "Arun-kku call panren nu message anuppu" / "Volume up"  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        GEMINI MULTI-PROJECT GATEWAY v2.0                          |
|             (Task Decomposition, Tool Selection & Argument Extraction)            |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        DAY 15 SAFETY EXECUTION GATEWAY                            |
|    - Tool Risk Classification (READ_ONLY -> LOW -> MEDIUM -> HIGH -> CRITICAL)     |
|    - Mandatory Pre-Mortem Brain Audit for Protected Operations                    |
|    - Explicit Confirmation Interlocks (Shutdown, Restart, WhatsApp Send, Recycle) |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                       MASTER MCP STDIO ORCHESTRATOR                               |
|        +----------------------------------+----------------------------------+    |
|        |       windows_control_mcp        |          system_os_mcp           |    |
|        |   (ZyeWindowsControl FastMCP)    |       (ZyeSystemOS FastMCP)      |    |
|        +----------------------------------+----------------------------------+    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                              zye_windows/ PACKAGE                                 |
|  - app_discovery.py       - app_launcher.py         - window_manager.py          |
|  - uia_inspector.py       - uia_interaction.py      - whatsapp_controller.py     |
|  - input_controller.py    - clipboard_manager.py    - power_manager.py           |
|  - volume_manager.py      - brightness_manager.py   - media_controller.py        |
|  - file_search.py         - process_manager.py      - screenshot_manager.py      |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                          WINDOWS 10/11 OPERATING SYSTEM                           |
|       (pywinauto UIA / PyAutoGUI / WMI / Win32 API / PowrProf / User32)           |
+-----------------------------------------------------------------------------------+
```

---

## 2. SUBSYSTEM CAPABILITIES & DESIGN SPECIFICATIONS

### A. Universal Windows Application Discovery (`zye_windows/app_discovery.py`)
- **Discovery Engine:** Executes PowerShell `Get-StartApps` to retrieve registered Start Menu and Store applications (both Win32 executables and UWP/Store AppIDs).
- **Disk Caching:** Persists discovered applications to `data/windows_app_cache.json` using atomic temporary file write and replacement, with a 1-hour cache TTL (`CACHE_TTL_SECONDS = 3600.0`).
- **Resilient Fallback:** When PowerShell is unavailable or times out, seamlessly falls back to a curated inventory of well-known applications (WhatsApp, Chrome, Edge, Spotify, Notepad, Calculator, Explorer, VS Code, VLC).
- **Search Logic:** Provides 3-tier matching: exact match, prefix match (`startswith`), and substring match.

### B. Application Launcher Engine (`zye_windows/app_launcher.py`)
- **Dual Launch Paths:**
  1. *Store / UWP Applications:* Dispatched via Windows Explorer shell protocol: `explorer.exe shell:AppsFolder\<AppID>`.
  2. *Win32 Executables:* Dispatched via `subprocess.Popen` or direct path execution.
- **Already-Running Window Detection:** Checks `WindowsWindowManager` before launching; if an active window exists, brings it to focus instead of launching duplicate instances.
- **Responsive Window Emergence Polling:** Actively polls `find_windows` with a configurable timeout (default 15.0s) to verify that the application has rendered a responsive window before returning success.

### C. Window Management & Desktop Workspace Controls (`zye_windows/window_manager.py`)
- **Supported Actions:** `focus`, `minimize`, `maximize`, `restore`, `close`, `snap_left`, `snap_right`.
- **Desktop Snapping:** Implements window snapping using simulated native Windows hotkeys (`Win + Left` and `Win + Right`) with target window activation.
- **Ambiguity Protection:** If multiple open windows match a keyword (e.g. multiple browser tabs), identifies all candidate titles and returns `AMBIGUOUS_WINDOW` without taking destructive actions.

### D. Windows UI Automation Tree Inspector (`zye_windows/uia_inspector.py`)
- **pywinauto UIA Backend:** Initializes `pywinauto.Desktop(backend="uia")` to traverse the accessibility tree.
- **Bounding & Pagination:** Clamps inspected controls to a default maximum of 60 (`DEFAULT_MAX_CONTROLS = 60`) to avoid token window blowouts.
- **Privacy & Secret Redaction:** Automatically detects password fields (`elem_info.is_password == True`) and masks control names as `[PASSWORD FIELD]`.
- **Structured Metadata:** Extracts control names, automation IDs, control types (`Button`, `Edit`, `ListItem`, `TabItem`), bounding rectangles, and supported patterns.

### E. Named UI Element Interaction Engine (`zye_windows/uia_interaction.py`)
- **Pattern-First Invocation:** Traverses native UIA patterns in priority order:
  1. `InvokePattern.invoke()`
  2. `TogglePattern.toggle()`
  3. `SelectionItemPattern.select()`
- **Click Input Fallback:** If native patterns are unavailable or raise an exception, automatically falls back to `target_elem.click_input()`.
- **Disabled Control Protection:** Rejects clicks on disabled elements (`elem_info.enabled == False`) returning `ELEMENT_DISABLED`.

### F. Universal Input Controller & Clipboard Dictation (`zye_windows/input_controller.py`)
- **Unicode / Tamil Safety:** Uses clipboard paste (`Ctrl + V`) rather than raw simulated keystrokes, completely preventing character corruption for Tamil, Tanglish, and emojis.
- **Clipboard Preservation:** Backs up the prior clipboard contents, pastes the dictated text, and immediately restores the user's previous clipboard data.
- **Thread-Safe Serialization:** All keyboard and mouse automation is guarded by a global re-entrant lock (`INPUT_LOCK = threading.RLock()`).
- **Safe Hotkeys Whitelist:** Restricts simulated hotkeys to 66 authorized keys (`ALLOWED_KEYS`), rejecting unsafe combinations.

### G. Safe Clipboard Manager (`zye_windows/clipboard_manager.py`)
- **Privacy Guard:** Explicit user-invoked reading only. Content is never written to log files.
- **Size Clamping:** Bounded to 2,000 characters (`DEFAULT_MAX_CLIPBOARD_CHARS = 2000`).

### H. WhatsApp Desktop Voice & UI Automation Controller (`zye_windows/whatsapp_controller.py`)
- **9 Voice-Controlled Workflows:**
  1. `open_whatsapp`: Launch or focus WhatsApp Desktop.
  2. `search_whatsapp_contact`: Search recipient with exact/fuzzy match and ambiguity detection.
  3. `open_whatsapp_chat`: Open chat with a verified contact.
  4. `compose_whatsapp_message`: Draft message into active chat without dispatching.
  5. `send_whatsapp_message`: Dispatch message (**Gated by Day 15 Safety Gateway — requires `confirmed=True`**).
  6. `start_whatsapp_voice_call`: Initiate voice call with confirmed recipient.
  7. `start_whatsapp_video_call`: Initiate video call with confirmed recipient.
  8. `end_whatsapp_call`: Locate and click End Call button in WhatsApp window.
  9. `get_whatsapp_call_status`: Check whether an active call is ongoing.

### I. Master System Volume & Page Scrolling Engine (`zye_windows/volume_manager.py`)
- **Volume Controls:** `up`, `down`, `mute`, `unmute`, and `set_volume_percent(0..100)`.
- **Hands-Free Scrolling:** Directional scrolling (`up`, `down`) with clicks clamped between 1 and 25 units.

### J. Screen Brightness Control via WMI (`zye_windows/brightness_manager.py`)
- **WMI Methods:** Invokes `WmiMonitorBrightnessMethods.WmiSetBrightness` via PowerShell.
- **Range Clamping:** Strictly validates levels between 0 and 100%; rejects out-of-bounds input.
- **Hardware Fallback:** Gracefully detects desktop monitors or external displays lacking WMI brightness controls and returns `HARDWARE_NOT_SUPPORTED`.

### K. Windows Power Management & Battery Telemetry (`zye_windows/power_manager.py`)
- **Supported Operations:**
  - `lock`: Dispatched via `ctypes.windll.user32.LockWorkStation()`.
  - `sleep`: Dispatched via `ctypes.windll.PowrProf.SetSuspendState(0, 0, 0)`.
  - `shutdown` & `restart`: **CRITICAL RISK** — Requires explicit user confirmation (`confirmed=True`). Schedules shutdown with a 30-second grace window allowing cancellation.
  - `cancel_shutdown`: Executes `shutdown.exe /a` to abort scheduled power actions.
- **Battery Telemetry:** Queries `psutil.sensors_battery()` reporting percentage, charging status, and remaining time.

### L. Local User File Search Engine & Media Controls (`zye_windows/file_search.py`, `zye_windows/media_controller.py`)
- **File Search:** Searches user directories (`Desktop`, `Documents`, `Downloads`, `Videos`) with depth bounding (max depth 3), 5-second timeout, and path traversal rejection (`..`, `/`, `\`).
- **Safe Opener:** Opens single unambiguous matches via `os.startfile()`. Rejects ambiguous multiple matches.
- **Global Media Controls:** Dispatches `play_pause`, `next`, `previous`, and `stop` using virtual media keys.

---

## 3. DUAL MCP SERVERS SPECIFICATION

### Server 1: `windows_control_mcp.py` (`ZyeWindowsControl`)
Exposes 13 tools over standard JSON-RPC stdio protocol (with stderr-only logging):
1. `discover_applications(force_refresh=False)`
2. `search_applications(query)`
3. `open_any_app(app_name, timeout=15.0)`
4. `list_open_windows(include_empty=False)`
5. `manage_window(window_keyword, action)`
6. `inspect_app_ui(window_keyword, max_controls=60)`
7. `click_ui_element(window_keyword, element_name, control_type="")`
8. `type_into_app(window_keyword, text, press_enter=False)`
9. `dictate_text_anywhere(text, press_enter=False)`
10. `press_hotkey(keys)`
11. `get_clipboard_text(max_chars=2000)`
12. `search_whatsapp_contact(contact_name)`
13. `send_whatsapp_message(contact_name, message, confirmed=False)`

### Server 2: `system_os_mcp.py` (`ZyeSystemOS`)
Exposes 14 tools over standard JSON-RPC stdio protocol (with stderr-only logging):
1. `control_volume(action, steps=5)`
2. `set_volume_percent(level)`
3. `scroll_page(direction="down", amount=5)`
4. `set_brightness(level)`
5. `get_brightness()`
6. `power_action(action, confirmed=False)`
7. `cancel_shutdown()`
8. `get_battery_status()`
9. `media_control(command)`
10. `find_and_open_local_file(filename_query, open_file=False)`
11. `list_running_applications()`
12. `preview_recycle_bin()`
13. `empty_recycle_bin(confirmed=False)`
14. `capture_screenshot(label="")`

---

## 4. SAFETY GATEWAY & PRE-MORTEM BRAIN INTEGRATION

In accordance with Day 15 architecture, no protected file-modifying, hardware, or external communication operation executes without risk classification and mandatory confirmation gates.

| Tool Name | Risk Level | Confirmation Required? | Fallback / Interlock |
|---|---|---|---|
| `power_action` (shutdown/restart) | `CRITICAL_RISK` | **YES** (`confirmed=True`) | 30s cancellation window via `cancel_shutdown()` |
| `empty_recycle_bin` | `CRITICAL_RISK` | **YES** (`confirmed=True`) | Preview contents before empty |
| `send_whatsapp_message` | `HIGH_RISK` | **YES** (`confirmed=True`) | Composes draft in chat; awaits user approval |
| `start_whatsapp_voice_call` | `HIGH_RISK` | Recommended | Requires verified contact name |
| `start_whatsapp_video_call` | `HIGH_RISK` | Recommended | Requires verified contact name |
| `control_volume` | `MEDIUM_RISK` | NO | Clamped to max 20 steps |
| `set_brightness` | `MEDIUM_RISK` | NO | Validated to 0..100% |
| `snap_window` / `manage_window` | `MEDIUM_RISK` | NO | Ambiguity protection |
| `scroll_page` | `MEDIUM_RISK` | NO | Clamped to max 25 wheel clicks |
| `press_hotkey` | `MEDIUM_RISK` | NO | Whitelist of 66 authorized keys |
| `open_any_app` | `LOW_RISK` | NO | Already-running check + launch verification |
| `inspect_app_ui` | `READ_ONLY` | NO | Password field redaction + bounded to 60 controls |
| `get_battery_status` | `READ_ONLY` | NO | Read-only telemetry |
| `get_clipboard_text` | `READ_ONLY` | NO | Explicit user command only; no logging of content |

---

## 5. DIAGNOSTICS & DOCTOR INTEGRATION (`doctor.py`)

Stage 12 of `doctor.py` (`check_day16_windows_automation`) tests and validates all 12 Day 16 subsystems. In addition, 12 fast-path CLI flags are supported:
- `python doctor.py --day16-check`: Executes all Stage 12 checks.
- `python doctor.py --day16-full-test`: Runs 12 comprehensive end-to-end integration tests.
- Individual Subsystem Flags:
  - `--day16-app-discovery`: Start menu enumeration and JSON caching.
  - `--day16-app-launch`: Launch interface, Win32 & Store paths, missing app handling.
  - `--day16-uia-check`: pywinauto UIA tree inspection and password redaction.
  - `--day16-whatsapp-check`: 9 WhatsApp workflows and call status query.
  - `--day16-system-os-check`: Volume, brightness, power, and battery telemetry.
  - `--day16-power-check`: Confirmation interlocks on shutdown and restart.
  - `--day16-brightness-check`: Display brightness WMI calls and boundary validation.
  - `--day16-volume-check`: Audio volume steps, percentage, and scrolling.
  - `--day16-clipboard-check`: Safe reading, text bounding, and non-logging.
  - `--day16-file-search-check`: Path traversal rejection and user folder search.
  - `--day16-security-check`: Safety Gateway risk classification and no-bypass policy.

---

## 6. UNIT TEST SUITE VERIFICATION

All 14 test modules in `tests/test_day16_*.py` pass cleanly with **92 total tests, 0 failures, and 0 errors**:

| Test Module | Tests | Result | Subsystems Covered |
|---|---|---|---|
| `test_day16_app_discovery.py` | 6 | **PASS** | Start menu scan, cache read/write, search, fallback inventory |
| `test_day16_app_launcher.py` | 4 | **PASS** | App launch, Store AppID dispatch, already-running focus, error handling |
| `test_day16_uia_inspector.py` | 4 | **PASS** | Bounded inspection (60 ctrls), password redaction, window not found |
| `test_day16_uia_interaction.py` | 6 | **PASS** | Pattern invocation, click fallback, ambiguity, disabled controls |
| `test_day16_whatsapp.py` | 13 | **PASS** | 9 WhatsApp workflows, draft composing, confirmation gate, call states |
| `test_day16_window_manager.py` | 8 | **PASS** | Window list, focus, minimize, snap left/right, ambiguity |
| `test_day16_clipboard.py` | 7 | **PASS** | Safe bounded reading, dictation with clipboard restore, hotkey whitelist |
| `test_day16_power_manager.py` | 8 | **PASS** | Lock, sleep, shutdown/restart confirmation, cancel shutdown, battery |
| `test_day16_brightness.py` | 6 | **PASS** | Range validation (0..100), WMI call dispatch, hardware fallback |
| `test_day16_volume.py` | 9 | **PASS** | Volume up/down/mute, level setting, hands-free scrolling |
| `test_day16_media.py` | 5 | **PASS** | Play/pause, next, previous, stop media commands |
| `test_day16_file_search.py` | 6 | **PASS** | Directory search, depth bounding, traversal rejection, single match open |
| `test_day16_security.py` | 5 | **PASS** | Safety Gateway risk classification, non-idempotent operations list |
| `test_day16_regression.py` | 5 | **PASS** | Multi-day imports, MCP server registry in `main.py`, config blocks |
| **TOTAL** | **92** | **100% PASS** | **Complete Universal Windows Automation & OS Control Subsystem** |

---

## 7. SIGN-OFF & CERTIFICATION

The Day 16 Universal Windows Automation and Master OS Control subsystem has been implemented, integrated, and verified in accordance with all principal-level engineering specifications:
- **No file modified without regression protection.**
- **No sensitive operation executed without Safety Gateway risk classification.**
- **All 12 Day 16 doctor diagnostics passing.**
- **All 92 unit tests passing.**
- **Day 01–15 foundation completely preserved.**

**Zye AI Day 16 — Phase 2 Foundation: FULLY CERTIFIED.**

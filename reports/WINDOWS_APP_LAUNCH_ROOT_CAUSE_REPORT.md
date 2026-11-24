# ZYE AI — WINDOWS APPLICATION LAUNCH ROOT CAUSE ANALYSIS REPORT
## False Success Prevention, Window Visibility Verification & Store App Resolution

**Document ID:** WAL-RCA-2026-11-22  
**Component:** `windows_control_mcp.py`, `zye_windows/`, `system_os_mcp.py`  
**Status:** ROOT CAUSES IDENTIFIED & DOCUMENTED  

---

### 1. Executive Summary

When the user asked ZYE to open a Windows application (e.g. WhatsApp, Chrome, Calculator), ZYE occasionally reported that the application had successfully opened, even though no visible window appeared on the desktop.

Analysis revealed three primary architectural defects:
1. `system_os_mcp.py`'s `start_application_process` returned `status: "SUCCESS"` merely because `subprocess.Popen` returned a process ID, without checking for window creation.
2. In `zye_windows/app_launcher.py`, window verification polled `pygetwindow.getAllWindows()`, which fails to detect modern Windows 11 packaged Store applications (UWP) hosted in `ApplicationFrameHost.exe`.
3. Gemini's system prompt lacked negative grounding rules against false successes.

---

### 2. Deep Technical Breakdown of Root Causes

#### 2.1 Process Startup Equated with UI Success
- **Defect in `zye_windows/process_manager.py` (lines 548–555)**:
  ```python
  proc = subprocess.Popen(cmd, shell=False)
  time.sleep(0.3)
  return {
      "status": "SUCCESS",
      "pid": proc.pid,
      "application": clean_app,
      "message": f"Launched '{clean_app}' with PID {proc.pid}."
  }
  ```
  `subprocess.Popen` only indicates that the operating system allocated an execution thread and process slot. It provides **zero evidence** that:
  - The process initialized its graphical subsystem.
  - A top-level desktop window handle (HWND) was created.
  - The window is visible, mapped, and non-minimized.
  - The application is responsive to user input.

#### 2.2 UWP / Windows Store Application Window Blindspot
- **Defect in `zye_windows/window_manager.py` (lines 125–136)**:
  ```python
  matches = [w for w in gw.getAllWindows() if kw in (w.title or "").lower() and w.title.strip()]
  ```
  - `pygetwindow.getAllWindows()` uses Win32 `EnumWindows` and checks `GetWindowTextW`.
  - In Windows 10 and 11, packaged Store applications (such as WhatsApp Desktop, Calculator, Clock, Settings) are managed by Windows Modern Core Application Lifecycle.
  - Their top-level HWND is owned by `ApplicationFrameHost.exe`.
  - During launch and background initialization, their Win32 window text is frequently empty (`""`), or only populated in the UI Automation (UIA) accessibility tree.
  - As a result, `pygetwindow` returned an empty list `[]`, causing `app_launcher.py` to time out or return inconclusive status, which was misreported.

#### 2.3 Shell AppsFolder Launch Disconnect
- **Defect in `zye_windows/app_launcher.py` (lines 177–179)**:
  ```python
  cmd = ["explorer.exe", f"shell:AppsFolder\\{app_id}"]
  subprocess.Popen(cmd)
  ```
  - Launching via `explorer.exe shell:AppsFolder\...` dispatches the launch request to `explorer.exe`.
  - `explorer.exe` launches, signals the DCOM Application Activation Manager, and exits almost immediately.
  - The actual app (e.g. `WhatsApp.exe`) starts asynchronously 1.0–2.5 seconds later with a completely different PID.
  - The launcher had no mechanism to discover the child process spawned by Application Activation Manager or correlate it to the target app.

#### 2.4 Lack of Strict Negative System Instruction in Gemini
- In `main.py` and `zye_gemini_live.py`, Gemini's prompt lacked negative constraint instructions.
- When an MCP tool returned `status: "LAUNCH_PENDING_OR_BACKGROUND"` or `status: "SUCCESS"` (process only), Gemini assumed the application was ready and announced: *"WhatsApp successfully opened"*.

---

### 3. Required Engineering Fixes

1. **Structured Execution Schema ([application_execution_schema.py](file:///d:/Zye/zye_windows/application_execution_schema.py))**:
   - Return explicit statuses: `UI_READY`, `WINDOW_VISIBLE`, `ALREADY_OPEN`, `PROCESS_STARTED`, `WINDOW_TIMEOUT`, `APP_NOT_FOUND`, `AMBIGUOUS_APP_MATCH`, `LAUNCH_FAILED`.
   - Never use `SUCCESS` without `verified: true` and window details.
2. **Dual-Backend Window & UI Verification**:
   - Combine Win32 `EnumWindows` + `pywinauto.Desktop(backend="uia")` to reliably detect both Win32 and packaged UWP/Store windows.
   - Verify that the window is visible, has non-zero geometry, and belongs to the intended app.
3. **Application Resolver & Aliases**:
   - Enhance application name resolution to match aliases (e.g., "calc" -> "Calculator", "chrome" -> "Google Chrome", "whatsapp" -> "WhatsApp").
4. **Gemini Zero-False-Success Enforcement**:
   - Ground Gemini's responses strictly in the verification result.
   - If status is `PROCESS_STARTED` or `WINDOW_TIMEOUT`, Gemini must clearly state that the window has not yet been verified.

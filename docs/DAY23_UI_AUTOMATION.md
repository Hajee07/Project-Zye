# Zye AI — Day 23 Universal Desktop UI Automation & Ribbon Accelerators

## 1. Overview

While deep COM automation handles Word, Excel, and PowerPoint natively, desktop UI elements such as Office Ribbon tabs, contextual popup dialogs, and native application controls require controlled UI automation.

---

## 2. Foreground Window Guard (`zye_office/desktop_ui/foreground_window_guard.py`)

Runaway keystrokes sent to the wrong application window can cause severe data loss. The `ForegroundWindowGuard` prevents this by continuously checking:
1. Active foreground window handle (`HWND`) via `GetForegroundWindow()`.
2. Process image name via `GetWindowThreadProcessId()` and `psutil`.
3. Process validation: if a command targets Word (`WINWORD.EXE`), but the active window is Chrome (`CHROME.EXE`), execution is immediately aborted with `UIForegroundMismatchError`.

---

## 3. Bounded Keyboard Sequence Engine (`zye_office/desktop_ui/keyboard_sequence_engine.py`)

- **Length Bounding**: Enforces a strict upper bound (default: 20 keys per sequence) to prevent infinite loops or runaway automation.
- **Focus Verification Before Every Keystroke**: Checks that the HWND has not changed between individual keystrokes. If the user clicks another window mid-sequence, execution is aborted with `UIFocusLostError`.
- **Safe Key Names**: Whitelists trusted keys (`alt`, `ctrl`, `shift`, `enter`, `esc`, `tab`, function keys) and alphanumeric characters.

---

## 4. Desktop Ribbon Accelerator (`zye_office/desktop_ui/ribbon_accelerator.py`)

Accelerates navigation through Microsoft Office Ribbon tabs using standard Alt hotkeys:
- **Home**: `Alt + H`
- **Insert**: `Alt + N`
- **Design**: `Alt + G`
- **Transitions (PPT)**: `Alt + K`
- **Animations (PPT)**: `Alt + A`
- **Slide Show (PPT)**: `Alt + S`
- **Review**: `Alt + R`
- **View**: `Alt + W`

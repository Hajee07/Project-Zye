# ZYE AI — Windows UI Automation & Window Management Engine

## 1. System Overview

The Windows UI Automation (UIA) and Window Management Engine (`zye_windows/uia_inspector.py`, `uia_interaction.py`, `window_manager.py`) allows ZYE AI to inspect and manipulate any native Windows application control tree.

---

## 2. Key Components

1. **UIA Tree Inspection (`WindowsUIAInspector`)**:
   - Walks the Windows Accessibility and Automation element tree.
   - Discovers buttons, edit controls, combo boxes, list views, and tabs.
   - Extracts AutomationIds, control types, bounding rectangles, and supported patterns.
2. **UIA Pattern Invocation (`WindowsUIAInteraction`)**:
   - `InvokePattern`: Clicks buttons and triggers actions directly without mouse movement.
   - `ValuePattern` / `TextPattern`: Reads and writes text values in edit boxes.
   - `TogglePattern`: Toggles checkboxes and radio buttons.
   - `SelectionItemPattern`: Selects items in drop-downs and lists.
3. **Window Management (`WindowsWindowManager`)**:
   - Enumerate all top-level desktop windows via `list_open_windows()`.
   - Focus, minimize, maximize, restore, close.
   - Window snapping: snap left, snap right, snap top, snap bottom.
   - Geometry manipulation: move, resize, center window on screen.

"""
Windows UI Automation Accessibility Tree Inspector — Zye Day 16.
Inspects native controls using pywinauto backend="uia".
Extracts control names, automation IDs, bounding boxes, patterns, and interactive states
with pagination and sensitive control redaction.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Optional

try:
    from pywinauto import Desktop
    _PYWINAUTO_AVAILABLE = True
except ImportError:
    _PYWINAUTO_AVAILABLE = False

from zye_windows.windows_models import UIControl, UIInspectResult

logger = logging.getLogger("zye.windows.uia_inspector")

DEFAULT_MAX_CONTROLS = 60

INTERACTIVE_CONTROL_TYPES = {
    "Button", "Edit", "ListItem", "MenuItem", "TabItem",
    "Hyperlink", "CheckBox", "RadioButton", "ComboBox",
    "TreeItem", "DataItem", "Document", "Text", "ToolBar", "Window"
}


class WindowsUIAInspector:
    """
    Inspects active application windows using the Windows UI Automation (UIA) tree.
    Provides structured, bounded control metadata for voice-directed interaction.
    """

    def __init__(self, max_controls: int = DEFAULT_MAX_CONTROLS) -> None:
        self.max_controls = max_controls

    def inspect_app_ui(
        self,
        window_keyword: str,
        max_controls: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Inspect the UI of a window matching window_keyword.
        Returns a bounded list of interactive controls with their types and automation IDs.
        """
        if not _PYWINAUTO_AVAILABLE:
            return {
                "status": "ERROR",
                "message": "pywinauto is not available. UI Automation inspection requires pywinauto.",
                "window": window_keyword,
                "controls": [],
            }

        limit = max_controls or self.max_controls
        clean_keyword = str(window_keyword).strip()
        if not clean_keyword:
            return {
                "status": "ERROR",
                "message": "window_keyword cannot be empty.",
                "window": window_keyword,
                "controls": [],
            }

        try:
            desktop = Desktop(backend="uia")
            windows = desktop.windows()

            # Find matching top-level window
            target_window = None
            candidate_titles: list[str] = []

            for w in windows:
                try:
                    title = w.window_text() or ""
                    if not title.strip():
                        continue
                    candidate_titles.append(title)
                    if clean_keyword.lower() in title.lower():
                        target_window = w
                        break
                except Exception:
                    continue

            if target_window is None:
                return {
                    "status": "WINDOW_NOT_FOUND",
                    "message": f"No active window found matching '{clean_keyword}'.",
                    "window": clean_keyword,
                    "available_windows": candidate_titles[:10],
                    "controls": [],
                }

            window_title = target_window.window_text()
            process_id = getattr(target_window, "process_id", lambda: 0)()
            hwnd = getattr(target_window, "handle", 0)

            # Inspect controls
            discovered_controls: list[UIControl] = []
            seen_signatures: set[str] = set()

            try:
                descendants = target_window.descendants()
            except Exception as d_exc:
                logger.warning("Could not enumerate descendants of window '%s': %s", window_title, d_exc)
                descendants = []

            for elem in descendants:
                if len(discovered_controls) >= limit:
                    break

                try:
                    elem_info = elem.element_info
                    c_type = elem_info.control_type or ""
                    c_name = elem_info.name or ""
                    auto_id = getattr(elem_info, "automation_id", "") or ""

                    # Filter noise: only include interactive or named controls
                    if not c_name and not auto_id:
                        continue
                    if c_type and c_type not in INTERACTIVE_CONTROL_TYPES and not c_name:
                        continue

                    # Avoid duplicate representations
                    sig = f"{c_type}:{c_name}:{auto_id}"
                    if sig in seen_signatures:
                        continue
                    seen_signatures.add(sig)

                    # Bounding rect
                    rect_dict: dict[str, int] = {}
                    try:
                        rect = elem_info.rectangle
                        rect_dict = {
                            "left": rect.left,
                            "top": rect.top,
                            "right": rect.right,
                            "bottom": rect.bottom,
                            "width": rect.width(),
                            "height": rect.height(),
                        }
                    except Exception:
                        pass

                    # Detect password fields
                    is_pw = False
                    try:
                        is_pw = bool(getattr(elem_info, "is_password", False))
                    except Exception:
                        pass

                    # Available patterns
                    patterns: list[str] = []
                    try:
                        for pat_name in ["Invoke", "Value", "Toggle", "SelectionItem", "ExpandCollapse", "Scroll"]:
                            if hasattr(elem, pat_name):
                                patterns.append(pat_name)
                    except Exception:
                        pass

                    ctrl = UIControl(
                        name=c_name if not is_pw else "[PASSWORD FIELD]",
                        control_type=c_type,
                        automation_id=auto_id,
                        enabled=bool(getattr(elem_info, "enabled", True)),
                        visible=bool(getattr(elem_info, "visible", True)),
                        rectangle=rect_dict,
                        patterns=patterns,
                        is_password=is_pw,
                    )
                    discovered_controls.append(ctrl)

                except Exception as elem_exc:
                    continue

            result = UIInspectResult(
                application=clean_keyword,
                window=window_title,
                process_id=process_id,
                hwnd=hwnd,
                controls_count=len(discovered_controls),
                controls=discovered_controls,
                truncated=len(discovered_controls) >= limit,
            )
            return {
                "status": "SUCCESS",
                **result.model_dump(),
            }

        except Exception as exc:
            logger.error("Error inspecting UI for window '%s': %s", clean_keyword, exc)
            return {
                "status": "ERROR",
                "message": f"UIA inspection failed: {exc}",
                "window": clean_keyword,
                "controls": [],
            }

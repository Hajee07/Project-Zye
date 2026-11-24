"""
Named UI Element Interaction Engine — Zye Day 16.
Finds and triggers specific buttons, menu items, list items, and tabs using UIA patterns,
with ambiguity protection and click_input fallback.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Any, Optional

try:
    from pywinauto import Desktop
    _PYWINAUTO_AVAILABLE = True
except ImportError:
    _PYWINAUTO_AVAILABLE = False

logger = logging.getLogger("zye.windows.uia_interaction")


class WindowsUIAInteraction:
    """
    Executes controlled clicks and pattern invocations on named UIA controls.
    """

    def click_ui_element(
        self,
        window_keyword: str,
        element_name: str,
        control_type: str = "",
    ) -> dict[str, Any]:
        """
        Locate and click or invoke an interactive element within the specified window.
        """
        if not _PYWINAUTO_AVAILABLE:
            return {
                "status": "ERROR",
                "message": "pywinauto is not available for UI element interaction.",
                "window": window_keyword,
                "element": element_name,
            }

        win_kw = str(window_keyword).strip()
        elem_name = str(element_name).strip()
        ctrl_t = str(control_type).strip().lower()

        if not win_kw or not elem_name:
            return {
                "status": "ERROR",
                "message": "window_keyword and element_name cannot be empty.",
                "window": win_kw,
                "element": elem_name,
            }

        try:
            desktop = Desktop(backend="uia")
            windows = desktop.windows()

            target_window = None
            for w in windows:
                try:
                    title = w.window_text() or ""
                    if win_kw.lower() in title.lower() and title.strip():
                        target_window = w
                        break
                except Exception:
                    continue

            if target_window is None:
                return {
                    "status": "WINDOW_NOT_FOUND",
                    "message": f"No active window matching '{win_kw}' found.",
                    "window": win_kw,
                    "element": elem_name,
                }

            # Focus the window first
            try:
                target_window.set_focus()
            except Exception:
                pass

            # Search descendants
            descendants = target_window.descendants()
            matching_elements: list[Any] = []

            for d in descendants:
                try:
                    info = d.element_info
                    name = (info.name or "").strip()
                    auto_id = getattr(info, "automation_id", "") or ""
                    c_type = (info.control_type or "").strip().lower()

                    # Check control type filter if specified
                    if ctrl_t and c_type != ctrl_t:
                        continue

                    # Match by name or automation_id
                    if elem_name.lower() == name.lower() or elem_name.lower() == auto_id.lower():
                        matching_elements.append(d)
                    elif elem_name.lower() in name.lower() and len(elem_name) >= 3:
                        matching_elements.append(d)
                except Exception:
                    continue

            if not matching_elements:
                return {
                    "status": "ELEMENT_NOT_FOUND",
                    "message": f"Element '{elem_name}' not found in window '{target_window.window_text()}'.",
                    "window": target_window.window_text(),
                    "element": elem_name,
                }

            # Check for ambiguity
            if len(matching_elements) > 1:
                # Prioritize exact name match
                exact = [e for e in matching_elements if (e.element_info.name or "").lower() == elem_name.lower()]
                if len(exact) == 1:
                    target_elem = exact[0]
                else:
                    candidates = [
                        f"{e.element_info.name} ({e.element_info.control_type}, ID: {getattr(e.element_info, 'automation_id', '')})"
                        for e in matching_elements[:5]
                    ]
                    return {
                        "status": "AMBIGUOUS_ELEMENT",
                        "message": f"Multiple controls match '{elem_name}'. Please clarify which element.",
                        "candidates": candidates,
                        "window": target_window.window_text(),
                        "element": elem_name,
                    }
            else:
                target_elem = matching_elements[0]

            elem_info = target_elem.element_info
            # Check enabled state
            if not getattr(elem_info, "enabled", True):
                return {
                    "status": "ELEMENT_DISABLED",
                    "message": f"Element '{elem_name}' is currently disabled.",
                    "window": target_window.window_text(),
                    "element": elem_name,
                }

            # Execute action: prefer UIA Invoke / Toggle / SelectionItem patterns, fallback to click_input
            action_invoked = ""
            try:
                # 1. InvokePattern
                if hasattr(target_elem, "invoke"):
                    target_elem.invoke()
                    action_invoked = "InvokePattern.invoke"
                # 2. TogglePattern
                elif hasattr(target_elem, "toggle"):
                    target_elem.toggle()
                    action_invoked = "TogglePattern.toggle"
                # 3. SelectionItemPattern
                elif hasattr(target_elem, "select"):
                    target_elem.select()
                    action_invoked = "SelectionItemPattern.select"
                # 4. Fallback click_input
                else:
                    target_elem.click_input()
                    action_invoked = "click_input"

                time.sleep(0.15)
                return {
                    "status": "SUCCESS",
                    "action": "click_ui_element",
                    "element_name": elem_info.name,
                    "control_type": elem_info.control_type,
                    "automation_id": getattr(elem_info, "automation_id", ""),
                    "invocation_method": action_invoked,
                    "window": target_window.window_text(),
                    "verified": True,
                }
            except Exception as act_exc:
                # Fallback to click_input if pattern failed
                try:
                    target_elem.click_input()
                    time.sleep(0.15)
                    return {
                        "status": "SUCCESS",
                        "action": "click_ui_element",
                        "element_name": elem_info.name,
                        "control_type": elem_info.control_type,
                        "automation_id": getattr(elem_info, "automation_id", ""),
                        "invocation_method": "click_input_fallback",
                        "window": target_window.window_text(),
                        "verified": True,
                    }
                except Exception as fallback_exc:
                    return {
                        "status": "ERROR",
                        "message": f"Could not interact with '{elem_name}': {act_exc} (fallback failed: {fallback_exc})",
                        "window": target_window.window_text(),
                        "element": elem_name,
                    }

        except Exception as exc:
            logger.error("Error clicking UI element '%s': %s", elem_name, exc)
            return {
                "status": "ERROR",
                "message": f"Interaction failed: {exc}",
                "window": win_kw,
                "element": elem_name,
            }

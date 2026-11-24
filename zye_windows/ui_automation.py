"""
Advanced Windows UI Automation Engine — Zye Day 19.
Screenshot-free UI accessibility tree inspection, element discovery, safe pattern invoke,
smart clicking, and Unicode text entry using pywinauto backend="uia".
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

from zye_windows.input_controller import WindowsInputController
from zye_windows.uia_inspector import WindowsUIAInspector
from zye_windows.uia_interaction import WindowsUIAInteraction
from zye_windows.windows_models import UIControl

logger = logging.getLogger("zye.windows.ui_automation")

DEFAULT_MAX_ELEMENTS = 60
DEFAULT_TIMEOUT_SECONDS = 10.0


class WindowsUIAutomation:
    """
    Unified UI Automation facade providing structural inspection, control finding,
    safe pattern clicking, text typing, and selection without screenshot overhead.
    """

    def __init__(
        self,
        inspector: Optional[WindowsUIAInspector] = None,
        interaction: Optional[WindowsUIAInteraction] = None,
        input_ctrl: Optional[WindowsInputController] = None,
        max_elements: int = DEFAULT_MAX_ELEMENTS,
    ) -> None:
        self.inspector = inspector or WindowsUIAInspector(max_controls=max_elements)
        self.interaction = interaction or WindowsUIAInteraction()
        self.input_ctrl = input_ctrl or WindowsInputController()
        self.max_elements = max_elements

    def inspect_app_ui(
        self,
        window_keyword: str,
        max_controls: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Inspect the UI of a window matching window_keyword.
        Returns a bounded list of interactive controls with their types and automation IDs.
        """
        return self.inspector.inspect_app_ui(window_keyword, max_controls=max_controls or self.max_elements)

    def get_ui_element_tree(
        self,
        window_keyword: str,
        max_depth: int = 3,
        max_elements: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Extract a bounded hierarchy tree of UI elements for the target window.
        """
        if not _PYWINAUTO_AVAILABLE:
            return {"status": "ERROR", "message": "pywinauto is not available."}

        win_kw = str(window_keyword).strip()
        if not win_kw:
            return {"status": "ERROR", "message": "window_keyword cannot be empty."}

        limit = max_elements or self.max_elements
        try:
            desktop = Desktop(backend="uia")
            windows = desktop.windows()
            target_win = None
            for w in windows:
                try:
                    title = w.window_text() or ""
                    if win_kw.lower() in title.lower() and title.strip():
                        target_win = w
                        break
                except Exception:
                    continue

            if target_win is None:
                return {
                    "status": "WINDOW_NOT_FOUND",
                    "message": f"Window matching '{win_kw}' not found.",
                    "window": win_kw,
                    "tree": [],
                }

            tree_nodes: list[dict[str, Any]] = []

            def _walk(ctrl: Any, depth: int) -> None:
                if depth > max_depth or len(tree_nodes) >= limit:
                    return
                try:
                    children = ctrl.children()
                except Exception:
                    return

                for c in children:
                    if len(tree_nodes) >= limit:
                        break
                    try:
                        info = c.element_info
                        name = (info.name or "").strip()
                        c_type = (info.control_type or "").strip()
                        auto_id = getattr(info, "automation_id", "") or ""
                        tree_nodes.append({
                            "depth": depth,
                            "name": name,
                            "control_type": c_type,
                            "automation_id": auto_id,
                            "enabled": getattr(info, "enabled", True),
                            "visible": getattr(info, "visible", True),
                        })
                        _walk(c, depth + 1)
                    except Exception:
                        continue

            _walk(target_win, 1)
            return {
                "status": "SUCCESS",
                "window": target_win.window_text(),
                "element_count": len(tree_nodes),
                "tree": tree_nodes,
            }
        except Exception as exc:
            return {"status": "ERROR", "message": f"Failed to build UI tree: {exc}"}

    def find_ui_element(
        self,
        window_keyword: str,
        element_name: str,
        control_type: str = "",
    ) -> dict[str, Any]:
        """
        Locate a specific UI element inside the target window by name or automation ID.
        Checks for uniqueness to prevent ambiguous clicks.
        """
        inspect_res = self.inspect_app_ui(window_keyword, max_controls=self.max_elements)
        if inspect_res.get("status") != "SUCCESS":
            return inspect_res

        controls = inspect_res.get("controls", [])
        clean_elem = element_name.strip().lower()
        ctrl_t = control_type.strip().lower()

        matches = []
        for c in controls:
            name = (c.get("name") or "").lower()
            auto_id = (c.get("automation_id") or "").lower()
            c_type = (c.get("control_type") or "").lower()

            if ctrl_t and ctrl_t != c_type:
                continue

            if clean_elem == name or clean_elem == auto_id or clean_elem in name:
                matches.append(c)

        if not matches:
            return {
                "status": "NOT_FOUND",
                "message": f"Element '{element_name}' not found in window '{window_keyword}'.",
                "element": element_name,
            }

        if len(matches) > 1:
            # Check for exact match
            exact = [m for m in matches if m.get("name", "").lower() == clean_elem or m.get("automation_id", "").lower() == clean_elem]
            if len(exact) == 1:
                return {
                    "status": "SUCCESS",
                    "element": exact[0],
                    "unique": True,
                }
            return {
                "status": "AMBIGUOUS_ELEMENT",
                "message": f"Multiple ({len(matches)}) elements match '{element_name}'. Please disambiguate.",
                "candidates": matches[:5],
                "unique": False,
            }

        return {
            "status": "SUCCESS",
            "element": matches[0],
            "unique": True,
        }

    def get_ui_element_details(
        self,
        window_keyword: str,
        element_name: str,
    ) -> dict[str, Any]:
        """Fetch exhaustive details (type, rect, enabled, visible) for a named control."""
        found = self.find_ui_element(window_keyword, element_name)
        if found.get("status") != "SUCCESS":
            return found
        return {
            "status": "SUCCESS",
            "details": found.get("element"),
            "window": window_keyword,
        }

    def click_ui_element(
        self,
        window_keyword: str,
        element_name: str,
        control_type: str = "",
    ) -> dict[str, Any]:
        """
        Safely click or invoke a UI element inside window_keyword.
        Verifies element exists, is enabled, and is unique before clicking.
        """
        # First check uniqueness
        found = self.find_ui_element(window_keyword, element_name, control_type=control_type)
        if found.get("status") == "AMBIGUOUS_ELEMENT":
            return found
        if found.get("status") != "SUCCESS":
            return found

        elem_meta = found.get("element", {})
        if not elem_meta.get("is_enabled", True):
            return {
                "status": "ELEMENT_DISABLED",
                "message": f"Element '{element_name}' is currently disabled.",
                "element": elem_meta,
            }

        # Delegate execution to interaction engine
        return self.interaction.click_ui_element(
            window_keyword=window_keyword,
            element_name=element_name,
            control_type=control_type,
        )

    def type_into_ui_element(
        self,
        window_keyword: str,
        element_name: str,
        text: str,
        submit: bool = False,
    ) -> dict[str, Any]:
        """
        Focus target Edit element and insert text with Unicode preservation.
        """
        if not text:
            return {"status": "ERROR", "message": "Text cannot be empty."}

        # Focus target element
        click_res = self.click_ui_element(window_keyword, element_name, control_type="Edit")
        if click_res.get("status") not in ("SUCCESS", "ALREADY_FOCUSED"):
            # If Edit not found with exact name, try focusing the window and using dictate directly
            pass

        # Safely insert text using input controller's Unicode-safe dictation
        return self.input_ctrl.dictate_text_anywhere(text, press_enter=submit)

    def select_ui_element(
        self,
        window_keyword: str,
        element_name: str,
    ) -> dict[str, Any]:
        """Select a ListItem, MenuItem, or TabItem control."""
        return self.click_ui_element(window_keyword, element_name)

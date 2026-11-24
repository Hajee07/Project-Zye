"""
Ribbon & Menu Accelerator for Microsoft Office and Desktop Apps — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.desktop_ui.keyboard_sequence_engine import KeyboardSequenceEngine

logger = logging.getLogger("zye.office.ui.ribbon")


class DesktopRibbonAccelerator:
    """Triggers Alt-key ribbon shortcuts and application menu sequences."""

    def __init__(self, keyboard_engine: Optional[KeyboardSequenceEngine] = None) -> None:
        self.keyboard = keyboard_engine or KeyboardSequenceEngine()

    def trigger_ribbon_tab(self, tab_key: str, expected_process: Optional[str] = None) -> Dict[str, Any]:
        """Activate a Ribbon tab (e.g. 'h' for Home, 'n' for Insert, 'p' for Page Layout)."""
        seq = ["alt", tab_key]
        return self.keyboard.execute_sequence(seq, expected_process=expected_process)

    def execute_ribbon_action(
        self,
        key_sequence: List[str],
        expected_process: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a full Alt-shortcut sequence."""
        return self.keyboard.execute_sequence(key_sequence, expected_process=expected_process)
